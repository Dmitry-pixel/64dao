# -*- coding: utf-8 -*-
"""
Метод 4 «Алмазное колесо» — заливка контента из content/m4/*.json.

Что заливается: 10 модулей, 120 вопросов с вариантами ответа, 22 правила
противоречий, 7 цепочек симптомов, 90 карточек отчёта.

Главное правило: после первой заливки хозяин контента — админка, а не файлы.
Поэтому обычный запуск только ДОБАВЛЯЕТ недостающее (новый вопрос, новую
карточку, новый вариант ответа) и не меняет ни одной существующей строки.
Правки, сделанные в админке, повторный запуск не трогает.

    docker compose exec backend python seed_m4_content.py            # добавить недостающее
    docker compose exec backend python seed_m4_content.py --check    # только проверить файлы
    docker compose exec backend python seed_m4_content.py --reset    # перезаписать всё из файлов

--reset возвращает тексты к файлам и стирает правки из админки. У вопросов,
карточек и правил, чей текст при этом изменился, поднимается версия
(item_version / rule_version): иначе старые отчёты станут несопоставимы с
новыми, а модуль динамики этого не заметит.

Перед записью файлы проверяются: коды вопросов в правилах, цепочках,
контрольных парах и условиях показа должны существовать, у каждой
рекомендации — три оценки приоритета. Ошибка в файлах — ничего не пишется.
"""
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.m4_models import (
    M4Card,
    M4Module,
    M4Question,
    M4QuestionOption,
    M4Rule,
    M4SymptomChain,
)

CONTENT = Path(__file__).parent / "content" / "m4"

# Поля, изменение которых делает старые ответы и отчёты несопоставимыми.
QUESTION_VERSIONED = ("text", "type", "reverse", "unknown_score")
CARD_VERSIONED = ("title", "body", "mistake", "steps", "first_step", "how_to_check")


def load(name: str):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


# ── Чтение и проверка файлов ─────────────────────────────────────────────────
def read_content() -> dict:
    mod_file = load("modules.json")
    scale_types = mod_file["scale_types"]

    modules, questions, intros = [], [], {}
    for i, m in enumerate(mod_file["modules"]):
        modules.append({
            "code": m["code"], "slug": m["slug"], "name": m["name"],
            "client_question": m["client_question"], "why_it_matters": m["why_it_matters"],
            "is_effect": bool(m.get("is_effect")), "sort": i + 1,
        })

    for path in sorted((CONTENT / "questions").glob("*.json")):
        f = json.loads(path.read_text(encoding="utf-8"))
        intros[f["module"]] = f.get("intro")
        for i, q in enumerate(f["questions"]):
            if q["type"] in ("bool", "scale3"):
                opts = [o for o in scale_types[q["type"]]["options"] if o["value"] != "unknown"]
            else:
                opts = q.get("options") or []
            questions.append({
                "code": q["code"], "module_code": f["module"], "text": q["text"],
                "type": q["type"], "unit": q.get("unit"), "weight": q["weight"],
                "is_fact": bool(q.get("is_fact")), "tier": q["tier"],
                "reverse": bool(q.get("reverse")),
                "score_neutral": bool(q.get("score_neutral")),
                "score_excluded": bool(q.get("score_excluded")),
                "affects": q.get("affects"),
                "unknown_allowed": q.get("unknown_allowed", True),
                "unknown_score": q.get("unknown_score"),
                "unknown_confidence_penalty": q.get("unknown_confidence_penalty", 1),
                "metric_code": q.get("metric_code"),
                "threshold_based": bool(q.get("threshold_based")),
                "control_pair": q.get("control_pair"),
                "applies_when": q.get("applies_when"),
                "construct_code": q.get("construct_code"),
                "source_ref": q.get("source_ref"),
                "min_value": q.get("min"), "max_value": q.get("max"),
                "note_internal": q.get("note_internal"),
                "sort": i + 1,
                "options": [
                    {"value": o["value"], "label": o["label"], "score": o.get("score"), "sort": j + 1}
                    for j, o in enumerate(opts)
                ],
            })
    for m in modules:
        m["intro"] = intros.get(m["code"])

    rf = load("contradiction-rules.json")
    mvp = set(rf.get("mvp_rules", []))
    rules = [{
        "code": r["code"], "title": r["title"], "severity": r["severity"],
        "conditions": r["conditions"], "diagnosis": r["diagnosis"],
        "what_happens": r["what_happens"], "fix_one_of": r["fix_one_of"],
        "cost_of_inaction": r["cost_of_inaction"], "source_ref": r.get("source_ref"),
        "is_mvp": r["code"] in mvp, "sort": i + 1,
    } for i, r in enumerate(rf["rules"])]

    chains = [{
        "code": s["code"], "label": s["label"], "detected_by": s["detected_by"],
        "chain": s["chain"], "root_modules": s["root_modules"],
        "check_questions": s["check_questions"], "first_action": s["first_action"],
        "note": s.get("note"), "sort": i + 1,
    } for i, s in enumerate(load("symptom-chains.json")["symptoms"])]

    cards = [{
        "kind": c["kind"], "key": c["key"], "module_code": c.get("module"),
        "state": c.get("state"), "rule_code": c.get("rule"),
        "title": c["title"], "body": c["body"], "mistake": c.get("mistake"),
        "steps": c.get("steps"), "first_step": c.get("first_step"),
        "how_to_check": c.get("how_to_check"), "effect": c.get("effect"),
        "speed_weeks": c.get("speed_weeks"), "cost": c.get("cost"), "sort": c.get("sort", 0),
    } for c in load("cards.json")["cards"]]

    return {"modules": modules, "questions": questions, "rules": rules,
            "chains": chains, "cards": cards}


def rule_refs(node, out: list) -> None:
    """Все пары (код вопроса, значение) из условия правила."""
    if isinstance(node, dict):
        if "q" in node:
            out.append((node["q"], node.get("op"), node.get("value")))
        for v in node.values():
            rule_refs(v, out)
    elif isinstance(node, list):
        for v in node:
            rule_refs(v, out)


def check(c: dict) -> list[str]:
    errs = []
    mods = {m["code"] for m in c["modules"]}
    qs = {q["code"]: q for q in c["questions"]}
    rules = {r["code"] for r in c["rules"]}

    if len(qs) != len(c["questions"]):
        errs.append("повторяющиеся коды вопросов")
    for q in c["questions"]:
        if q["module_code"] not in mods:
            errs.append(f"{q['code']}: нет модуля {q['module_code']}")
        if len(q["options"]) > 3:
            errs.append(f"{q['code']}: больше трёх вариантов ответа")
        if q["type"] == "choice" and not q["options"]:
            errs.append(f"{q['code']}: choice без вариантов")
        if q["control_pair"] and q["control_pair"] not in qs:
            errs.append(f"{q['code']}: контрольная пара {q['control_pair']} не найдена")
        for ref in (q["applies_when"] or {}):
            # profile.* — поле профиля компании, а не вопрос анкеты
            if not ref.startswith("profile.") and ref not in qs:
                errs.append(f"{q['code']}: условие показа ссылается на {ref}")

    for r in c["rules"]:
        refs = []
        rule_refs(r["conditions"], refs)
        for code, op, value in refs:
            q = qs.get(code)
            if q is None:
                errs.append(f"{r['code']}: нет вопроса {code}")
                continue
            if op == "gt_question":
                if value not in qs:
                    errs.append(f"{r['code']}: нет вопроса {value}")
                continue
            if q["type"] in ("number", "money"):
                continue
            allowed = {o["value"] for o in q["options"]} | {"unknown"}
            for v in (value if isinstance(value, list) else [value]):
                if v not in allowed:
                    errs.append(f"{r['code']}: у {code} нет варианта «{v}»")

    for s in c["chains"]:
        for code in s["detected_by"] + s["check_questions"]:
            if code not in qs:
                errs.append(f"цепочка {s['code']}: нет вопроса {code}")
        for m in s["root_modules"]:
            if m not in mods:
                errs.append(f"цепочка {s['code']}: нет модуля {m}")

    seen = set()
    for k in c["cards"]:
        pair = (k["kind"], k["key"])
        if pair in seen:
            errs.append(f"карточка {pair} повторяется")
        seen.add(pair)
        if k["module_code"] is not None and k["module_code"] not in mods:
            errs.append(f"карточка {k['key']}: нет модуля {k['module_code']}")
        if k["rule_code"] is not None and k["rule_code"] not in rules:
            errs.append(f"карточка {k['key']}: нет правила {k['rule_code']}")
        if k["kind"] == "recommendation" and None in (k["effect"], k["speed_weeks"], k["cost"]):
            errs.append(f"рекомендация {k['key']}: не хватает effect / speed_weeks / cost")
    return errs


# ── Запись ───────────────────────────────────────────────────────────────────
def apply(row, data: dict, fields, versioned=(), version_attr=None) -> bool:
    """Перезапись полей строки. Возвращает True, если что-то изменилось.
    Если изменилось поле из versioned — поднимает версию."""
    changed = [f for f in fields if getattr(row, f) != data[f]]
    for f in changed:
        setattr(row, f, data[f])
    if version_attr and any(f in versioned for f in changed):
        setattr(row, version_attr, getattr(row, version_attr) + 1)
    return bool(changed)


async def seed(c: dict, reset: bool) -> dict:
    stats = {}

    def bump(table, what):
        stats.setdefault(table, {"добавлено": 0, "перезаписано": 0, "без изменений": 0})
        stats[table][what] += 1

    async with AsyncSessionLocal() as s:
        # Модули
        existing = {m.code: m for m in (await s.execute(select(M4Module))).scalars()}
        for d in c["modules"]:
            row = existing.get(d["code"])
            if row is None:
                s.add(M4Module(**d))
                bump("m4_modules", "добавлено")
            elif reset and apply(row, d, [k for k in d if k != "code"]):
                bump("m4_modules", "перезаписано")
            else:
                bump("m4_modules", "без изменений")
        await s.flush()

        # Вопросы и варианты
        existing = {q.code: q for q in (await s.execute(select(M4Question))).scalars()}
        for d in c["questions"]:
            d = dict(d)
            opts = d.pop("options")
            row = existing.get(d["code"])
            if row is None:
                row = M4Question(**d)
                s.add(row)
                await s.flush()
                for o in opts:
                    s.add(M4QuestionOption(question_id=row.id, **o))
                bump("m4_questions", "добавлено")
                continue
            changed = reset and apply(row, d, [k for k in d if k != "code"],
                                      QUESTION_VERSIONED, "item_version")
            cur = {o.value: o for o in (await s.execute(
                select(M4QuestionOption).where(M4QuestionOption.question_id == row.id)
            )).scalars()}
            for o in opts:
                orow = cur.get(o["value"])
                if orow is None:
                    s.add(M4QuestionOption(question_id=row.id, **o))
                    changed = True
                elif reset and apply(orow, o, ("label", "score", "sort")):
                    changed = True
                    row.item_version += 1
            bump("m4_questions", "перезаписано" if changed else "без изменений")
        await s.flush()

        # Правила — раньше карточек: на них ссылается внешний ключ
        existing = {r.code: r for r in (await s.execute(select(M4Rule))).scalars()}
        for d in c["rules"]:
            row = existing.get(d["code"])
            if row is None:
                s.add(M4Rule(**d))
                bump("m4_rules", "добавлено")
            elif reset and apply(row, d, [k for k in d if k != "code"],
                                 ("conditions",), "rule_version"):
                bump("m4_rules", "перезаписано")
            else:
                bump("m4_rules", "без изменений")
        await s.flush()

        # Цепочки симптомов
        existing = {x.code: x for x in (await s.execute(select(M4SymptomChain))).scalars()}
        for d in c["chains"]:
            row = existing.get(d["code"])
            if row is None:
                s.add(M4SymptomChain(**d))
                bump("m4_symptom_chains", "добавлено")
            elif reset and apply(row, d, [k for k in d if k != "code"]):
                bump("m4_symptom_chains", "перезаписано")
            else:
                bump("m4_symptom_chains", "без изменений")

        # Карточки
        existing = {(k.kind, k.key): k for k in (await s.execute(select(M4Card))).scalars()}
        for d in c["cards"]:
            row = existing.get((d["kind"], d["key"]))
            if row is None:
                s.add(M4Card(**d))
                bump("m4_cards", "добавлено")
            elif reset and apply(row, d, [k for k in d if k not in ("kind", "key")],
                                 CARD_VERSIONED, "item_version"):
                bump("m4_cards", "перезаписано")
            else:
                bump("m4_cards", "без изменений")

        await s.commit()
    return stats


def main() -> None:
    reset = "--reset" in sys.argv
    content = read_content()
    errs = check(content)
    print(f"Файлы: модулей {len(content['modules'])}, вопросов {len(content['questions'])}, "
          f"правил {len(content['rules'])}, цепочек {len(content['chains'])}, "
          f"карточек {len(content['cards'])}")
    if errs:
        print("ОШИБКИ В ФАЙЛАХ, ничего не записано:")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print("Проверка файлов: OK")
    if "--check" in sys.argv:
        return
    stats = asyncio.run(seed(content, reset))
    for table, st in stats.items():
        print(f"{table:20} " + ", ".join(f"{k} {v}" for k, v in st.items()))


if __name__ == "__main__":
    main()

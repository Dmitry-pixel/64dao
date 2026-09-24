# -*- coding: utf-8 -*-
"""
Метод 4 — сборка отчёта из снимка расчёта и карточек.

Один источник для веба и PDF: снимок даёт цифры и решения (какие модули
низкие, где ограничение, что сработало, в каком порядке действовать),
карточки и правила из админки — тексты. Рендеры получают готовую
структуру и сами ничего не вычисляют, иначе веб и PDF разойдутся.

Правила отбора (content/m4/cards.json → render_rules):
  * состояние — одна карточка на модуль, по баллу;
  * карточка ограничения дополняет состояние модуля, а не заменяет его;
  * рекомендации — только для модулей low/mid и для сработавших правил;
  * отсутствующая или выключенная карточка не роняет отчёт: раздел
    собирается дальше без неё (card = None).

Тексты берутся текущие: правка карточки в админке меняет и ранее
рассчитанные отчёты. Версии на момент расчёта записаны в прогоне
(item_versions) — по ним видно, что текст с тех пор правили.

В отчёт не попадают source_ref, баллы вариантов и внутренние заметки.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.m4_models import M4Card, M4Module, M4Rule, M4Run, M4Snapshot
from app.models import Company

# Сопоставление причин и следствия: короткая фраза к выводу расчёта.
# Не карточка — это пояснение к цифре, а не рекомендация.
CAUSE_EFFECT_TEXT = {
    "causes_high_effect_low": (
        "Управленческие модули в среднем сильнее, чем показывают финансы. Либо цифры в модуле «Финансы» "
        "названы неточно, либо улучшения ещё не дошли до денег — результат отстаёт от причин на квартал и больше."
    ),
    "causes_low_effect_high": (
        "Финансы выглядят лучше, чем устройство компании. Результат держится на благоприятном рынке, а не на "
        "управлении — при смене условий он уйдёт первым."
    ),
    "both_low": (
        "Слабы и управленческие модули, и финансы: цифры честно отражают устройство компании. "
        "Работать нужно с системным ограничением, а не с финансами напрямую."
    ),
    "consistent": "Финансы соответствуют состоянию управленческих модулей.",
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _card(c: M4Card | None) -> dict | None:
    if c is None:
        return None
    return {"title": c.title, "body": c.body, "mistake": c.mistake, "steps": c.steps,
            "first_step": c.first_step, "how_to_check": c.how_to_check}


async def build(db: AsyncSession, run: M4Run, snap: M4Snapshot) -> dict:
    modules = {m.code: m for m in (await db.execute(select(M4Module))).scalars()}
    cards = {(c.kind, c.key): c for c in
             (await db.execute(select(M4Card).where(M4Card.is_active.is_(True)))).scalars()}
    rules = {r.code: r for r in (await db.execute(select(M4Rule))).scalars()}
    company = await db.get(Company, run.company_id)

    def name(code: int) -> str:
        m = modules.get(code)
        return m.name if m else f"Модуль {code}"

    # ── Модули ────────────────────────────────────────────────────────────
    mod_out = []
    for code in range(1, 11):
        v = snap.module_scores.get(str(code), {})
        state = v.get("state")
        mod_out.append({
            "code": code, "name": name(code),
            "client_question": modules[code].client_question if code in modules else None,
            "is_effect": code == 10,
            "score": v.get("score"), "state": state,
            "no_accounting": bool(v.get("no_accounting")),
            "card": _card(cards.get(("module_state", f"m{code:02d}_{state}"))) if state else None,
        })

    # ── Ограничение ───────────────────────────────────────────────────────
    constraint = None
    c = snap.constraint_detail
    if c:
        constraint = {
            "module": c["module"], "name": name(c["module"]), "score": c["score"],
            "blocked": [{"code": b, "name": name(b)} for b in c.get("blocked", [])],
            "card": _card(cards.get(("module_constraint", f"m{c['module']:02d}"))),
        }

    # ── Противоречия ──────────────────────────────────────────────────────
    contradictions = []
    for f in snap.fired_rules:
        r = rules.get(f["code"])
        if r is None:
            continue
        contradictions.append({
            "code": r.code, "title": r.title, "severity": r.severity, "diagnosis": r.diagnosis,
            "what_happens": r.what_happens, "fix_one_of": r.fix_one_of, "cost_of_inaction": r.cost_of_inaction,
        })
    contradictions.sort(key=lambda x: SEVERITY_ORDER.get(x["severity"], 3))
    unverified = [{"code": code, "title": rules[code].title} for code in snap.unverified_rules if code in rules]

    # ── Очередь действий ──────────────────────────────────────────────────
    actions = []
    for item in snap.priority_queue:
        card = cards.get(("recommendation", item["key"]))
        if card is None:
            continue
        a = {
            "n": len(actions) + 1, "key": item["key"], "module_code": item.get("module_code"),
            "module_name": name(item["module_code"]) if item.get("module_code") else None,
            "rule_code": item.get("rule_code"),
            "is_constraint": item.get("is_constraint", False),
            "blocked_by_constraint": item.get("blocked_by_constraint", False),
            "effect": item.get("effect"), "speed_weeks": item.get("speed_weeks"), "cost": item.get("cost"),
            "title": card.title, "first_step": card.first_step, "how_to_check": card.how_to_check,
        }
        if item.get("rule_code"):
            # У рекомендации по правилу своего текста нет — варианты решения
            # живут в самом правиле (fix_one_of), тело карточки служебное.
            rule = rules.get(item["rule_code"])
            a.update(body=None, steps=None, options=rule.fix_one_of if rule else None)
        else:
            a.update(body=card.body, steps=card.steps, options=None)
        actions.append(a)

    # ── Достоверность ─────────────────────────────────────────────────────
    comp = snap.confidence_components or {}
    level = comp.get("level", "medium")
    confidence = {
        "index": snap.confidence_index, "level": level,
        "cautious": level == "low",
        "card": _card(cards.get(("confidence", level))),
        "no_accounting": [{"code": m["code"], "name": m["name"]} for m in mod_out if m["no_accounting"]],
    }

    ce = snap.cause_effect
    return {
        "run": {"id": run.id, "mode": run.mode, "company_name": company.name if company else None,
                "calculated_at": run.calculated_at, "calc_version": snap.calc_version, "reduced": snap.reduced},
        "modules": mod_out,
        "top_gaps": [{"code": g, "name": name(g)} for g in snap.top_gaps],
        "constraint": constraint,
        "cause_effect": {**ce, "text": CAUSE_EFFECT_TEXT.get(ce["case"])} if ce else None,
        "contradictions": contradictions,
        "unverified": unverified,
        "actions": actions,
        "resistance": float(snap.resistance_factor),
        "confidence": confidence,
    }

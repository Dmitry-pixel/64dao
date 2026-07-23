# -*- coding: utf-8 -*-
"""
Интерпретация финансовой функции — слои A–E (Спецификация §5).

Разделение ответственности:
- ПРЕДИКАТЫ (правила напряжений R1–R12, выбор тональности/квадранта/триграмм,
  порядок приоритетов) — детерминированный код здесь; БД не нужна → тестируемо.
- ТЕКСТ — из контента (fin_content + strategies.fin_pattern_*), передаётся как
  готовый mapping `content`. Загрузка из БД — `load_content(session)`.

Правило с is_active=false в отчёт не попадает: `load_content` отбирает только
активные строки, поэтому отсутствие ключа в `content` = «не выводить».
"""
from __future__ import annotations

from app.finance_items import BLOCKS
from app.contour_route import build_route

PLACEHOLDER = "Не заполнено"

# Человекочитаемые расшифровки флагов (Спецификация §3.5/§3.6) для «оговорок по данным»
_LINE_FLAG_TEXT = {
    "INCONSISTENT_BLOCK": "противоречивые ответы в блоке (разброс ≥2) — рекомендуется уточняющее интервью",
    "BORDERLINE_LINE":    "неустойчивое определение (балл в зоне 2.40–2.60) — рекомендуется уточняющее интервью",
    "PARTIAL_BLOCK":      "один ответ «Не знаю» — балл рассчитан по трём пунктам",
    "VETO_APPLIED":       "линия переопределена в Инь по правилу вето (нет приверженности первого лица, пункт 4.1)",
    "VETO_UNKNOWN":       "по пункту 4.1 выбран ответ «Не знаю» — правило вето не применялось",
}


# ── Слой D. Предикаты правил напряжений R1–R12 (Спецификация §5.5) ─────────────
def evaluate_rules(lines: list[dict]) -> list[str]:
    """Возвращает ID сработавших правил в порядке R1..R12."""
    L = {l["line"]: l for l in lines}
    sym = lambda n: L[n]["symbol"]
    moving = [n for n in L if L[n]["moving"]]
    has_moving = len(moving) >= 1

    fired: list[str] = []
    if sym(4) == "A" and sym(6) == "B":                 fired.append("R1")
    if sym(6) == "A" and (sym(1) == "B" or sym(2) == "B"): fired.append("R2")
    if sym(3) == "A" and sym(2) == "B":                 fired.append("R3")
    if sym(2) == "A" and sym(3) == "B":                 fired.append("R4")
    if sym(1) == "B" and sym(3) == "A":                 fired.append("R5")
    if sym(5) == "B" and has_moving:                    fired.append("R6")
    if sym(4) == "B" and sym(6) == "A":                 fired.append("R7")
    if sym(1) == "A" and sym(2) == "A" and sym(6) == "B": fired.append("R8")
    if L[4]["state"] == "old_yang":                     fired.append("R9")
    if sym(3) == "B" and has_moving:                    fired.append("R10")
    if sym(5) == "B" and sym(2) == "B":                 fired.append("R11")
    if len(moving) >= 3:                                fired.append("R12")
    return fired


# ── Слой A. Тональность по индексу зрелости (Спецификация §5.2) ────────────────
def tonality_key(maturity_index: int) -> str:
    if maturity_index >= 5:
        return "mature"
    if maturity_index >= 3:
        return "transitional"
    return "crisis"


# ── Сборка интерпретации ──────────────────────────────────────────────────────
def build_interpretation(result: dict, content: dict, blocks: dict | None = None) -> dict:
    """
    Детерминированная сборка структуры интерпретации из результата скоринга
    (Этап 2) и контента. LLM не участвует (план §8.3 — v2).
    """
    blocks = blocks or BLOCKS
    lines = result["lines"]

    def c(kind: str, key: str) -> dict | None:
        return content.get(kind, {}).get(key)

    # A — тональность
    tkey = tonality_key(result["maturity_index"])
    tp = c("tonality", tkey)
    tonality = {"key": tkey, "title": (tp or {}).get("title"),
                "text": (tp or {}).get("text", PLACEHOLDER)}

    # B — квадрант + триграммы
    qkey = result["quadrant"]
    qp = c("quadrant", qkey)
    quadrant = {"key": qkey, "title": (qp or {}).get("title"),
                "text": (qp or {}).get("text", PLACEHOLDER)}
    lower_code = "".join(l["symbol"] for l in lines[0:3])
    upper_code = "".join(l["symbol"] for l in lines[3:6])
    lp = c("trigram", f"{lower_code}_lower")
    up = c("trigram", f"{upper_code}_upper")
    trigrams = {
        "lower": {"code": lower_code, "title": (lp or {}).get("title"),
                  "text": (lp or {}).get("text", PLACEHOLDER)},
        "upper": {"code": upper_code, "title": (up or {}).get("title"),
                  "text": (up or {}).get("text", PLACEHOLDER)},
    }

    # C — паттерн текущей гексаграммы
    cur = result["combination_current"]
    pc = content.get("fin_pattern", {}).get(cur)
    pattern_current = {
        "essence": (pc or {}).get("essence") or PLACEHOLDER,
        "mistake": (pc or {}).get("mistake") or PLACEHOLDER,
    }

    # D — напряжения (только активные: отсутствие ключа = не выводить)
    tensions = []
    for rid in evaluate_rules(lines):
        p = c("tension_rule", rid)
        if p is None:
            continue
        tensions.append({"id": rid, "text": p.get("text", PLACEHOLDER)})

    # Вето (Поправка П6): линия со сработавшим вето — отдельный блок ДО приоритетов.
    # Из приоритетов и плановых шагов она исключается, чтобы не дублироваться.
    veto_line = next((l for l in lines if "VETO_APPLIED" in l.get("flags", [])), None)
    veto_block = None
    if veto_line:
        _n = veto_line["line"]
        _pkg = c("action_package", f"line{_n}_yin")
        veto_block = {
            "line": _n,
            "block_title": blocks[_n]["title"],
            "score": veto_line["score"],
            "state": veto_line["state"],
            "package_title": (_pkg or {}).get("title"),
            "package_text": (_pkg or {}).get("text", PLACEHOLDER),
        }
    _veto_n = veto_line["line"] if veto_line else None

    # E — приоритеты (подвижные): старый Инь раньше старого Яна (§5.6)
    moving = [l for l in lines if l["moving"] and l["line"] != _veto_n]
    moving.sort(key=lambda l: (0 if l["state"] == "old_yin" else 1, l["line"]))
    priorities = []
    for l in moving:
        n = l["line"]
        pkg_key = f"line{n}_yin" if l["symbol"] == "B" else f"line{n}_oldyang"
        pkg = c("action_package", pkg_key)
        priorities.append({
            "line": n,
            "block_title": blocks[n]["title"],
            "state": l["state"],
            "package_title": (pkg or {}).get("title"),
            "package_text": (pkg or {}).get("text", PLACEHOLDER),
        })

    # Траектория: текущая → результирующая (§3.4 п.7). None → «конфигурация стабильна»
    res_combo = result["combination_resulting"]
    if res_combo:
        rp = content.get("fin_pattern", {}).get(res_combo)
        trajectory = {
            "current": result["hexagram_current"],
            "resulting": result["hexagram_resulting"],
            "essence": (rp or {}).get("essence") or PLACEHOLDER,
            "mistake": (rp or {}).get("mistake") or PLACEHOLDER,
        }
    else:
        trajectory = None

    # Оговорки по данным
    caveats = _build_caveats(result, blocks)

    # Следующие шаги — детерминированно из пакетов подвижных линий (план §3.4 п.9)
    # Плановые шаги: иньские линии без подвижности, от слабейшей к сильнейшей
    planned = [l for l in lines
               if l["symbol"] == "B" and not l["moving"] and l["line"] != _veto_n]
    planned.sort(key=lambda l: (l["score"], l["line"]))
    planned_steps = []
    for l in planned:
        n = l["line"]
        pkg = c("action_package", f"line{n}_yin")
        planned_steps.append({
            "line": n,
            "block_title": blocks[n]["title"],
            "state": l["state"],
            "package_title": (pkg or {}).get("title"),
            "package_text": (pkg or {}).get("text", PLACEHOLDER),
        })

    _ordered = ([veto_block] if veto_block else []) + priorities + planned_steps
    next_steps = [p["package_text"] for p in _ordered
                  if p["package_text"] != PLACEHOLDER]

    # Маршрут перехода (роадмап 2.1): шаги по подвижным линиям, текст из контента.
    route = build_route(result["lines"], result["combination_current"])
    _lines_by_num = {l["line"]: l for l in result["lines"]}
    for i, step in enumerate(route):
        ha = step["hexagram_after"]
        pkg = content.get("action_package", {}).get(step["action_key"])
        step["action_text"] = (pkg or {}).get("text") or PLACEHOLDER
        fp = content.get("fin_pattern", {}).get(ha.get("code"))
        step["after_essence"] = (fp or {}).get("essence") or PLACEHOLDER
        step["is_last"] = i == len(route) - 1
        step["mistake"] = ((fp or {}).get("mistake") or PLACEHOLDER) if step["is_last"] else None
        _ln = _lines_by_num.get(step["line"], {})
        step["is_veto"] = "VETO_APPLIED" in (_ln.get("flags") or [])

    return {
        "tonality": tonality,
        "veto_block": veto_block,
        "quadrant": quadrant,
        "trigrams": trigrams,
        "pattern_current": pattern_current,
        "tensions": tensions,
        "priorities": priorities,
        "planned_steps": planned_steps,
        "trajectory": trajectory,
        "route": route,
        "caveats": caveats,
        "next_steps": next_steps,
    }


def _build_caveats(result: dict, blocks: dict | None = None) -> list[str]:
    blocks = blocks or BLOCKS
    out: list[str] = []
    if "STRAIGHTLINING" in result.get("quality_flags", []):
        out.append("Анкета помечена как недостоверная: ≥20 из 24 ответов одинаковы (straightlining).")
    if "LOW_DATA_COMPLETENESS" in result.get("quality_flags", []):
        out.append("Низкая полнота данных: три и более ответов «не знаю» — выводы по затронутым линиям носят предварительный характер, рекомендуется дозаполнение или интервью.")
    for l in result["lines"]:
        title = blocks[l["line"]]["title"]
        for f in l["flags"]:
            txt = _LINE_FLAG_TEXT.get(f)
            if txt:
                out.append(f"{title}: {txt}.")
    return out


# ── Загрузка контента из БД (используется PDF/API на Этапах 4–5) ───────────────
async def load_content(session, contour: str = "finance") -> dict:
    """
    Собирает mapping контента из БД. Берёт только is_active=true строки fin_content
    (неактивные правила/блоки в отчёт не попадают) и fin_pattern_* из strategies.
    """
    from sqlalchemy import select
    from app.models import FinContent, Strategy

    content: dict[str, dict] = {
        "tonality": {}, "quadrant": {}, "trigram": {},
        "tension_rule": {}, "action_package": {}, "fin_pattern": {},
    }
    rows = (await session.execute(
        select(FinContent).where(
            FinContent.is_active.is_(True),
            FinContent.contour.in_([contour, "common"]),
        )
    )).scalars().all()
    # Резолюция по Поправке П1: общий слой 'common' кладётся первым,
    # контурное переопределение перезаписывает его поверх.
    for fc in sorted(rows, key=lambda r: 0 if r.contour == "common" else 1):
        content.setdefault(fc.kind, {})[fc.key] = fc.payload

    strows = (await session.execute(
        select(Strategy.combination, Strategy.fin_pattern_essence, Strategy.fin_pattern_mistake)
    )).all()
    for combo, essence, mistake in strows:
        if essence or mistake:
            content["fin_pattern"][combo] = {"essence": essence, "mistake": mistake}
    return content


def enrich_route(result: dict, content: dict) -> list[dict]:
    """Маршрут перехода с текстами действий (фича F, переиспользуется чек-листом).
    Обогащение совпадает с блоком внутри build_interpretation — единый источник."""
    route = build_route(result["lines"], result["combination_current"])
    _lines_by_num = {l["line"]: l for l in result["lines"]}
    for i, step in enumerate(route):
        ha = step["hexagram_after"]
        pkg = content.get("action_package", {}).get(step["action_key"])
        step["action_text"] = (pkg or {}).get("text") or PLACEHOLDER
        fp = content.get("fin_pattern", {}).get(ha.get("code"))
        step["after_essence"] = (fp or {}).get("essence") or PLACEHOLDER
        step["is_last"] = i == len(route) - 1
        step["mistake"] = ((fp or {}).get("mistake") or PLACEHOLDER) if step["is_last"] else None
        _ln = _lines_by_num.get(step["line"], {})
        step["is_veto"] = "VETO_APPLIED" in (_ln.get("flags") or [])
    return route

# -*- coding: utf-8 -*-
"""
Маршрут перехода контура (роадмап 2.1).

Чистые функции без БД и FastAPI: маршрут — детерминированная функция от снимка
result контура, воспроизводится при генерации отчёта. Порядок шагов повторяет
сортировку приоритетов финблока (сначала «старый Инь» — назревшие слабости,
затем «старый Ян» — риски перегрева; внутри группы — снизу вверх).
"""
from __future__ import annotations

from app.contour_scoring import _lookup
from app.contours import CONTOUR_ORDER

GAP_THRESHOLD = 3


def _flip(code: str, line: int) -> str:
    """A↔B в позиции линии (line 1-based, линия 1 = нижняя = индекс 0)."""
    i = line - 1
    ch = "B" if code[i] == "A" else "A"
    return code[:i] + ch + code[i + 1:]


def build_route(lines: list[dict], combination_current: str) -> list[dict]:
    """Пошаговый маршрут по подвижным линиям контура.

    lines: result["lines"] (список словарей LineResult).
    Возвращает список шагов; пустой список — если подвижных линий нет.
    Последний шаг всегда приводит в combination_resulting.
    """
    moving = [l for l in lines if l.get("moving")]
    order = sorted(moving, key=lambda l: (0 if l["state"] == "old_yin" else 1, l["line"]))

    code = combination_current
    steps: list[dict] = []
    for idx, l in enumerate(order, start=1):
        n = l["line"]
        code = _flip(code, n)
        # Ключ пакета действий — как в finance_interpret: Инь→_yin, Ян→_oldyang
        action_key = f"line{n}_yin" if l["symbol"] == "B" else f"line{n}_oldyang"
        steps.append({
            "order": idx,
            "line": n,
            "line_key": l["block"],        # в снимке line_key хранится в поле block
            "from_state": l["state"],       # old_yin | old_yang
            "action_key": action_key,
            "hexagram_after": _lookup(code),
        })
    return steps


def build_summary_route(results: dict[str, dict]) -> dict | None:
    """Сводный маршрут компании: этапы = контуры с подвижными линиями, по
    возрастанию зрелости (тай-брейки как в сводной карте). Контуры без подвижных
    линий перечисляются отдельно. None — если пройден < 2 контуров."""
    known = {k: v for k, v in results.items() if k in CONTOUR_ORDER and v}
    if len(known) < 2:
        return None

    entries = []
    stable = []
    for key in CONTOUR_ORDER:
        r = known.get(key)
        if not r:
            continue
        route = build_route(r["lines"], r["combination_current"])
        e = {
            "contour": key,
            "route_len": len(route),
            "entry_line": route[0]["line"] if route else None,
            "maturity_index": r.get("maturity_index"),
            "moving_count": len(r.get("moving_lines") or []),
            "hexagram_current": r.get("hexagram_current"),
            "hexagram_resulting": r.get("hexagram_resulting"),
        }
        if e["route_len"] == 0:
            stable.append(key)
        else:
            entries.append(e)

    def rank(e: dict) -> tuple:
        return (e["maturity_index"], -e["moving_count"], CONTOUR_ORDER.index(e["contour"]))

    stages = sorted(entries, key=rank)
    for i, s in enumerate(stages, start=1):
        s["stage"] = i

    focus_first = False
    if len(stages) >= 2:
        focus_first = (stages[1]["maturity_index"] - stages[0]["maturity_index"]) >= GAP_THRESHOLD

    return {"stages": stages, "stable": stable, "focus_first": focus_first}

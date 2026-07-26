# -*- coding: utf-8 -*-
"""
Сводная карта контуров (план контуров §2.4, Поправки П5 и П7).

Чистая логика: на вход — снимки result пройденных контуров, на выход — строки
таблицы и кандидат в системное ограничение. БД и FastAPI не участвуют.
"""
from __future__ import annotations

from app.contours import CONTOURS, CONTOUR_ORDER, GAP_THRESHOLD  # noqa: F401

# Со скольких контуров карта имеет смысл: сравнивать нечего, пока он один
MIN_CONTOURS = 2


def build_summary(results: dict[str, dict]) -> dict | None:
    """
    results: {ключ контура: снимок result}. Возвращает None, если контуров
    меньше двух — тогда раздел сводной карты в отчёт не попадает.
    """
    known = {k: v for k, v in results.items() if k in CONTOURS and v}
    if len(known) < MIN_CONTOURS:
        return None

    rows = []
    for key in CONTOUR_ORDER:
        r = known.get(key)
        if not r:
            continue
        rows.append({
            "contour": key,
            "title": CONTOURS[key].title,
            "combination": r.get("combination_current"),
            "hexagram_current": r.get("hexagram_current"),
            "hexagram_resulting": r.get("hexagram_resulting"),
            "maturity_index": r.get("maturity_index"),
            "moving_count": len(r.get("moving_lines") or []),
            "is_constraint": False,
        })

    # Ключ выбора ограничения: ниже зрелость -> раньше; при равенстве больше
    # подвижных линий -> раньше. Фиксированный порядок тай-брейком НЕ служит:
    # выбор по нему был бы произвольным и выдавал бы алфавит за вывод.
    def rank(row: dict) -> tuple[int, int]:
        return (row["maturity_index"], -row["moving_count"])

    best = min(rank(r) for r in rows)
    tied = [r for r in rows if rank(r) == best]

    constraint = None
    gap = None
    if len(tied) == 1:
        constraint = tied[0]["contour"]
        tied[0]["is_constraint"] = True
        others = sorted(r["maturity_index"] for r in rows if r["contour"] != constraint)
        if others:
            gap = others[0] - tied[0]["maturity_index"]

    stable = [r["contour"] for r in rows if r["moving_count"] == 0]

    return {
        "rows": rows,
        "constraint": constraint,
        "tied": [r["contour"] for r in tied] if constraint is None else [],
        "gap": gap,
        "gap_significant": bool(gap is not None and gap >= GAP_THRESHOLD),
        "stable": stable,
        "count": len(rows),
    }

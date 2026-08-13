# -*- coding: utf-8 -*-
"""
Сводная карта контуров (план контуров §2.4, Поправки П5 и П7).

Чистая логика: на вход — снимки result пройденных контуров, на выход — строки
таблицы и кандидат в системное ограничение. БД и FastAPI не участвуют.
"""
from __future__ import annotations

from app.contour_levels import LEVELS, levels_of
from app.contours import CONTOURS, CONTOUR_ORDER, GAP_THRESHOLD  # noqa: F401

# Со скольких контуров карта имеет смысл: сравнивать нечего, пока он один
MIN_CONTOURS = 2

# Со скольких контуров совпадение уровня перестаёт быть локальным. Три из
# четырёх: два совпадения — ещё пара функций, три — свойство организации.
LEVEL_SYSTEMIC_MIN = 3

# Отсутствие совпадений — тоже вывод, и формулируется он здесь, а не в двух
# рендерах. Отчётов два, правило одно.
LEVELS_NO_MATCH = (
    "Совпадений по уровням нет: состояния различаются от контура к контуру, "
    "и работать с ними следует внутри функций."
)


def _level_reading(row: dict) -> str | None:
    if row["systemic_weak"]:
        return (f'Уровень «{row["title"]}» в состоянии Стойкость в '
                f'{row["weak"]} контурах из {row["total"]}: дефицит общий '
                f'и внутри отдельной функции не лечится.')
    if row["systemic_strong"]:
        return (f'Уровень «{row["title"]}» несёт нагрузку в {row["strong"]} '
                f'контурах из {row["total"]}: на него можно опереться.')
    return None


def _levels_matrix(known: dict[str, dict]) -> list[dict]:
    """
    Один уровень по всем пройденным контурам. НЕ свёртка: агрегировать четыре
    контура в одну гексаграмму компании нечем, любое правило было бы
    произвольным. Сопоставление ничего не выдумывает, оно считает совпадения.
    """
    per = {k: {l["level"]: l for l in levels_of(r)}
           for k, r in known.items() if r}
    out = []
    for lkey, ltitle, question, lines in LEVELS:
        cells = [{"contour": k, "title": CONTOURS[k].title,
                  "code": per[k][lkey]["code"], "label": per[k][lkey]["label"],
                  "moving": per[k][lkey]["moving"]}
                 for k in CONTOUR_ORDER if per.get(k, {}).get(lkey)]
        if not cells:
            continue
        row = {
            "level": lkey, "title": ltitle, "question": question,
            "lines": list(lines), "cells": cells, "total": len(cells),
            "weak": sum(1 for c in cells if c["code"] == "BB"),
            "strong": sum(1 for c in cells if c["code"] == "AA"),
        }
        # Асимметрия намеренная. Слабость в трёх контурах из четырёх уже
        # закономерность. Опорой уровень называется только при полном
        # совпадении: 3 из 4 при слабом четвёртом — это пересказ
        # контура-ограничения, который в отчёте назван отдельно.
        row["systemic_weak"] = (row["weak"] == row["total"]
                                or row["weak"] >= LEVEL_SYSTEMIC_MIN)
        row["systemic_strong"] = row["strong"] == row["total"]
        row["reading"] = _level_reading(row)
        out.append(row)
    return out


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

    levels = _levels_matrix(known)

    return {
        "rows": rows,
        "constraint": constraint,
        "tied": [r["contour"] for r in tied] if constraint is None else [],
        "gap": gap,
        "gap_significant": bool(gap is not None and gap >= GAP_THRESHOLD),
        "stable": stable,
        "count": len(rows),
        "levels": levels,
        "levels_note": (None if any(r["reading"] for r in levels)
                        else LEVELS_NO_MATCH if levels else None),
    }

# -*- coding: utf-8 -*-
"""
Метод 3 — портфельный слой: ограничения, принадлежащие компании.

Раздел 03 отвечает на вопрос, который нельзя задать, оценивая направления по
отдельности: какая слабость повторяется и, значит, принадлежит компании, а не
продукту. Одно слабое направление — его собственная беда. Слабая линия у
большинства направлений — свойство компании, и чинить её в каждом направлении
порознь значит несколько раз оплатить одну кривую обучения.

Всё считается из снимка расчёта, контент не нужен: слабость линии видна в
символах, а классификация ограничения — в номере линии. Линии 1–3 описывают
то, что компания делает сама (конкурентная сила), линии 4–6 — то, во что она
поставлена (привлекательность рынка). Отсюда деление на ограничение
компетенции и структурное ограничение.

Проверено на образце 64dao-portfolio-report-sample.html версии 0.2: правило
отбирает те же две линии и относит их к тем же типам.
"""
from __future__ import annotations

from typing import Any, Literal

YIN = "B"

LINE_FACTORS = {
    1: "Ресурсы, юнит-экономика",
    2: "Продукт, дифференциация",
    3: "Каналы и доля",
    4: "Спрос сегмента",
    5: "Структура рынка, маржа",
    6: "Макро и регулирование",
}

# Линии 1–3 — то, что компания делает сама. Линии 4–6 — то, во что она
# поставлена. Тип ограничения следует отсюда, а не из текста.
STRENGTH_LINES = (1, 2, 3)

ConstraintKind = Literal["competence", "structural"]

KIND_TITLES: dict[ConstraintKind, str] = {
    "competence": "компетенция",
    "structural": "структурное",
}


def yin_profile(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Профиль линии по портфелю: сколько направлений слабы, сколько сильны и
    сколько из тех и других подвижны.

    Четыре числа вместо одного, потому что «слабость у трёх из пяти» ещё не
    вывод: важно, есть ли на что опереться среди оставшихся и хватает ли
    энергии на исправление.

    ДЕЛЬТА ЛИНИИ (delta_line) — назревшие минус перегретые ПО ЭТОЙ ЛИНИИ
    во всём портфеле. Не путать с дельтой портфеля (delta_portfolio, та самая
    Δ в шапке) и с дельтой направления (delta_direction, входит в индекс V
    с весом 0,20).

    Порядок — от самой частой слабости к самой редкой; при равенстве младшая
    линия первой, иначе два одинаковых расчёта дадут таблицы в разном порядке.
    """
    total = len(results)
    rows = []
    for line in range(1, 7):
        weak = [r for r in results if r["symbols"][line - 1] == YIN]
        strong = [r for r in results if r["symbols"][line - 1] != YIN]
        ripe = [r for r in weak
                if (r.get("mobility") or {}).get(str(line)) == "old_yin"]
        hot = [r for r in strong
               if (r.get("mobility") or {}).get(str(line)) == "old_yang"]
        rows.append({
            "line": line,
            "factor": LINE_FACTORS[line],
            "yin": len(weak),
            "yin_ripe": len(ripe),
            "yang": len(strong),
            "yang_hot": len(hot),
            "delta_line": len(ripe) - len(hot),
            "total": total,
            "strong_names": [r["name"] for r in strong],
        })
    rows.sort(key=lambda r: (-r["yin"], r["line"]))
    return rows


def support_note(row: dict[str, Any]) -> str:
    """
    На что опереться по этой линии. Перегретая сильная позиция опорой не
    является: она держится на пределе и без закрепления деградирует.
    """
    yang, hot = row["yang"], row["yang_hot"]
    if yang == 0:
        return "сильных позиций нет вовсе"
    if yang == 1:
        if hot == 1:
            return "единственная сильная позиция перегрета: опереться не на что"
        return f"единственная сильная позиция — у направления «{row['strong_names'][0]}»"
    if hot == 1:
        return f"из {yang} сильных позиций одна перегрета: опора неустойчива"
    if hot > 1:
        return f"из {yang} сильных позиций перегрето {hot}: опора неустойчива"
    return f"сильных позиций {yang}, ни одна не перегрета"


DELTA_LINE_READINGS = {
    1: "энергия для исправления есть: назревших больше, чем перегретых",
    0: "сколько назрело, столько же и перегрето — по линии будет замена, не рост",
    -1: "линия скорее просядет, чем выправится: перегретых больше",
}


def delta_line_reading(delta: int) -> str:
    return DELTA_LINE_READINGS[(delta > 0) - (delta < 0)]


def _reading(row: dict[str, Any]) -> str:
    """
    Прочтение строки таблицы. Следует из чисел, не из контента.

    Уточнение по опоре добавляется только там, где слабость признана
    повторяющейся: в остальных случаях оно уводит внимание от вывода.
    """
    yin, total = row["yin"], row["total"]
    if yin == 0:
        return "Не является ограничением портфеля"
    if yin == total:
        return "Слабость у всех направлений: это свойство компании, а не продукта"
    if yin == 1:
        return "Единичный случай — свойство направления, а не компании"
    return f"Повторяется у {yin} направлений из {total}; {support_note(row)}"


def yin_table(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = yin_profile(results)
    for row in rows:
        row["reading"] = _reading(row)
    return rows


def constraints(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Именованные ограничения компании: линии, слабые у большинства направлений.

    Порог — строгое большинство. Слабость у половины портфеля ещё может быть
    совпадением; слабость у большинства совпадением быть перестаёт.

    На контрольном кейсе правило отбирает линию 5 (4 из 5) и линию 3 (3 из 5)
    и не отбирает линии 1 и 2 (по 2 из 5) — те же две, что названы в образце,
    и в том же порядке.
    """
    total = len(results)
    out = []
    for row in yin_profile(results):
        if row["yin"] * 2 <= total:
            continue
        kind: ConstraintKind = (
            "competence" if row["line"] in STRENGTH_LINES else "structural"
        )
        if kind == "structural":
            body = (
                f"Линия {row['line']} — {row['factor'].lower()} — слаба "
                f"у {row['yin']} направлений из {total}. Это свойство рынка, "
                "на котором работает компания, а не результат её действий: "
                "внутри направлений оно не исправляется. Направление с другим "
                "рынком перестаёт быть побочным экспериментом."
            )
        else:
            body = (
                f"Линия {row['line']} — {row['factor'].lower()} — слаба "
                f"у {row['yin']} направлений из {total}. Это корпоративная "
                "компетенция, а не проблема отдельных продуктов: вкладывать "
                "в неё порознь по каждому направлению значит несколько раз "
                "оплатить одну и ту же кривую обучения."
            )
        body += f" Опора: {support_note(row)}."
        if row["delta_line"] != 0:
            body += f" {delta_line_reading(row['delta_line']).capitalize()}."
        out.append({
            "line": row["line"], "factor": row["factor"], "yin": row["yin"],
            "yang": row["yang"], "yang_hot": row["yang_hot"],
            "delta_line": row["delta_line"],
            "total": total, "kind": kind, "kind_title": KIND_TITLES[kind],
            "body": body,
        })
    return out


def metric_readings(summary: dict[str, Any]) -> list[dict[str, str]]:
    """Четыре агрегата портфеля с прочтением. Пороги — в коде, не в контенте."""
    positions = summary["sum_positions"]
    positions_max = summary["sum_positions_max"] or 1
    share = positions / positions_max * 100
    if share < 40:
        positions_reading = "Портфель слабый по совокупности позиций"
    elif share < 55:
        positions_reading = "Портфель около середины"
    elif share < 70:
        positions_reading = "Портфель чуть выше середины"
    else:
        positions_reading = "Портфель сильный по совокупности позиций"

    turbulence = summary["turbulence"]
    max_moving = 6 * summary["objects"]
    moving_share = turbulence / max_moving * 100 if max_moving else 0
    if turbulence == 0:
        turbulence_reading = ("Подвижных линий нет: конфигурация стабильна, "
                              "в том числе возможен стабильный упадок")
    elif moving_share < 10:
        turbulence_reading = "Низкая энергия перехода"
    elif moving_share < 25:
        turbulence_reading = "Умеренная энергия перехода"
    else:
        turbulence_reading = "Высокая доля подвижных линий: фаза широкой трансформации"

    delta = summary["delta"]
    if delta == 0:
        delta_reading = ("Назревших слабостей ровно столько же, сколько "
                         "перегретых сил: прироста «в целом» не будет, будет "
                         "замена источника выручки")
    elif delta > 0:
        delta_reading = "Назревших слабостей больше, чем перегретых сил: портфель в фазе роста"
    else:
        delta_reading = ("Перегретых сил больше, чем назревших слабостей: "
                         "ресурс уйдёт на защиту достигнутого")

    cells = summary["distinct_cells"]
    if cells <= 1:
        cells_reading = "Все направления в одной ячейке — формулировки их не различили"
    elif cells == 2:
        cells_reading = "Различение слабое: направления почти не разошлись по матрице"
    else:
        cells_reading = "Направления дифференцированы"

    return [
        {"name": "Сумма позиций", "value": f"{positions} / {positions_max}",
         "reading": positions_reading},
        {"name": "Подвижных линий, T", "value": f"{turbulence} / {max_moving}",
         "reading": turbulence_reading},
        {"name": "Дельта портфеля Δ", "value": f"+{delta}" if delta > 0 else str(delta),
         "reading": delta_reading},
        {"name": "Занято ячеек", "value": f"{cells} из 9",
         "reading": cells_reading},
    ]


def tact_note(results: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    """
    Правило такта: не более двух направлений в активной трансформации.
    Ограничение управленческого ресурса, а не денег.
    """
    active = sum(
        1 for r in results if (r.get("target_lines") or r.get("risk_lines"))
    )
    return (
        f"Такт: {summary['turbulence']} подвижных линий на {active} направлениях. "
        "Рекомендуемое ограничение — не более двух направлений в активной "
        "трансформации одновременно. Узким местом станет управленческий ресурс, "
        "а не деньги."
    )

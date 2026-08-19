# -*- coding: utf-8 -*-
"""
Три уровня (сань-цай): разрез шести линий контура по парам.

ЧИСТЫЕ ФУНКЦИИ. Ни БД, ни файловой системы, ни времени.
Вход — снимок result из contour_scoring.compute_contour_result,
выход — список из трёх уровней.

Новых данных не добавляет: уровни детерминированы полем lines, которое уже
лежит в снимке, и не зависят ни от одной правимой настройки. Поэтому в снимок
не пишутся, а пересчитываются при сборке отчёта. Воспроизводимость не страдает.

Основание: 64dao_line_semantics_adr.md, инвариант И3 (пары линий 1-2, 3-4, 5-6).

ВНИМАНИЕ. Соответствие символов ярлыкам отличается от документа «Business State
Diagnostic»: там символ означал режим работы (Ян как активность), здесь — балл
линии выше порога 2.50, то есть зрелость. При зрелостной шкале Инь+Инь нельзя
называть накоплением. Разбор: 64dao_levels_block_plan.md §2.2.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.contours import LINE_KEYS, LINE_TITLES

# Ключ, заголовок, вопрос уровня, пара линий снизу вверх.
LEVELS: tuple[tuple[str, str, str, tuple[int, int]], ...] = (
    ("earth",  "Земля",   "способность исполнять",  (1, 2)),
    ("human",  "Человек", "носитель способности",   (3, 4)),
    ("heaven", "Небо",    "направление и контекст", (5, 6)),
)

# Нижняя линия пары — что делается, верхняя — чем обеспечено и санкционировано.
STATE_LABELS: dict[str, str] = {
    "AA": "Развитие",    # обе опоры несут нагрузку
    "AB": "Импульс",     # действие есть, обеспечения нет
    "BA": "Оформление",  # обеспечение есть, действия нет
    "BB": "Стойкость",   # ресурса хватает только на удержание
}

# Линия 5 измеряет обстановку, а не компанию: Инь на ней — давление среды,
# а не провал функции. Оговорка обязательна в карточке (план §4.4).
HEAVEN_CAVEAT = (
    "Линия 5 описывает обстановку, а не компанию: Инь на ней означает давление "
    "внешней среды, а не слабость функции. Уровень читается как соотношение "
    "давления среды и наличия направления, а не как зрелость."
)


# Раздел уровней соседствует с триграммами и обязан объяснить, чем от них
# отличается. Без этого он читается как второе, спорящее с первым заключение
# (64dao_levels_block_plan.md §4.3).
CUTS_CAVEAT = (
    "Триграммы и уровни это два разреза одних и тех же шести ответов, а не две "
    "независимые оценки. Триграммы отвечают на вопрос, где функция сильна: внутри "
    "себя или в своём контексте. Уровни отвечают на другой: чем именно функция "
    "держится, исполнением, людьми или направлением."
)


def _round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def levels_of(result: dict) -> list[dict]:
    """
    Три уровня из снимка контура. Пустой список, если снимок неполный:
    legacy-диагностики обязаны рендериться без исключения (мастер-документ, №7).
    """
    raw = (result or {}).get("lines") or []
    by_line = {l["line"]: l for l in raw if isinstance(l, dict) and "line" in l}
    current = (result or {}).get("combination_current") or ""
    if len(by_line) < 6 or len(current) != 6:
        return []
    if any(ch not in ("A", "B") for ch in current):
        return []

    resulting = (result or {}).get("combination_resulting") or ""
    if len(resulting) != 6 or any(ch not in ("A", "B") for ch in resulting):
        resulting = ""

    out: list[dict] = []
    for key, title, question, (lo, hi) in LEVELS:
        low, high = by_line[lo], by_line[hi]
        code = current[lo - 1] + current[hi - 1]
        moving = [n for n, l in ((lo, low), (hi, high)) if l.get("moving")]
        code_res = (resulting[lo - 1] + resulting[hi - 1]) if (moving and resulting) else None
        out.append({
            "level": key,
            "title": title,
            "question": question,
            "lines": [lo, hi],
            "line_titles": [LINE_TITLES[LINE_KEYS[lo - 1]], LINE_TITLES[LINE_KEYS[hi - 1]]],
            "symbols": [current[lo - 1], current[hi - 1]],
            "code": code,
            "label": STATE_LABELS[code],
            "moving": len(moving),
            "moving_lines": moving,
            "code_resulting": code_res,
            "label_resulting": STATE_LABELS[code_res] if code_res else None,
            "content_key": f"{key}_{code}",
            "score": _round2((float(low.get("score") or 0) + float(high.get("score") or 0)) / 2),
            "caveat": HEAVEN_CAVEAT if key == "heaven" else None,
        })
    return out

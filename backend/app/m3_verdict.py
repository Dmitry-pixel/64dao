# -*- coding: utf-8 -*-
"""
Метод 3 — вердикт направления по позиции в матрице GE/McKinsey.

Вердикт складывается из двух слоёв.

Первый — зона. Девять клеток матрицы дают базовую рекомендацию: та самая
сетка «Инвестировать / Защищать / Удерживать / Собирать урожай / Выходить».
Это классика, и она узнаваема — на неё отчёт и опирается.

Второй — конфигурация линий. Классическая матрица выдала бы двум
направлениям одной клетки одинаковую рекомендацию. Метод 3 этого не делает:
направления 2 и 3 контрольного кейса стоят в одной клетке и получают
противоположные вердикты, потому что у первого есть подвижные линии, а у
второго нет. Подвижность — это внутренний запрос на изменение: там, где его
нет, деньги не срабатывают, сколько бы ни обещала зона.

Поэтому таблица ниже двумерная: зона задаёт намерение, подвижность —
что с этим намерением делать сейчас.

Проверка: правило воспроизводит все пять вердиктов образца
64dao-portfolio-report-sample.html версии 0.2 — см. test_m3_verdict.
"""
from __future__ import annotations

from typing import Any, Literal

from app import m3_scoring as sc

Stance = Literal["invest", "protect", "build", "hold", "limited", "harvest", "exit"]
Mobility = Literal["both", "target", "risk", "stable"]

# ── Девять зон ────────────────────────────────────────────────────────────────
# Ключ — (конкурентная сила, привлекательность рынка), значения как в снимке
# расчёта: low / mid / high, где high по силе означает «сильная».
ZONES: dict[tuple[str, str], tuple[Stance, str, str]] = {
    ("high", "high"): ("invest",  "Инвестировать",           "Invest / Grow"),
    ("mid",  "high"): ("protect", "Защищать",                "Protect / Refocus"),
    ("low",  "high"): ("build",   "Избирательно развивать",  "Selectively Build"),
    ("high", "mid"):  ("protect", "Защищать",                "Protect / Refocus"),
    ("mid",  "mid"):  ("hold",    "Удерживать",              "Hold / Maintain"),
    ("low",  "mid"):  ("limited", "Ограниченное развитие",   "Limited Harvest"),
    ("high", "low"):  ("hold",    "Удерживать",              "Hold / Maintain"),
    ("mid",  "low"):  ("harvest", "Собирать урожай",         "Harvest"),
    ("low",  "low"):  ("exit",    "Избегать / выходить",     "Divest / Exit"),
}

# ── Вердикт: зона × подвижность ───────────────────────────────────────────────
# «stable» — подвижных линий нет вовсе. В сильных зонах это значит «идёт как
# идёт», в слабых — что вкладывать не во что: слабость не назрела и внутрен-
# него давления на изменение не создаёт.
VERDICTS: dict[tuple[Stance, Mobility], str] = {
    ("invest",  "target"): "Инвестировать в рост",
    ("invest",  "risk"):   "Инвестировать, закрепив достигнутое",
    ("invest",  "both"):   "Инвестировать и закреплять одновременно",
    ("invest",  "stable"): "Наращивать по плану",

    ("protect", "target"): "Защищать, вкладывая в назревшее",
    ("protect", "risk"):   "Защищать: закрепить перегретое",
    ("protect", "both"):   "Защищать, со сроком",
    ("protect", "stable"): "Защищать, не наращивая",

    ("build",   "target"): "Инвестировать точечно",
    ("build",   "risk"):   "Развивать избирательно, закрепив достигнутое",
    ("build",   "both"):   "Развивать избирательно, со сроком",
    ("build",   "stable"): "Отложить: рынок хорош, взять его нечем",

    ("hold",    "target"): "Удерживать, проработав назревшее",
    ("hold",    "risk"):   "Не инвестировать в рост. Закрепить",
    ("hold",    "both"):   "Удерживать, со сроком",
    ("hold",    "stable"): "Удерживать, не развивать",

    ("limited", "target"): "Ограниченно развивать по назревшему",
    ("limited", "risk"):   "Ограниченно развивать, закрепив достигнутое",
    ("limited", "both"):   "Селективно, со сроком",
    ("limited", "stable"): "Пересборка или выход",

    ("harvest", "target"): "Собирать урожай, сняв назревшее",
    ("harvest", "risk"):   "Собирать урожай, закрепив достигнутое",
    ("harvest", "both"):   "Собирать урожай, со сроком",
    ("harvest", "stable"): "Собирать урожай",

    ("exit",    "target"): "Пересобрать или выходить",
    ("exit",    "risk"):   "Выходить, защитив выручку",
    ("exit",    "both"):   "Выходить, со сроком",
    # Не «Пересборка или выход», как у limited+stable: там средний рынок,
    # и пересборке есть во что упереться. Здесь слабы обе оси, а stable
    # означает, что и внутреннего запроса на изменение нет. Одинаковый
    # текст на двух разных ячейках стирал различие, которое метод меряет.
    ("exit",    "stable"): "Не вкладывать: пересобирать нечем",
}

# Переопределения для сокращённого режима: только те ключи, где формулировка
# отвечает на вопрос «среди чего выбирать». При одном направлении выбирать
# не среди чего, и «точечно», «избирательно», «селективно» повисают в воздухе,
# а «отложить» означает «займись другими» — а других нет.
# Остальные двадцать один ярлык берутся из базовой таблицы: копировать их
# значит завести две версии, которые разойдутся при первой правке.
VERDICTS_REDUCED: dict[tuple[Stance, Mobility], str] = {
    ("build",   "target"): "Вкладывать в назревшее, а не в рост целиком",
    ("build",   "risk"):   "Развивать по назревшим линиям, закрепив достигнутое",
    ("build",   "both"):   "Развивать по назревшим линиям, окно ограничено",
    ("build",   "stable"): "Рынок хорош, взять его нечем: сначала строить силу",
    ("limited", "both"):   "По назревшим линиям, окно ограничено",
}


MOBILITY_NOTE: dict[Mobility, str] = {
    "target": "есть назревшее изменение — энергия для него есть сейчас",
    "risk": "позиция перегрета: без закрепления она деградирует",
    "both": "есть и назревшее изменение, и перегрев — окно ограничено по времени",
    "stable": "подвижных линий нет: внутреннего запроса на изменение система "
              "не фиксирует",
}


def mobility_state(result: dict[str, Any]) -> Mobility:
    has_target = bool(result.get("target_lines"))
    has_risk = bool(result.get("risk_lines"))
    if has_target and has_risk:
        return "both"
    if has_target:
        return "target"
    if has_risk:
        return "risk"
    return "stable"


def zone_of(result: dict[str, Any]) -> tuple[Stance, str, str]:
    key = (result["cell_strength"], result["cell_attract"])
    if key not in ZONES:
        raise ValueError(f"Неизвестная зона матрицы: {key}")
    return ZONES[key]


def verdict_for(result: dict[str, Any]) -> dict[str, Any]:
    """
    Вердикт направления.

    Возвращает разложенный результат, а не готовую фразу: отчёту нужен
    короткий императив в одной вёрстке и та же рекомендация строкой таблицы
    в другой, а собирать их обратной разборкой текста — плохая идея.

    Ранги V и Z в вердикт не входят, но дают приписку: направление, первое
    по Z, защищают первым независимо от того, что говорит его зона.
    """
    stance, zone_ru, zone_en = zone_of(result)
    state = mobility_state(result)
    key = (stance, state)
    # Признак ставится на результат при сборке отчёта, поэтому все три места
    # вызова verdict_for видят его без правки сигнатуры.
    verdict = (VERDICTS_REDUCED.get(key) or VERDICTS[key]) if result.get("reduced") \
        else VERDICTS[key]

    notes: list[str] = [MOBILITY_NOTE[state]]
    if result.get("v_rank") == 1:
        notes.append("первое место по приоритету вложения")
    if result.get("z_rank") == 1:
        notes.append("первое место в очереди защиты")

    return {
        "zone_ru": zone_ru,
        "zone_en": zone_en,
        "stance": stance,
        "mobility": state,
        "verdict": verdict,
        "notes": notes,
    }


# ── Траектория: в какую ячейку матрицы уводит цель и куда сползает риск ───────
# Ячейку задаёт триграмма, а не координата: нижняя (линии 1–3) — конкурентная
# сила, верхняя (4–6) — привлекательность рынка. Символы целевой гексаграммы
# получаются инверсией старых Инь, рисковой — инверсией старых Ян, поэтому их
# ячейки считаются точно, без допущений.
#
# Правило свёртки — общее с расчётом (m3_scoring.cell_of): сумма отраслевых
# весов линий-Ян. Своя копия здесь считала по числу Ян и после перехода на
# веса разошлась бы с карточкой: одно направление получило бы в шапке одну
# ячейку, а в тексте перехода — другую. `before` пересчитывает ТЕКУЩУЮ ячейку,
# так что расхождение было бы видно прямо в одном абзаце.

CELL_NOM = {"low": "низкая", "mid": "средняя", "high": "высокая"}
CELL_GEN = {"low": "низкой", "mid": "средней", "high": "высокой"}
CELL_ACC = {"low": "низкую", "mid": "среднюю", "high": "высокую"}

_ORDER = {"low": 0, "mid": 1, "high": 2}

AXIS_NAMES = {"strength": "конкурентная сила", "attract": "привлекательность рынка"}


def cells_of(
    symbols: str,
    weights: dict[str, int],
    config: dict | None = None,
) -> tuple[str, str]:
    """(ячейка по силе, ячейка по привлекательности) из шести символов."""
    if len(symbols) != 6:
        raise ValueError(f"Ожидалось шесть символов, получено {len(symbols)!r}")
    return (
        sc.cell_of(symbols, "strength", weights, config),
        sc.cell_of(symbols, "attract", weights, config),
    )


def symbols_after(symbols: str, lines: list[int]) -> str:
    """Символы после инверсии указанных линий. Линии нумеруются с единицы."""
    chars = list(symbols)
    for n in lines:
        chars[n - 1] = "B" if chars[n - 1] == "A" else "A"
    return "".join(chars)


def _with_preposition(preposition: str, word: str) -> str:
    """«с средней» — не по-русски. Перед свистящей ставится «со»."""
    if preposition == "с" and word.startswith("ср"):
        return f"со {word}"
    return f"{preposition} {word}"


def transition(result: dict[str, Any], kind: Literal["target", "risk"],
               config: dict | None = None) -> dict | None:
    """
    Переход по матрице: из какой ячейки в какую уводит цель или риск.

    Возвращает None, если вектора нет или он не меняет ни одной ячейки —
    подвижная линия может остаться внутри своей триграммы и зону не сдвинуть.
    Печатать «переходит из средней в среднюю» незачем.
    """
    lines = result.get(f"{kind}_lines") or []
    to_hex = result.get(f"{kind}_hex")
    if not lines or to_hex is None:
        return None

    weights = result.get("weights")
    if not weights:
        # Снимок до ревизии 030 весов не хранит. Пересчитать ячейку перехода
        # нечем, а считать её по старому правилу значит поставить в один
        # абзац две несовместимые ячейки. Молчим.
        return None
    before = cells_of(result["symbols"], weights, config)
    after = cells_of(symbols_after(result["symbols"], lines), weights, config)

    moves = []
    for axis, index in (("strength", 0), ("attract", 1)):
        if before[index] == after[index]:
            continue
        frm, to = before[index], after[index]
        name = AXIS_NAMES[axis]
        if kind == "target" and _ORDER[to] > _ORDER[frm]:
            phrase = f"{name} переходит из {CELL_GEN[frm]} в {CELL_ACC[to]}"
        else:
            verb = "падает" if _ORDER[to] < _ORDER[frm] else "переходит"
            phrase = f"{name} {verb} {_with_preposition('с', CELL_GEN[frm])} до {CELL_GEN[to]}"
        moves.append({"axis": axis, "from": frm, "to": to, "phrase": phrase})

    if not moves:
        return None

    return {
        "kind": kind,
        "from_hex": result["current_hex"],
        "to_hex": to_hex,
        "from_cells": before,
        "to_cells": after,
        "moves": moves,
        "phrase": ", ".join(m["phrase"] for m in moves),
    }


# ── Очередь исполнения: почему направление стоит именно здесь ─────────────────
# Ранг Z отвечает на другой вопрос, чем ранг V: не «где деньги дадут эффект»,
# а «что нельзя потерять и что горит». Причина места в очереди складывается
# из двух вещей — размера направления и наличия перегрева.
CRITICAL_SHARE = 40.0   # доля, при которой цена ошибки становится предельной
SMALL_SHARE = 10.0      # доля, ниже которой отсрочка почти ничего не стоит


def execution_reason(result: dict[str, Any], share: float | None) -> str:
    """
    Пояснение к месту в очереди исполнения.

    Воспроизводит формулировки образца на всех пяти направлениях
    контрольного кейса — см. test_m3_verdict.
    """
    has_risk = bool(result.get("risk_lines"))
    has_target = bool(result.get("target_lines"))

    if has_risk:
        if share is not None and share >= CRITICAL_SHARE:
            return (f"{_share(share)}% выручки на перегретой позиции: "
                    "цена ошибки максимальна")
        if share is not None:
            return (f"{_share(share)}% выручки, позиция на пике — "
                    "окно закрывается само")
        return "перегрев: окно закрывается независимо от ваших действий"

    if not has_target:
        stance = zone_of(result)[0]
        if stance in ("limited", "exit"):
            return "стабильно, решение принимается вне маршрута"
        return "стабильно, срочности нет"

    if share is not None and share < SMALL_SHARE:
        return (f"{_share(share)}% выручки, эрозии нет: "
                "отложить можно без потерь")
    return "назревшее изменение без перегрева: срочности нет"


def _share(value: float) -> str:
    """Доля целым числом, если она целая: «45», а не «45.0»."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


# ── Подпись ячейки ────────────────────────────────────────────────────────────
# «Низкая / Высокая» не говорит, чего низкая и чего высокая. Обе оси при этом
# разные по природе: горизонталь описывает компанию, вертикаль — рынок, и
# путать их нельзя. Поэтому подпись называет обе величины целиком.
AXIS_STRENGTH = "конкурентоспособность бизнеса"
AXIS_ATTRACT = "привлекательность рынка"


AXIS_SHORT = {"strength": "Сила", "attract": "Рынок"}


def market_label(overrides: int) -> str:
    """
    Подпись колонки «Рынок»: чей рыночный слой пошёл в расчёт.

    Подмена идёт попунктно, а не блоком целиком, поэтому частичное
    переопределение — рабочее состояние, а не недозаполненность. Число
    в скобках показывает глубину отличия; без него направление с одним
    переопределённым пунктом читалось бы наравне с полностью своим.

    Жила в m3_pdf и была продублирована на TypeScript в веб-отчёте.
    Переехала сюда, чтобы у формулировки осталось одно определение:
    PDF зовёт её напрямую, веб получает готовую строку в payload.
    """
    if overrides <= 0:
        return "Общий"
    return f"Свой ({overrides} из {sc.MARKET_ITEMS_TOTAL})"


def cell_breakdown_text(axis: str, detail: dict[str, Any]) -> str:
    """
    Как получился уровень оси: «Сила: Ян на Л2 (45) + Л3 (30) = 75 из 100 →
    высокая» (§10.1a).

    Строка отвечает на вопрос, который до неё висел в отчёте без ответа:
    почему направление с линией 4,00 стоит в низкой ячейке. Ответ — вес
    этого фактора в отрасли, и он печатается числом, проверяемым по
    таблице линий выше.

    Формулировка продублирована в веб-отчёте (`report/m3/[id]/page.tsx`,
    cellBreakdownText) — так же, как market_label. При правке менять обе;
    расхождение ловит test_m3_report_parity.
    """
    lines = detail.get("lines") or []
    if lines:
        parts = " + ".join(f"Л{w['line']} ({w['weight']})" for w in lines)
        got = f"Ян на {parts} = {detail['sum']}"
    else:
        got = f"Ян нет — {detail['sum']}"
    return (f"{AXIS_SHORT[axis]}: {got} из {detail['total']} → "
            f"{CELL_NOM[detail['level']]}")


def cell_label(cell_strength: str, cell_attract: str) -> str:
    """
    Подпись ячейки матрицы: «Низкая конкурентоспособность бизнеса /
    Высокая привлекательность рынка».

    Единственное место, где эта строка собирается. m3_service.build_report
    вызывает эту же функцию, иначе веб и PDF разойдутся в формулировке.
    """
    for value in (cell_strength, cell_attract):
        if value not in CELL_NOM:
            raise ValueError(f"Неизвестный уровень ячейки: {value!r}")
    return (f"{CELL_NOM[cell_strength].capitalize()} {AXIS_STRENGTH} / "
            f"{CELL_NOM[cell_attract].capitalize()} {AXIS_ATTRACT}")

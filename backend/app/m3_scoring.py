# -*- coding: utf-8 -*-
"""
Метод 3 «Матрица силы» — расчётное ядро.

ЧИСТЫЕ ФУНКЦИИ. Ни одного обращения к БД, файловой системе и времени.
На вход словари, на выход словари. Всё, что зависит от окружения, передаётся
параметром config (по умолчанию — DEFAULT_M3_CONFIG из m3_config).

Порядок вычислений — §3 инструкции разработчику:
  1. разрешение источника Л5/Л6 (ответ объекта, иначе ответ портфеля);
  2. инверсия реверсивных пунктов: v' = 5 - v;
  3. балл линии — среднее по 2 или 3 пунктам, округление до 2 знаков;
  4. правило арбитра;
  5. вето по убыточности;
  6. символ;
  7. подвижность;
  8. триграммы;
  9. ячейка матрицы;
 10. координаты по отраслевому пресету;
 11. текущая / целевая / рисковая гексаграммы;
 12. индексы V и Z;
 13. флаги объекта (после арбитра);
 14. портфельный слой;
 15. удержание вердиктов.

Ключевое отличие от Метода 2: целевая гексаграмма — инверсия ТОЛЬКО старых Инь,
рисковая — инверсия ТОЛЬКО старых Ян. Обе группы никогда не инвертируются вместе
(§14 спецификации).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.hexagrams import hexagram_by_code
from app.m3_config import DEFAULT_M3_CONFIG, industry_weights

# ── Алфавит и коды пунктов ────────────────────────────────────────────────────
# Буквы блоков — КИРИЛЛИЦА. Латинские P/H/A визуально неотличимы и ломают
# сопоставление с анкетой; тест test_item_codes_are_cyrillic это фиксирует.
BLOCK_MARKET = "Р"    # Р — рыночный блок, уровень портфеля
BLOCK_OBJECT = "Н"    # Н — объектный блок, уровень направления
BLOCK_ARBITER = "А"   # А — адаптивные пункты-арбитры
OVERRIDE = "*"             # Р1* … Р6* — переопределение рынка по направлению

YANG, YIN = "A", "B"
OLD_YANG, OLD_YIN = "old_yang", "old_yin"
LINES = (1, 2, 3, 4, 5, 6)

# Пункт -> линия.
MARKET_ITEMS_TOTAL = 6     # Р1…Р6 — столько пунктов у рыночного блока
MARKET_ITEM_LINE: dict[str, int] = {f"{BLOCK_MARKET}{i}": (5 if i <= 3 else 6) for i in range(1, 7)}
OVERRIDE_ITEM_LINE: dict[str, int] = {f"{k}{OVERRIDE}": v for k, v in MARKET_ITEM_LINE.items()}
OBJECT_ITEM_LINE: dict[str, int] = {f"{BLOCK_OBJECT}{i}": (i + 1) // 2 for i in range(1, 9)}
ARBITER_ITEM_LINE: dict[str, int] = {f"{BLOCK_ARBITER}{i}": i for i in range(1, 5)}

ITEM_LINE: dict[str, int] = {
    **MARKET_ITEM_LINE, **OVERRIDE_ITEM_LINE, **OBJECT_ITEM_LINE, **ARBITER_ITEM_LINE
}

# Реверсивные пункты: балл' = 5 - балл.
REVERSE_ITEMS: frozenset[str] = frozenset({
    f"{BLOCK_MARKET}3", f"{BLOCK_MARKET}6",
    f"{BLOCK_MARKET}3{OVERRIDE}", f"{BLOCK_MARKET}6{OVERRIDE}",
    f"{BLOCK_OBJECT}2", f"{BLOCK_OBJECT}4", f"{BLOCK_OBJECT}6", f"{BLOCK_OBJECT}8",
})

# Базовые пункты линии (без арбитра) — по ним считается правило показа арбитра.
BASE_ITEMS_BY_LINE: dict[int, tuple[str, ...]] = {
    1: (f"{BLOCK_OBJECT}1", f"{BLOCK_OBJECT}2"),
    2: (f"{BLOCK_OBJECT}3", f"{BLOCK_OBJECT}4"),
    3: (f"{BLOCK_OBJECT}5", f"{BLOCK_OBJECT}6"),
    4: (f"{BLOCK_OBJECT}7", f"{BLOCK_OBJECT}8"),
    5: (f"{BLOCK_MARKET}1", f"{BLOCK_MARKET}2", f"{BLOCK_MARKET}3"),
    6: (f"{BLOCK_MARKET}4", f"{BLOCK_MARKET}5", f"{BLOCK_MARKET}6"),
}
ARBITER_BY_LINE: dict[int, str] = {v: k for k, v in ARBITER_ITEM_LINE.items()}

VALID_RAW = (1, 2, 3, 4)

PROFITABILITY = ("profitable", "marginal", "unprofitable", "unknown")

# Уровень ячейки задаётся суммой отраслевых весов линий-Ян в триграмме.
# Пороги — в конфиге (cell_weight_thresholds), см. §10.1 передачи.
# Прежнее правило считало Ян, не глядя на веса, и отраслевой пресет
# на вердикт не влиял вовсе: вердикт берётся из ячейки.
AXIS_LINES: dict[str, tuple[int, int, int]] = {"strength": (1, 2, 3), "attract": (4, 5, 6)}
CELL_LABEL_RU = {"low": "Низкая", "mid": "Средняя", "high": "Высокая"}


# Какие портфельные флаги удерживают вердикты аллокации.
#
# UNIFORM_PORTFOLIO и SELF_INFLATION говорят, что анкете нельзя верить:
# одинаковые клетки у всех направлений и сплошь завышенные баллы означают,
# что заполняли не глядя. На таких данных распределять деньги нельзя.
#
# RANK_MISMATCH здесь намеренно НЕТ. Расхождение порядка собственника
# с расчётом данные не портит — оно и есть содержательный результат
# диагностики. Удерживая на нём вердикты, отчёт говорил бы только тогда,
# когда и так согласен с собственником, то есть никогда не спорил бы.
# Расхождение показывается разделом (m3_portfolio.rank_comparison).
HOLDING_FLAGS = ("UNIFORM_PORTFOLIO", "SELF_INFLATION")


class M3ScoringError(ValueError):
    """Базовая ошибка расчётного ядра Метода 3."""


class InvalidAnswerError(M3ScoringError):
    """Значение ответа вне {1,2,3,4,None}."""


class LineUndefinedError(M3ScoringError):
    """Все пункты линии — «не знаю»: балл не определяется."""

    def __init__(self, line: int):
        self.line = line
        super().__init__(f"Линия {line}: все пункты без ответа — балл не определяется")


class PortfolioSizeError(M3ScoringError):
    """Число направлений вне допустимого диапазона."""


# ── Округление ────────────────────────────────────────────────────────────────
# Банковское округление float даёт 2,675 -> 2,67 и расходится с шаблоном пилота,
# построенным на ROUND_HALF_UP. Считаем через Decimal.
def _round(value: float, digits: int) -> float:
    q = Decimal(1).scaleb(-digits)
    return float(Decimal(repr(float(value))).quantize(q, rounding=ROUND_HALF_UP))


def r2(value: float) -> float:
    return _round(value, 2)


def r4(value: float) -> float:
    return _round(value, 4)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ── 1–2. Разрешение источника и инверсия ──────────────────────────────────────
def effective_value(item_code: str, raw: int | None) -> float | None:
    """Инверсия реверсивных пунктов: балл' = 5 - балл (§8.1)."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int) or raw not in VALID_RAW:
        raise InvalidAnswerError(f"Пункт {item_code}: значение {raw!r} вне {{1,2,3,4,None}}")
    return float(5 - raw) if item_code in REVERSE_ITEMS else float(raw)


def resolve_line_items(
    line: int,
    portfolio_answers: dict[str, int | None],
    object_answers: dict[str, int | None],
) -> list[tuple[str, float]]:
    """
    Эффективные баллы пунктов линии в порядке анкеты.

    Линии 5 и 6: ответ объекта (Р*), если он есть; иначе ответ портфеля (Р).
    Скрининг-вопросы управляют только показом Р* на фронте — на расчёт они
    не влияют: источником является наличие ответа, а не флаг скрининга.
    Линии 1–4: пункты Н плюс арбитр А, если он отвечен.
    """
    out: list[tuple[str, float]] = []
    for code in BASE_ITEMS_BY_LINE[line]:
        if line in (5, 6):
            override = f"{code}{OVERRIDE}"
            if object_answers.get(override) is not None:
                raw, src = object_answers[override], override
            else:
                raw, src = portfolio_answers.get(code), code
        else:
            raw, src = object_answers.get(code), code
        value = effective_value(src, raw)
        if value is not None:
            out.append((src, value))

    arbiter = ARBITER_BY_LINE.get(line)
    if arbiter is not None and object_answers.get(arbiter) is not None:
        out.append((arbiter, effective_value(arbiter, object_answers[arbiter])))
    return out


def market_override_count(object_answers: dict[str, int | None]) -> int:
    """
    Сколько пунктов рынка направление переопределяет своими ответами (0–6).

    Признак тот же, что и в resolve_line_items: ответ Р* существует и он не
    «не знаю» (value IS NULL). Флаги скрининга не учитываются — они говорят,
    что спросили, а не что ответили.

    Живёт рядом с правилом подмены намеренно: колонка «Рынок» в отчёте
    обязана описывать то, что сделал расчёт, а не то, что кажется похожим.
    Две копии этого условия разошлись бы при первой правке.
    """
    return sum(
        1 for i in range(1, MARKET_ITEMS_TOTAL + 1)
        if object_answers.get(f"{BLOCK_MARKET}{i}{OVERRIDE}") is not None
    )


# ── 3–4. Балл линии и правило арбитра ─────────────────────────────────────────
def line_score(
    line: int,
    portfolio_answers: dict[str, int | None],
    object_answers: dict[str, int | None],
) -> float:
    items = resolve_line_items(line, portfolio_answers, object_answers)
    if not items:
        raise LineUndefinedError(line)
    return r2(sum(v for _, v in items) / len(items))


def line_scores(
    portfolio_answers: dict[str, int | None],
    object_answers: dict[str, int | None],
) -> dict[int, float]:
    return {n: line_score(n, portfolio_answers, object_answers) for n in LINES}


def arbiter_required(
    portfolio_answers: dict[str, int | None],
    object_answers: dict[str, int | None],
    config: dict | None = None,
) -> list[int]:
    """
    По каким линиям нужен адаптивный пункт (§5, версия 0.2).

    Арбитр показывается, если |a - b| >= 2 либо (a + b) / 2 попадает в порог
    1,50 · 2,50 · 3,50. Второе условие покрывает все три порога метода: границу
    символа и обе границы подвижности.

    Линии 5 и 6 арбитров не имеют — там три базовых пункта.
    """
    cfg = config or DEFAULT_M3_CONFIG
    gap = cfg["arbiter_gap"]
    midpoints = set(cfg["arbiter_midpoints"])

    need: list[int] = []
    for line in (1, 2, 3, 4):
        values = []
        for code in BASE_ITEMS_BY_LINE[line]:
            v = effective_value(code, object_answers.get(code))
            if v is not None:
                values.append(v)
        if len(values) < 2:
            # Один ответ из двух — линия и так держится на одном пункте:
            # арбитр обязателен.
            need.append(line)
            continue
        a, b = values[0], values[1]
        if abs(a - b) >= gap or r2((a + b) / 2) in midpoints:
            need.append(line)
    return need


# ── 5–7. Вето, символ, подвижность ────────────────────────────────────────────
def symbol_of(score: float, config: dict | None = None) -> str:
    cfg = config or DEFAULT_M3_CONFIG
    return YANG if score >= cfg["symbol_threshold"] else YIN


def mobility_of(score: float, config: dict | None = None) -> str | None:
    cfg = config or DEFAULT_M3_CONFIG
    if score >= cfg["old_yang_threshold"]:
        return OLD_YANG
    if score <= cfg["old_yin_threshold"]:
        return OLD_YIN
    return None


# ── 9–10. Ячейка и координата ─────────────────────────────────────────────────
def cell_detail(
    symbols: str,
    axis: str,
    weights: dict[str, int],
    config: dict | None = None,
) -> dict:
    """
    Уровень ячейки по оси и его вывод.

    axis: 'strength' — нижняя триграмма Л1Л2Л3; 'attract' — верхняя Л4Л5Л6.

    Уровень — по сумме весов тех линий оси, что дали Ян. Не по их числу:
    веса внутри оси дают 100, и линия с весом 45 значит для позиции больше,
    чем линия с весом 25. Считая головы, расчёт объявлял сильный продукт в IT
    равным сильным каналам, а отраслевой пресет не доходил до вердикта.

    Возвращает и разбор, а не только уровень: карточка направления обязана
    показать, из чего уровень получился (§10.1a). Второй раз то же самое
    в слое отчёта не считается — разошлись бы.
    """
    cfg = config or DEFAULT_M3_CONFIG
    if axis not in AXIS_LINES:
        raise M3ScoringError(f"Неизвестная ось ячейки: {axis!r}")
    low, high = cfg["cell_weight_thresholds"]

    lines = AXIS_LINES[axis]
    yang = [{"line": n, "weight": weights[f"L{n}"]}
            for n in lines if symbols[n - 1] == YANG]
    total = sum(weights[f"L{n}"] for n in lines)
    got = sum(w["weight"] for w in yang)

    level = "low" if got < low else ("mid" if got < high else "high")
    return {"level": level, "sum": got, "total": total, "lines": yang}


def cell_of(
    symbols: str,
    axis: str,
    weights: dict[str, int],
    config: dict | None = None,
) -> str:
    return cell_detail(symbols, axis, weights, config)["level"]


def coordinate(scores: dict[int, float], weights: dict[str, int], axis: str) -> float:
    """Взвешенное среднее трёх линий оси по отраслевому пресету. Веса дают 100."""
    keys = (1, 2, 3) if axis == "strength" else (4, 5, 6)
    total = sum(weights[f"L{n}"] for n in keys)
    return r2(sum(scores[n] * weights[f"L{n}"] for n in keys) / total)


# ── 11. Гексаграммы ───────────────────────────────────────────────────────────
def _invert(symbols: str, positions: list[int]) -> str:
    chars = list(symbols)
    for n in positions:
        chars[n - 1] = YIN if chars[n - 1] == YANG else YANG
    return "".join(chars)


def trajectory(symbols: str, mobility: dict[int, str]) -> dict:
    """
    Целевая и рисковая гексаграммы — два независимых вычисления (§14).

    Целевая  = инверсия ТОЛЬКО старых Инь: куда придём, если проработаем назревшее.
    Рисковая = инверсия ТОЛЬКО старых Ян:  куда сползём, если не закрепим достигнутое.
    Обе группы никогда не инвертируются вместе — такая гексаграмма не описывает
    ни один реальный сценарий.
    """
    yin_lines = sorted(n for n, s in mobility.items() if s == OLD_YIN)
    yang_lines = sorted(n for n, s in mobility.items() if s == OLD_YANG)

    target_code = _invert(symbols, yin_lines) if yin_lines else None
    risk_code = _invert(symbols, yang_lines) if yang_lines else None

    return {
        "target_code": target_code,
        "target_hex": hexagram_by_code(target_code)[0] if target_code else None,
        "target_lines": yin_lines,
        "risk_code": risk_code,
        "risk_hex": hexagram_by_code(risk_code)[0] if risk_code else None,
        "risk_lines": yang_lines,
    }


# ── 12. Индексы приоритета ────────────────────────────────────────────────────
def indices(
    coord_strength: float,
    coord_attract: float,
    old_yin_count: int,
    old_yang_count: int,
    revenue_dynamics: float | None,
    revenue_share: float | None,
    config: dict | None = None,
) -> dict:
    """
    V — индекс вложения: куда осмысленно направить деньги на рост.
    Z — индекс защиты: что нельзя потерять и что горит.

    Доля выручки входит ТОЛЬКО в Z. Большая доля делает ошибку дороже, но сама
    по себе не является причиной вкладывать в рост; именно эта подмена ломала
    наивную формулу «позиция + Δ» (§16).

    A, S, D, M округляются до 4 знаков ДО подстановки в V. Причина не
    арифметическая, а отчётная: нормированные компоненты выводятся в отчёт,
    и V должен пересчитываться вручную из напечатанных значений. Так же
    устроен и шаблон пилота — расхождение видно на направлении 1 контрольного
    кейса (0,4909 против 0,4908 при подстановке неокруглённых).
    """
    cfg = config or DEFAULT_M3_CONFIG
    vw, zw = cfg["v_weights"], cfg["z_weights"]

    a = r4((coord_attract - 1) / 3)
    s = r4((coord_strength - 1) / 3)
    d = r4((old_yin_count - old_yang_count + 3) / 6)
    m = r4((clamp((revenue_dynamics or 0.0) / cfg["momentum_divisor"], -1.0, 1.0) + 1) / 2)

    v = vw["A"] * a + vw["S"] * s + vw["D"] * d + vw["M"] * m

    w = (revenue_share or 0.0) / 100.0
    r = min(old_yang_count / cfg["risk_yang_cap"], 1.0)
    z = zw["W"] * w + zw["R"] * r

    return {
        "a_norm": a, "s_norm": s, "d_norm": d, "m_norm": m,
        "v_index": r4(v), "z_index": r4(z),
    }


def rank_desc(values: list[float]) -> list[int]:
    """
    Ранги по убыванию: 1 — наибольшее значение.
    Ничья разрешается порядковым номером направления — ранги остаются
    перестановкой 1..n, иначе Спирмен и «два списка» отчёта теряют смысл.
    """
    order = sorted(range(len(values)), key=lambda i: (-values[i], i))
    ranks = [0] * len(values)
    for place, idx in enumerate(order, start=1):
        ranks[idx] = place
    return ranks


def spearman(a: list[int], b: list[int]) -> float | None:
    """Ранговая корреляция для перестановок без связей: 1 - 6*Σd² / (n(n²-1))."""
    n = len(a)
    if n != len(b) or n < 2:
        return None
    d2 = sum((x - y) ** 2 for x, y in zip(a, b))
    return r2(1 - 6 * d2 / (n * (n * n - 1)))


# ── Напряжения P1–P10 (§9) ────────────────────────────────────────────────────
def tensions(
    symbols: str,
    mobility: dict[int, str],
    config: dict | None = None,
) -> list[str]:
    """
    Не более трёх правил на направление, по возрастанию номера: на контрольном
    кейсе у одного направления сработали четыре, что размывает вывод.
    """
    cfg = config or DEFAULT_M3_CONFIG
    s = {n: symbols[n - 1] for n in LINES}
    moving = len(mobility)

    fired: list[str] = []
    if s[2] == YANG and s[3] == YIN:
        fired.append("P1")
    if s[3] == YANG and s[2] == YIN:
        fired.append("P2")
    if s[1] == YIN and s[4] == YANG:
        fired.append("P3")
    if s[4] == YANG and s[5] == YIN:
        fired.append("P4")
    if s[5] == YIN and s[6] == YANG:
        fired.append("P5")
    if mobility.get(3) == OLD_YANG:
        fired.append("P6")
    if moving >= 3:
        fired.append("P7")
    if s[1] == YIN and s[2] == YIN:
        fired.append("P8")
    if s[4] == YIN and s[5] == YIN and s[6] == YIN:
        fired.append("P9")
    if s[2] == YIN and s[3] == YIN:
        fired.append("P10")

    fired.sort(key=lambda p: int(p[1:]))
    return fired[: cfg["tensions_per_object_max"]]


# ── Ведущие линии (§6 инструкции) ─────────────────────────────────────────────
def leading_lines(scores: dict[int, float]) -> dict[str, int]:
    """
    Ведущая слабая — минимальный балл, при ничьей НИЖНЯЯ по номеру:
    фундамент важнее надстройки.
    Ведущая сильная — максимальный балл, при ничьей ВЕРХНЯЯ по номеру:
    чем выше линия, тем меньше она вами контролируется и тем важнее
    предупреждение об утрате.
    """
    lo = min(scores.values())
    hi = max(scores.values())
    weak = min(n for n in LINES if scores[n] == lo)
    strong = max(n for n in LINES if scores[n] == hi)
    return {"weak_line": weak, "strong_line": strong}


# ── 13. Флаги объекта ─────────────────────────────────────────────────────────
def object_flags(
    scores: dict[int, float],
    anchors: dict,
    veto_applied: bool,
    config: dict | None = None,
) -> list[str]:
    """Вычисляются ПОСЛЕ разрешения арбитра — иначе ловят снятые пороги."""
    cfg = config or DEFAULT_M3_CONFIG
    flags: list[str] = []

    bl_lo, bl_hi = cfg["borderline_line"]
    ny_lo, ny_hi = cfg["near_old_yang"]
    oi_lo, oi_hi = cfg["near_old_yin"]
    if any(bl_lo <= s <= bl_hi for s in scores.values()):
        flags.append("BORDERLINE_LINE")
    if any(ny_lo <= s <= ny_hi for s in scores.values()):
        flags.append("NEAR_OLD_YANG")
    if any(oi_lo <= s <= oi_hi for s in scores.values()):
        flags.append("NEAR_OLD_YIN")

    profitability = anchors.get("profitability")
    if veto_applied:
        flags.append("VETO_UNPROFITABLE")
    if profitability == "unknown":
        # Вето не запускает, но само по себе является диагнозом линии 1.
        flags.append("VETO_UNKNOWN")

    dyn = anchors.get("revenue_dynamics")
    share = anchors.get("revenue_share")
    rc = cfg["revenue_contradiction"]
    if dyn is not None and dyn <= rc["dynamics_max"] and scores[4] >= rc["l4_min"]:
        flags.append("REVENUE_CONTRADICTION")
    if profitability == "unprofitable" and scores[1] >= cfg["economy_contradiction"]["l1_min"]:
        flags.append("ECONOMY_CONTRADICTION")
    sc = cfg["scale_contradiction"]
    if share is not None and share >= sc["share_min"] and scores[3] <= sc["l3_max"]:
        flags.append("SCALE_CONTRADICTION")

    if len(set(scores.values())) == 1:
        flags.append("STRAIGHTLINING")

    return flags


# ── Расчёт одного направления ─────────────────────────────────────────────────
def score_object(
    obj: dict,
    portfolio_answers: dict[str, int | None],
    portfolio_industry_id: int | None = None,
    config: dict | None = None,
) -> dict:
    """
    obj: {
      'id', 'position', 'name',
      'answers': {'Н1':3, ..., 'Р1*':1, ...},
      'revenue', 'revenue_dynamics', 'revenue_share', 'profitability',
      'industry_id'  # переопределяет отраслевой пресет портфеля
    }
    """
    cfg = config or DEFAULT_M3_CONFIG
    answers = obj.get("answers") or {}

    scores = line_scores(portfolio_answers, answers)

    # 5. Вето: убыточное направление не может иметь сильную ресурсную линию —
    # самооценка здесь систематически завышена. Подвижность — по факт. баллу.
    veto_applied = obj.get("profitability") == "unprofitable"

    symbols_list = [symbol_of(scores[n], cfg) for n in LINES]
    if veto_applied:
        symbols_list[0] = YIN
    symbols = "".join(symbols_list)

    mobility = {n: m for n in LINES if (m := mobility_of(scores[n], cfg)) is not None}

    industry_id = obj.get("industry_id") or portfolio_industry_id
    weights = obj.get("weights") or industry_weights(industry_id, cfg)

    coord_strength = coordinate(scores, weights, "strength")
    coord_attract = coordinate(scores, weights, "attract")

    current_hex, current_name = hexagram_by_code(symbols)
    traj = trajectory(symbols, mobility)

    old_yin_count = sum(1 for m in mobility.values() if m == OLD_YIN)
    old_yang_count = sum(1 for m in mobility.values() if m == OLD_YANG)

    idx = indices(
        coord_strength, coord_attract, old_yin_count, old_yang_count,
        obj.get("revenue_dynamics"), obj.get("revenue_share"), cfg,
    )

    flags = object_flags(scores, obj, veto_applied, cfg)
    # Вето обнулило символ Л1, но балл остался в зоне старого Ян: инверсия такой
    # линии в рисковую гексаграмму описывает улучшение, а не эрозию. Случай
    # редкий, но молчать о нём нельзя.
    if veto_applied and mobility.get(1) == OLD_YANG:
        flags.append("VETO_MOBILITY_CONFLICT")

    detail_strength = cell_detail(symbols, "strength", weights, cfg)
    detail_attract = cell_detail(symbols, "attract", weights, cfg)
    cell_strength = detail_strength["level"]
    cell_attract = detail_attract["level"]

    return {
        "object_id": obj.get("id"),
        "position": obj.get("position"),
        "name": obj.get("name"),
        "scores": {f"l{n}": scores[n] for n in LINES},
        "symbols": symbols,
        "mobility": {str(n): m for n, m in mobility.items()},
        "moving_count": len(mobility),
        "old_yin_count": old_yin_count,
        "old_yang_count": old_yang_count,
        "cell_strength": cell_strength,
        "cell_attract": cell_attract,
        "cell_key": f"{cell_strength}_{cell_attract}",
        "cell_label": f"{CELL_LABEL_RU[cell_strength]} / {CELL_LABEL_RU[cell_attract]}",
        "cell_breakdown": {"strength": detail_strength, "attract": detail_attract},
        "coord_strength": coord_strength,
        "coord_attract": coord_attract,
        "current_hex": current_hex,
        "current_code": symbols,
        "current_name": current_name,
        **traj,
        **idx,
        "tensions": tensions(symbols, mobility, cfg),
        **leading_lines(scores),
        "flags": flags,
        "industry_id": industry_id,
        "weights": weights,
        "veto_applied": veto_applied,
    }


# ── 14–15. Портфельный слой ───────────────────────────────────────────────────
def score_portfolio(
    results: list[dict],
    owner_ranks: list[int] | None = None,
    config: dict | None = None,
) -> dict:
    """
    Портфельные агрегаты, флаги и удержание вердиктов.

    При любом портфельном флаге verdicts_held = True: отчёт отдаёт диагноз
    и маршруты, но не отдаёт вердикты аллокации.
    """
    cfg = config or DEFAULT_M3_CONFIG
    n = len(results)
    if not cfg["objects_min"] <= n <= cfg["objects_max"]:
        raise PortfolioSizeError(
            f"Направлений в портфеле: {n}. Допустимо от {cfg['objects_min']} "
            f"до {cfg['objects_max']}."
        )

    reduced = n < cfg["portfolio_min"]
    sum_positions = sum(r["symbols"].count(YANG) for r in results)
    turbulence = sum(r["moving_count"] for r in results)
    old_yin_total = sum(r["old_yin_count"] for r in results)
    old_yang_total = sum(r["old_yang_count"] for r in results)
    delta = old_yin_total - old_yang_total
    distinct_cells = len({r["cell_key"] for r in results})

    v_ranks = rank_desc([r["v_index"] for r in results])
    z_ranks = rank_desc([r["z_index"] for r in results])
    for r, vr, zr in zip(results, v_ranks, z_ranks):
        r["v_rank"], r["z_rank"] = vr, zr

    rho = spearman(v_ranks, owner_ranks) if (owner_ranks and not reduced) else None

    all_scores = [s for r in results for s in r["scores"].values()]
    si = cfg["self_inflation"]
    inflated_share = (
        sum(1 for s in all_scores if s >= si["line_score_min"]) / len(all_scores)
        if all_scores else 0.0
    )

    # Все три флага меряют разброс МЕЖДУ направлениями и ниже порога
    # сравнения либо срабатывают механически, либо не определены.
    # UNIFORM_PORTFOLIO: при одном направлении distinct_cells всегда 1.
    # RANK_MISMATCH: порядок из одного элемента не с чем сравнивать.
    # SELF_INFLATION: считается по линиям и формально определён, но его
    # различающая сила берётся из широты портфеля. «Все направления
    # высокие» подозрительно, «одно направление высокое» — просто сильное
    # направление. Порог калиброван на 18-48 баллах; при шести он держал бы
    # вердикт у сильных одиночек, а вердикт там главный вывод.
    flags: list[str] = []
    if not reduced:
        if distinct_cells == 1:
            flags.append("UNIFORM_PORTFOLIO")
        if inflated_share >= si["share_min"]:
            flags.append("SELF_INFLATION")
        if rho is not None and rho < cfg["rank_mismatch_spearman_max"]:
            flags.append("RANK_MISMATCH")

    # Критерии приёмки пилота (§11) — считаются всегда, вердиктов не меняют.
    spread_share = (
        sum(1 for s in all_scores if 2.50 <= s <= 3.00) / len(all_scores)
        if all_scores else 0.0
    )

    return {
        "objects": n,
        "reduced": reduced,
        "owner_ranks": list(owner_ranks) if owner_ranks else None,
        "sum_positions": sum_positions,
        "sum_positions_max": 6 * n,
        "turbulence": turbulence,
        "old_yin_total": old_yin_total,
        "old_yang_total": old_yang_total,
        "delta": delta,
        "distinct_cells": distinct_cells,
        "spearman": rho,
        "inflated_share": r2(inflated_share),
        "spread_share": r2(spread_share),
        "flags": flags,
        "verdicts_held": any(f in HOLDING_FLAGS for f in flags),
    }


# ── Точка входа ───────────────────────────────────────────────────────────────
def calculate(portfolio: dict, config: dict | None = None) -> dict:
    """
    portfolio: {
      'industry_id': int | None,
      'answers': {'Р1': 2, ..., 'Р6': 2},   # блок Р, уровень портфеля
      'objects': [obj, ...],                # 3..8 направлений
      'owner_ranks': [3, 1, 5, 4, 2] | None # порядок, названный собственником
    }
    """
    cfg = config or DEFAULT_M3_CONFIG
    portfolio_answers = portfolio.get("answers") or {}
    objects = portfolio.get("objects") or []

    results = [
        score_object(obj, portfolio_answers, portfolio.get("industry_id"), cfg)
        for obj in objects
    ]
    summary = score_portfolio(results, portfolio.get("owner_ranks"), cfg)
    return {"objects": results, "portfolio": summary}

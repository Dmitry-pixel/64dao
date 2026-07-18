# -*- coding: utf-8 -*-
"""
Скоринг финансовой функции — реализация Спецификации §3 «1:1».

Вход: словарь ответов {item_id: raw} где raw ∈ {1,2,3,4} или None («не знаю»).
Выход: структура finance_result (см. план §2.3), сериализуемая в JSONB.

Считает ТОЛЬКО сервер (план: не доверять фронту).
Слои интерпретации (D/E: правила напряжений, тексты) — отдельный модуль (Этап 3);
здесь считаются лишь детерминированные величины A/B: maturity_index и квадрант.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from app.finance_items import (
    FINANCE_ITEMS, ITEM_IDS, ITEMS_BY_BLOCK, BLOCKS, REVERSE_ITEMS,
)
from app.hexagrams import HEXAGRAM_LIST

# code(6×A/B) → (number, name)
_CODE_TO_HEX: dict[str, tuple[int, str]] = {c: (n, name) for n, name, c in HEXAGRAM_LIST}

VALID_RAW = {1, 2, 3, 4}


# ── Ошибки ────────────────────────────────────────────────────────────────────
class FinanceScoringError(ValueError):
    """Базовая ошибка скоринга."""


class InvalidAnswersError(FinanceScoringError):
    """Некорректный набор/значения ответов (не проходит валидацию §3.3)."""


class BlockUnderfilledError(FinanceScoringError):
    """≥2 пропусков в блоке — линия не определяется (Спецификация §3.6)."""

    def __init__(self, block: int):
        self.block = block
        super().__init__(f"Блок {block}: ≥2 пропусков — линия не определяется")


# ── Результат ─────────────────────────────────────────────────────────────────
@dataclass
class LineResult:
    line: int
    block: str            # семантический ключ линии (processes, systems, ...)
    score: float          # средний балл блока (2 знака)
    symbol: str           # 'A' | 'B'
    state: str            # young_yang | old_yang | young_yin | old_yin
    moving: bool
    flags: list[str] = field(default_factory=list)


def validate_answers(answers: dict[str, int | None]) -> None:
    """Проверка §3.3: ровно 24 известных item_id, значения ∈ {1,2,3,4,null}."""
    keys = set(answers.keys())
    expected = set(ITEM_IDS)
    if keys != expected:
        missing = expected - keys
        extra = keys - expected
        raise InvalidAnswersError(
            f"Неверный набор пунктов. Отсутствуют: {sorted(missing)}; лишние: {sorted(extra)}"
        )
    for item_id, raw in answers.items():
        if raw is None:
            continue
        if not isinstance(raw, int) or isinstance(raw, bool) or raw not in VALID_RAW:
            raise InvalidAnswersError(f"Пункт {item_id}: значение {raw!r} вне {{1,2,3,4,null}}")


def _effective(item_id: str, raw: int) -> int:
    """Инверсия реверсивных пунктов: балл' = 5 − балл (Спецификация §3.1)."""
    return 5 - raw if item_id in REVERSE_ITEMS else raw


def _classify(avg: float, symbol: str, moving: bool) -> str:
    if symbol == "A":
        return "old_yang" if moving else "young_yang"
    return "old_yin" if moving else "young_yin"


def compute_finance_result(answers: dict[str, int | None]) -> dict:
    """Полный скоринг. Возвращает dict (finance_result)."""
    validate_answers(answers)

    lines: list[LineResult] = []
    quality_flags: list[str] = []

    for block in sorted(BLOCKS):
        items = ITEMS_BY_BLOCK[block]
        eff_scores: list[int] = []
        skipped = 0
        for it in items:
            raw = answers[it["item_id"]]
            if raw is None:
                skipped += 1
                continue
            eff_scores.append(_effective(it["item_id"], raw))

        # §3.6 — пропуски
        if skipped >= 2:
            raise BlockUnderfilledError(block)

        flags: list[str] = []
        if skipped == 1:
            flags.append("PARTIAL_BLOCK")

        avg = round(sum(eff_scores) / len(eff_scores), 2)

        # §3.2 — символ и подвижность (границы включительно; 2.50 → Ян)
        symbol = "A" if avg >= 2.5 else "B"
        moving = avg >= 3.5 or avg <= 1.5

        # §3.3 — вето (линия 4, пункт 4.1 == 1, без инверсии — прямой пункт)
        if block == 4:
            veto_raw = answers.get("4.1")
            if veto_raw is None:
                flags.append("VETO_UNKNOWN")
            elif veto_raw == 1:
                symbol = "B"
                moving = avg <= 1.5   # подвижность по фактическому среднему (§3.3)
                flags.append("VETO_APPLIED")

        # §3.5 — флаги качества по блоку
        if (max(eff_scores) - min(eff_scores)) >= 2:
            flags.append("INCONSISTENT_BLOCK")
        if 2.40 <= avg <= 2.60:
            flags.append("BORDERLINE_LINE")

        lines.append(LineResult(
            line=block,
            block=BLOCKS[block]["key"],
            score=avg,
            symbol=symbol,
            state=_classify(avg, symbol, moving),
            moving=moving,
            flags=flags,
        ))

    # Мягкий лимит «не знаю» на всю анкету (план §8.2): ≥3 пропусков — флаг
    total_skipped = sum(1 for i in ITEM_IDS if answers[i] is None)
    if total_skipped >= 3:
        quality_flags.append("LOW_DATA_COMPLETENESS")

    # §3.5 — STRAIGHTLINING (все 24 сырых одинаковы либо ≥20 из 24)
    raw_values = [answers[i] for i in ITEM_IDS if answers[i] is not None]
    if raw_values:
        top = max(raw_values.count(v) for v in set(raw_values))
        if top >= 20:
            quality_flags.append("STRAIGHTLINING")

    # §3.4 — комбинации
    code_current = "".join(l.symbol for l in lines)
    moving_lines = [l.line for l in lines if l.moving]
    if moving_lines:
        code_resulting = "".join(
            ("B" if l.symbol == "A" else "A") if l.moving else l.symbol
            for l in lines
        )
    else:
        code_resulting = None

    hex_current = _lookup(code_current)
    hex_resulting = _lookup(code_resulting) if code_resulting else None

    # Слой A — индекс зрелости (число Ян-линий); Слой B — квадрант
    maturity_index = sum(1 for l in lines if l.symbol == "A")
    quadrant = _quadrant(lines)

    return {
        "lines": [asdict(l) for l in lines],
        "combination_current": code_current,
        "combination_resulting": code_resulting,
        "moving_lines": moving_lines,
        "maturity_index": maturity_index,
        "quadrant": quadrant,
        "quality_flags": quality_flags,
        "hexagram_current": hex_current,
        "hexagram_resulting": hex_resulting,
    }


def _lookup(code: str) -> dict:
    num, name = _CODE_TO_HEX[code]
    return {"code": code, "number": num, "name": name}


def _quadrant(lines: list[LineResult]) -> str:
    """Слой B (§5.3): нижняя триграмма = линии 1–3, верхняя = 4–6; сильная при ≥2 Ян."""
    lower_strong = sum(1 for l in lines[0:3] if l.symbol == "A") >= 2
    upper_strong = sum(1 for l in lines[3:6] if l.symbol == "A") >= 2
    if lower_strong and upper_strong:
        return "scale"
    if lower_strong and not upper_strong:
        return "power_no_direction"
    if not lower_strong and upper_strong:
        return "ambition_no_engine"
    return "turnaround"

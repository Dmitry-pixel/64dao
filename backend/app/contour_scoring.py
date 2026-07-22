# -*- coding: utf-8 -*-
"""
Обобщённый скоринг контура диагностики (Спецификация §3).

Логика идентична финансовому блоку и от предметной области не зависит:
контур описывается ContourSpec — набор пунктов, реверсивные позиции, вето,
лимит пропусков. Считает ТОЛЬКО сервер (фронту не доверяем).

finance_scoring.py остаётся тонкой обёрткой над этим модулем.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

from app.hexagrams import HEXAGRAM_LIST

_CODE_TO_HEX: dict[str, tuple[int, str]] = {c: (n, name) for n, name, c in HEXAGRAM_LIST}
VALID_RAW = {1, 2, 3, 4}


@dataclass(frozen=True)
class ContourSpec:
    """Конфигурация анкеты контура: 6 блоков x 4 пункта, блок N -> линия N."""
    key: str
    title: str
    blocks: dict[int, dict[str, str]]
    items: list[dict]
    reverse_items: frozenset[str]
    veto_items: frozenset[str] = frozenset({"4.1"})
    veto_block: int = 4
    max_unknowns: int = 3

    @property
    def item_ids(self) -> tuple[str, ...]:
        return tuple(i["item_id"] for i in self.items)

    @property
    def items_by_block(self) -> dict[int, list[dict]]:
        return {b: [i for i in self.items if i["block"] == b] for b in self.blocks}


class ContourScoringError(ValueError):
    """Базовая ошибка скоринга."""


class InvalidAnswersError(ContourScoringError):
    """Некорректный набор или значения ответов (Спецификация §3.3)."""


class BlockUnderfilledError(ContourScoringError):
    """Два и более пропусков в блоке — линия не определяется (§3.6)."""

    def __init__(self, block: int):
        self.block = block
        super().__init__(f"Блок {block}: >=2 пропусков — линия не определяется")


class TooManyUnknownsError(InvalidAnswersError):
    """Превышен лимит ответов «Не знаю» на анкету (план финблока §8.2)."""

    def __init__(self, count: int, limit: int):
        self.count = count
        self.limit = limit
        super().__init__(
            f"Ответов «Не знаю»: {count}. Допустимо не более {limit} на анкету."
        )


@dataclass
class LineResult:
    line: int
    block: str
    score: float
    symbol: str
    state: str
    moving: bool
    flags: list[str] = field(default_factory=list)


def validate_answers(answers: dict[str, int | None], spec: ContourSpec) -> None:
    """Проверка §3.3: ровно набор известных item_id, значения из {1,2,3,4,null}."""
    keys = set(answers.keys())
    expected = set(spec.item_ids)
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
            raise InvalidAnswersError(
                f"Пункт {item_id}: значение {raw!r} вне {{1,2,3,4,null}}"
            )


def _effective(item_id: str, raw: int, spec: ContourSpec) -> int:
    """Инверсия реверсивных пунктов: балл' = 5 - балл (§3.1)."""
    return 5 - raw if item_id in spec.reverse_items else raw


def _classify(avg: float, symbol: str, moving: bool) -> str:
    if symbol == "A":
        return "old_yang" if moving else "young_yang"
    return "old_yin" if moving else "young_yin"


def _lookup(code: str) -> dict:
    num, name = _CODE_TO_HEX[code]
    return {"code": code, "number": num, "name": name}


def _quadrant(lines: list[LineResult]) -> str:
    """Слой B (§5.3): нижняя триграмма — линии 1-3, верхняя — 4-6; сильная при >=2 Ян."""
    lower_strong = sum(1 for l in lines[0:3] if l.symbol == "A") >= 2
    upper_strong = sum(1 for l in lines[3:6] if l.symbol == "A") >= 2
    if lower_strong and upper_strong:
        return "scale"
    if lower_strong and not upper_strong:
        return "power_no_direction"
    if not lower_strong and upper_strong:
        return "ambition_no_engine"
    return "turnaround"


def compute_contour_result(answers: dict[str, int | None], spec: ContourSpec) -> dict:
    """Полный скоринг контура. Возвращает снимок result, сериализуемый в JSONB."""
    validate_answers(answers, spec)

    unknown_total = sum(1 for v in answers.values() if v is None)
    if unknown_total > spec.max_unknowns:
        raise TooManyUnknownsError(unknown_total, spec.max_unknowns)

    items_by_block = spec.items_by_block
    lines: list[LineResult] = []
    quality_flags: list[str] = []

    for block in sorted(spec.blocks):
        eff_scores: list[int] = []
        skipped = 0
        for it in items_by_block[block]:
            raw = answers[it["item_id"]]
            if raw is None:
                skipped += 1
                continue
            eff_scores.append(_effective(it["item_id"], raw, spec))

        # §3.6 — пропуски
        if skipped >= 2:
            raise BlockUnderfilledError(block)

        flags: list[str] = []
        if skipped == 1:
            flags.append("PARTIAL_BLOCK")

        # §3.2 — символ и подвижность (границы включительно; 2.50 -> Ян)
        avg = round(sum(eff_scores) / len(eff_scores), 2)
        symbol = "A" if avg >= 2.5 else "B"
        moving = avg >= 3.5 or avg <= 1.5

        # §3.3 — вето (прямой пункт, без инверсии)
        if block == spec.veto_block and spec.veto_items:
            veto_id = sorted(spec.veto_items)[0]
            veto_raw = answers.get(veto_id)
            if veto_raw is None:
                flags.append("VETO_UNKNOWN")
            elif veto_raw == 1:
                symbol = "B"
                moving = avg <= 1.5
                flags.append("VETO_APPLIED")

        # §3.5 — флаги качества по блоку
        if (max(eff_scores) - min(eff_scores)) >= 2:
            flags.append("INCONSISTENT_BLOCK")
        if 2.40 <= avg <= 2.60:
            flags.append("BORDERLINE_LINE")

        lines.append(LineResult(
            line=block,
            block=spec.blocks[block]["key"],
            score=avg,
            symbol=symbol,
            state=_classify(avg, symbol, moving),
            moving=moving,
            flags=flags,
        ))

    item_ids = spec.item_ids

    # Мягкий лимит «не знаю» на анкету (план финблока §8.2)
    if sum(1 for i in item_ids if answers[i] is None) >= 3:
        quality_flags.append("LOW_DATA_COMPLETENESS")

    # §3.5 — STRAIGHTLINING (>=20 из 24 сырых ответов одинаковы)
    raw_values = [answers[i] for i in item_ids if answers[i] is not None]
    if raw_values:
        top = max(raw_values.count(v) for v in set(raw_values))
        if top >= 20:
            quality_flags.append("STRAIGHTLINING")

    # §3.4 — комбинации
    code_current = "".join(l.symbol for l in lines)
    moving_lines = [l.line for l in lines if l.moving]
    code_resulting = "".join(
        ("B" if l.symbol == "A" else "A") if l.moving else l.symbol for l in lines
    ) if moving_lines else None

    return {
        "lines": [asdict(l) for l in lines],
        "combination_current": code_current,
        "combination_resulting": code_resulting,
        "moving_lines": moving_lines,
        "maturity_index": sum(1 for l in lines if l.symbol == "A"),
        "quadrant": _quadrant(lines),
        "quality_flags": quality_flags,
        "hexagram_current": _lookup(code_current),
        "hexagram_resulting": _lookup(code_resulting) if code_resulting else None,
    }

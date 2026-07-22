# -*- coding: utf-8 -*-
"""
Скоринг финансовой функции — тонкая обёртка над обобщённым contour_scoring.

Логика переехала в app/contour_scoring.py (этап 2 плана контуров): она не
зависела от предметной области, поэтому дублировать её на четыре контура
незачем. Модуль сохранён ради существующих импортов; поведение не изменилось,
контрольный кейс Спецификации §3.7 проходит байт-в-байт.
"""
from __future__ import annotations

from app.finance_items import FINANCE_SPEC
from app.contour_scoring import (  # noqa: F401  — реэкспорт для совместимости
    ContourScoringError as FinanceScoringError,
    InvalidAnswersError,
    BlockUnderfilledError,
    TooManyUnknownsError,
    LineResult,
    VALID_RAW,
    compute_contour_result,
    validate_answers as _validate_answers,
    _effective as _effective_spec,
    _classify,
    _lookup,
    _quadrant,
)

MAX_UNKNOWNS_TOTAL = FINANCE_SPEC.max_unknowns


def validate_answers(answers: dict[str, int | None]) -> None:
    """Проверка набора ответов финблока (§3.3)."""
    _validate_answers(answers, FINANCE_SPEC)


def _effective(item_id: str, raw: int) -> int:
    """Инверсия реверсивных пунктов финблока (§3.1)."""
    return _effective_spec(item_id, raw, FINANCE_SPEC)


def compute_finance_result(answers: dict[str, int | None]) -> dict:
    """Полный скоринг финблока — тождественен compute_contour_result с FINANCE_SPEC."""
    return compute_contour_result(answers, FINANCE_SPEC)

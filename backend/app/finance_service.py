# -*- coding: utf-8 -*-
"""
Сервис-слой финансового блока: разрешение скоринга при сабмите диагностики.

Чистая логика (без БД и FastAPI) — тестируется отдельно. Роутер маппит
исключения на HTTP 400.
"""
from __future__ import annotations

from app.finance_items import ITEM_IDS
from app.finance_scoring import (
    compute_finance_result, InvalidAnswersError, BlockUnderfilledError,
)


class FinanceRequiredError(ValueError):
    """Финблок обязателен (флаг включён), но finance_answers не переданы."""


def resolve_submission_finance(
    finance_answers: dict | None,
    *,
    status: str,
    is_method1: bool,
    finance_required: bool,
) -> tuple[dict | None, str | None]:
    """
    Возвращает (finance_result, finance_combination).

    Правила (план §3.3 + флаг finance_block_required):
    - Нет ответов:
        * если флаг включён и это completed-диагностика Метода 1 -> FinanceRequiredError;
        * иначе (draft, Метод 2, флаг выключен) -> (None, None), legacy-совместимо.
    - Есть ответы:
        * completed -> обязателен полный валидный набор; ошибки скоринга
          (InvalidAnswersError / BlockUnderfilledError) пробрасываются -> 400;
        * draft -> считаем только если набор полный и валидный, иначе просто
          сохраняем сырые ответы без результата (частичное сохранение).
    Скоринг всегда на сервере — фронту не доверяем.
    """
    if finance_answers is None:
        if finance_required and status == "completed" and is_method1:
            raise FinanceRequiredError(
                "Финансовый блок обязателен для завершения диагностики Метода 1."
            )
        return None, None

    if status == "completed":
        result = compute_finance_result(finance_answers)   # может бросить -> 400
        return result, result["combination_current"]

    # draft: считаем best-effort только при полном наборе
    if set(finance_answers.keys()) == set(ITEM_IDS):
        try:
            result = compute_finance_result(finance_answers)
            return result, result["combination_current"]
        except (InvalidAnswersError, BlockUnderfilledError):
            return None, None
    return None, None

# -*- coding: utf-8 -*-
"""
Тесты сервис-слоя финблока (Этап 4): resolve_submission_finance. БД не нужна.
"""
import pytest

from app.finance_items import ITEM_IDS
from app.finance_scoring import BlockUnderfilledError, InvalidAnswersError
from app.finance_service import FinanceRequiredError, resolve_submission_finance


def full_answers(value=3) -> dict:
    return {i: value for i in ITEM_IDS}


def control_answers() -> dict:
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    return a


def test_no_finance_flag_off_completed_method1_ok():
    res, comb = resolve_submission_finance(None, status="completed", is_method1=True, finance_required=False)
    assert res is None and comb is None


def test_no_finance_flag_on_completed_method1_raises():
    with pytest.raises(FinanceRequiredError):
        resolve_submission_finance(None, status="completed", is_method1=True, finance_required=True)


def test_no_finance_flag_on_completed_method2_ok():
    res, comb = resolve_submission_finance(None, status="completed", is_method1=False, finance_required=True)
    assert res is None and comb is None


def test_no_finance_flag_on_draft_method1_ok():
    res, comb = resolve_submission_finance(None, status="draft", is_method1=True, finance_required=True)
    assert res is None and comb is None


def test_completed_with_valid_finance_scores():
    res, comb = resolve_submission_finance(control_answers(), status="completed", is_method1=True, finance_required=True)
    assert comb == "AAAABB"
    assert res["hexagram_current"]["number"] == 34


def test_completed_with_missing_item_raises():
    a = control_answers(); del a["3.3"]
    with pytest.raises(InvalidAnswersError):
        resolve_submission_finance(a, status="completed", is_method1=True, finance_required=True)


def test_completed_with_underfilled_block_raises():
    a = full_answers(3); a["1.1"] = None; a["1.2"] = None
    with pytest.raises(BlockUnderfilledError):
        resolve_submission_finance(a, status="completed", is_method1=True, finance_required=True)


def test_draft_partial_stores_without_result():
    partial = {"1.1": 3, "1.2": 4}
    res, comb = resolve_submission_finance(partial, status="draft", is_method1=True, finance_required=True)
    assert res is None and comb is None


def test_draft_complete_valid_scores():
    res, comb = resolve_submission_finance(control_answers(), status="draft", is_method1=True, finance_required=False)
    assert comb == "AAAABB"

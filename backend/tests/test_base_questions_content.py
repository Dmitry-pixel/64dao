# -*- coding: utf-8 -*-
"""
Резолвер редактируемых базовых вопросов: дефолты кода + правки из админки.

БД не нужна: merge_rows работает со списком словарей той же формы, что и
строки fin_content.
"""
import pytest

from app.base_questions import (
    EDITABLE_FIELDS,
    KEYS,
    STRUCTURAL_FIELDS,
    default_payload,
    lc_values,
    lifecycle_description,
    merge_rows,
)
from app.method1_questions import BASE_QUESTIONS


def _row(key, payload, is_active=True):
    return {"key": key, "payload": payload, "is_active": is_active}


def test_empty_db_gives_code_defaults():
    assert merge_rows([]) == [dict(q) for q in BASE_QUESTIONS]


def test_keys_cover_six_questions():
    assert KEYS == ("q1", "q2", "q3", "q4", "q5", "q6")
    assert len(BASE_QUESTIONS) == len(KEYS)


def test_edit_overrides_only_given_field():
    out = merge_rows([_row("q2", {"a_full": "ПРАВКА"})])
    assert out[1]["a_full"] == "ПРАВКА"
    assert out[1]["b_full"] == BASE_QUESTIONS[1]["b_full"]
    assert out[1]["q"] == BASE_QUESTIONS[1]["q"]
    assert out[0] == dict(BASE_QUESTIONS[0])


def test_inactive_row_is_ignored():
    out = merge_rows([_row("q2", {"a_full": "ПРАВКА"}, is_active=False)])
    assert out[1]["a_full"] == BASE_QUESTIONS[1]["a_full"]


def test_blank_and_bad_values_do_not_erase_defaults():
    out = merge_rows([_row("q3", {"q": "   ", "help": None, "a": 42})])
    assert out[2]["q"] == BASE_QUESTIONS[2]["q"]
    assert out[2]["help"] == BASE_QUESTIONS[2]["help"]
    assert out[2]["a"] == BASE_QUESTIONS[2]["a"]


def test_unknown_key_is_ignored():
    assert merge_rows([_row("q9", {"q": "мусор"})]) == [dict(q) for q in BASE_QUESTIONS]


def test_structural_fields_come_from_code():
    """lc_key и label задают привязку к отчёту — правке из админки не подлежат."""
    out = merge_rows([_row("q1", {f: "подмена" for f in STRUCTURAL_FIELDS})])
    for f in STRUCTURAL_FIELDS:
        assert out[0][f] == BASE_QUESTIONS[0][f]


def test_editable_fields_are_the_texts():
    assert set(EDITABLE_FIELDS) == {"q", "help", "a", "b", "a_full", "b_full"}


@pytest.mark.parametrize("combo,idx,letter", [("AAAAAA", 1, "A"), ("BBBBBB", 1, "B")])
def test_lc_values_follow_combination(combo, idx, letter):
    vals = lc_values(combo)
    expected = BASE_QUESTIONS[idx]["a_full" if letter == "A" else "b_full"]
    assert vals["lc_strategy"] == expected


def test_lc_values_use_edited_texts():
    qs = merge_rows([_row("q2", {"a_full": "НОВЫЙ ТЕКСТ"})])
    assert lc_values("AAAAAA", qs)["lc_strategy"] == "НОВЫЙ ТЕКСТ"
    assert lc_values("BBBBBB", qs)["lc_strategy"] == BASE_QUESTIONS[1]["b_full"]


def test_lc_values_reject_short_or_dirty_combination():
    assert lc_values("") == {}
    assert lc_values(None) == {}
    assert lc_values("AA") == {}
    assert "lc_profit" not in lc_values("XAAAAA")


def test_lifecycle_description_numbers_all_six():
    text = lifecycle_description("AAAAAA")
    lines = text.split("\n")
    assert len(lines) == 6
    assert lines[0].startswith("1. Формирование прибыли – ")
    assert lines[5].startswith("6. Тип ценности – ")


def test_default_payload_is_a_copy():
    p = default_payload(0)
    p["q"] = "испорчено"
    assert BASE_QUESTIONS[0]["q"] != "испорчено"


# ── Защита от переворота смысла ──────────────────────────────────────────────

from app.base_questions import BaseQuestionEditError, normalize, validate_edit  # noqa: E402

Q2 = BASE_QUESTIONS[1]


def test_reword_is_allowed():
    """Формулировку менять можно — смысл стороны сохраняется."""
    validate_edit("q2", "common", {
        "a": "Быстрый последователь: берём проверенное и улучшаем",
        "b": "Первопроходец: делаем то, чего на рынке ещё нет",
    })


def test_swap_of_both_answers_is_rejected():
    with pytest.raises(BaseQuestionEditError, match="местами"):
        validate_edit("q2", "common", {"a": Q2["b"], "b": Q2["a"]})


def test_putting_other_side_text_into_a_is_rejected():
    with pytest.raises(BaseQuestionEditError, match="местами"):
        validate_edit("q2", "common", {"a": Q2["b"]})


def test_putting_other_side_text_into_b_is_rejected():
    with pytest.raises(BaseQuestionEditError, match="местами"):
        validate_edit("q2", "common", {"b": Q2["a"]})


def test_swap_detected_despite_case_and_punctuation():
    disguised = Q2["b"].upper().replace("—", "-") + "."
    with pytest.raises(BaseQuestionEditError, match="местами"):
        validate_edit("q2", "common", {"a": disguised})


def test_full_form_swap_is_rejected():
    with pytest.raises(BaseQuestionEditError, match="местами"):
        validate_edit("q2", "common", {"a_full": Q2["b_full"]})


def test_swap_checked_against_current_value_not_only_default():
    """Если текст уже правили, переворот ловится относительно нового значения."""
    current = dict(Q2, a="Догоняющий: копируем удачное", b="Пионер: создаём категорию")
    validate_edit("q2", "common", {"a": "Догоняющий: быстро копируем удачное"}, current)
    with pytest.raises(BaseQuestionEditError, match="местами"):
        validate_edit("q2", "common", {"a": "Пионер: создаём категорию"}, current)


def test_structural_fields_cannot_be_changed():
    with pytest.raises(BaseQuestionEditError, match="структуру"):
        validate_edit("q1", "common", {"lc_key": "lc_other"})
    with pytest.raises(BaseQuestionEditError, match="структуру"):
        validate_edit("q1", "common", {"label": "Другая подпись"})


def test_structural_fields_may_be_resent_unchanged():
    validate_edit("q1", "common", {"lc_key": BASE_QUESTIONS[0]["lc_key"],
                                   "label": BASE_QUESTIONS[0]["label"]})


def test_empty_text_is_rejected():
    with pytest.raises(BaseQuestionEditError, match="пустым"):
        validate_edit("q1", "common", {"q": "   "})


def test_unknown_key_and_contour_are_rejected():
    with pytest.raises(BaseQuestionEditError, match="Ключ"):
        validate_edit("q9", "common", {"q": "текст"})
    with pytest.raises(BaseQuestionEditError, match="контурам"):
        validate_edit("q1", "finance", {"q": "текст"})


def test_normalize_ignores_case_spaces_punctuation():
    assert normalize("  Первопроходец — СОЗДАНИЕ  новых!  ") == normalize("первопроходец создание новых")

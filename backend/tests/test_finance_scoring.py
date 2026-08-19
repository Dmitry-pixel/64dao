# -*- coding: utf-8 -*-
"""
Юнит-тесты скоринга финансовой функции (Этап 2).
Чистая логика — БД не нужна. Покрывают Спецификацию §3 и план §5 (пп. 1–5, 7).
"""
import pytest

from app.finance_items import ITEM_IDS, REVERSE_ITEMS, VETO_ITEMS
from app.finance_scoring import (
    BlockUnderfilledError,
    InvalidAnswersError,
    _effective,
    compute_finance_result,
    validate_answers,
)
from app.hexagrams import HEXAGRAM_LIST


# ── Хелперы ───────────────────────────────────────────────────────────────────
def base_answers(value: int | None = 3) -> dict[str, int | None]:
    """Все 24 пункта = value."""
    return {i: value for i in ITEM_IDS}


def set_block(answers: dict, block: int, raws: list[int | None]) -> dict:
    assert len(raws) == 4
    for pos, raw in enumerate(raws, start=1):
        answers[f"{block}.{pos}"] = raw
    return answers


def line(result: dict, n: int) -> dict:
    return next(l for l in result["lines"] if l["line"] == n)


# ── 1. Контрольный кейс Спецификации §3.7 (сквозной) ──────────────────────────
def test_control_case_3_7():
    a = {}
    set_block(a, 1, [3, 4, 2, 3])   # eff 3,4,3,3 -> 3.25
    set_block(a, 2, [3, 3, 1, 3])   # eff 3,3,4,3 -> 3.25
    set_block(a, 3, [3, 2, 1, 3])   # eff 3,2,4,3 -> 3.00 (разброс 2 -> INCONSISTENT)
    set_block(a, 4, [4, 3, 3, 2])   # eff 4,3,3,3 -> 3.25
    set_block(a, 5, [2, 2, 4, 2])   # eff 2,2,1,2 -> 1.75
    set_block(a, 6, [1, 1, 4, 1])   # eff 1,1,1,1 -> 1.00 (старый Инь, подвижная)

    r = compute_finance_result(a)

    assert [line(r, n)["score"] for n in range(1, 7)] == [3.25, 3.25, 3.00, 3.25, 1.75, 1.00]
    assert r["combination_current"] == "AAAABB"
    assert r["hexagram_current"] == {"code": "AAAABB", "number": 34, "name": "Сила"}
    assert r["moving_lines"] == [6]
    assert r["combination_resulting"] == "AAAABA"
    assert r["hexagram_resulting"] == {"code": "AAAABA", "number": 14, "name": "Процветание"}
    assert "INCONSISTENT_BLOCK" in line(r, 3)["flags"]
    assert line(r, 6)["state"] == "old_yin"
    assert line(r, 6)["moving"] is True
    # Слой A/B
    assert r["maturity_index"] == 4
    assert r["quadrant"] == "power_no_direction"


# ── 2. Границы порогов (§3.2): 2.50 -> Ян; 3.50 -> старый Ян; 1.50 -> старый Инь
def test_boundary_2_50_is_yang_stable():
    a = base_answers(3)
    set_block(a, 1, [2, 3, 3, 3])   # eff 2,3,2,3 -> 2.50
    r = compute_finance_result(a)
    l = line(r, 1)
    assert l["score"] == 2.50 and l["symbol"] == "A" and l["moving"] is False
    assert l["state"] == "young_yang"


def test_boundary_3_50_is_old_yang_moving():
    a = base_answers(3)
    set_block(a, 1, [4, 4, 2, 3])   # eff 4,4,3,3 -> 3.50
    r = compute_finance_result(a)
    l = line(r, 1)
    assert l["score"] == 3.50 and l["symbol"] == "A" and l["moving"] is True
    assert l["state"] == "old_yang"


def test_boundary_1_50_is_old_yin_moving():
    a = base_answers(3)
    set_block(a, 1, [2, 1, 3, 1])   # eff 2,1,2,1 -> 1.50
    r = compute_finance_result(a)
    l = line(r, 1)
    assert l["score"] == 1.50 and l["symbol"] == "B" and l["moving"] is True
    assert l["state"] == "old_yin"


# ── 3. Вето (§3.3): 4.1==1 при среднем >=2.5 -> линия 4 = B + VETO_APPLIED ─────
def test_veto_forces_yin():
    a = base_answers(3)
    set_block(a, 4, [1, 4, 4, 1])   # eff 1,4,4,4 -> 3.25, но 4.1==1
    r = compute_finance_result(a)
    l = line(r, 4)
    assert l["symbol"] == "B"
    assert "VETO_APPLIED" in l["flags"]
    assert l["moving"] is False           # avg 3.25 > 1.5 -> молодой Инь
    assert l["state"] == "young_yin"


def test_veto_unknown_when_4_1_skipped():
    a = base_answers(3)
    set_block(a, 4, [None, 4, 4, 2])   # 4.1 пропущен -> вето не применяется
    r = compute_finance_result(a)
    l = line(r, 4)
    assert "VETO_UNKNOWN" in l["flags"]
    assert "PARTIAL_BLOCK" in l["flags"]
    assert l["symbol"] == "A"           # среднее по 3 (eff 4,4,3) = 3.67 -> Ян


# ── 4. Пропуски (§3.6) ────────────────────────────────────────────────────────
def test_partial_block_one_skip():
    a = base_answers(3)
    set_block(a, 2, [4, 4, 1, None])   # eff 4,4,4 (2.3 реверс: 5-1=4); 2.4 пропущен
    r = compute_finance_result(a)
    l = line(r, 2)
    assert "PARTIAL_BLOCK" in l["flags"]
    assert l["score"] == round(12 / 3, 2)   # 4.00


def test_underfilled_block_two_skips_raises():
    a = base_answers(3)
    set_block(a, 1, [None, None, 3, 3])
    with pytest.raises(BlockUnderfilledError) as ei:
        compute_finance_result(a)
    assert ei.value.block == 1


# ── 5. Реверсивность применяется ровно к 6 пунктам ────────────────────────────
def test_reverse_set_exact():
    assert {"1.3", "2.3", "3.3", "4.4", "5.3", "6.3"} == REVERSE_ITEMS
    assert {"4.1"} == VETO_ITEMS


def test_effective_inversion():
    for iid in REVERSE_ITEMS:
        assert _effective(iid, 4) == 1 and _effective(iid, 1) == 4
    for iid in ("1.1", "2.1", "4.1", "6.4"):
        assert _effective(iid, 4) == 4 and _effective(iid, 1) == 1


# ── 7. Сверка HEXAGRAM_LIST с классической генерацией из триграмм (Вэнь-ван) ───
def test_hexagram_list_matches_classical_king_wen():
    T = {"Qian": "AAA", "Dui": "AAB", "Li": "ABA", "Zhen": "ABB",
         "Xun": "BAA", "Kan": "BAB", "Gen": "BBA", "Kun": "BBB"}
    kw = {
        1: ("Qian", "Qian"), 2: ("Kun", "Kun"), 3: ("Zhen", "Kan"), 4: ("Kan", "Gen"),
        5: ("Qian", "Kan"), 6: ("Kan", "Qian"), 7: ("Kan", "Kun"), 8: ("Kun", "Kan"),
        9: ("Qian", "Xun"), 10: ("Dui", "Qian"), 11: ("Qian", "Kun"), 12: ("Kun", "Qian"),
        13: ("Li", "Qian"), 14: ("Qian", "Li"), 15: ("Gen", "Kun"), 16: ("Kun", "Zhen"),
        17: ("Zhen", "Dui"), 18: ("Xun", "Gen"), 19: ("Dui", "Kun"), 20: ("Kun", "Xun"),
        21: ("Zhen", "Li"), 22: ("Li", "Gen"), 23: ("Kun", "Gen"), 24: ("Zhen", "Kun"),
        25: ("Zhen", "Qian"), 26: ("Qian", "Gen"), 27: ("Zhen", "Gen"), 28: ("Xun", "Dui"),
        29: ("Kan", "Kan"), 30: ("Li", "Li"), 31: ("Gen", "Dui"), 32: ("Xun", "Zhen"),
        33: ("Gen", "Qian"), 34: ("Qian", "Zhen"), 35: ("Kun", "Li"), 36: ("Li", "Kun"),
        37: ("Li", "Xun"), 38: ("Dui", "Li"), 39: ("Gen", "Kan"), 40: ("Kan", "Zhen"),
        41: ("Dui", "Gen"), 42: ("Zhen", "Xun"), 43: ("Qian", "Dui"), 44: ("Xun", "Qian"),
        45: ("Kun", "Dui"), 46: ("Xun", "Kun"), 47: ("Kan", "Dui"), 48: ("Xun", "Kan"),
        49: ("Li", "Dui"), 50: ("Xun", "Li"), 51: ("Zhen", "Zhen"), 52: ("Gen", "Gen"),
        53: ("Gen", "Xun"), 54: ("Dui", "Zhen"), 55: ("Li", "Zhen"), 56: ("Gen", "Li"),
        57: ("Xun", "Xun"), 58: ("Dui", "Dui"), 59: ("Kan", "Xun"), 60: ("Dui", "Kan"),
        61: ("Dui", "Xun"), 62: ("Gen", "Zhen"), 63: ("Li", "Kan"), 64: ("Kan", "Li"),
    }
    classical = {n: T[lo] + T[up] for n, (lo, up) in kw.items()}  # lower(1-3)+upper(4-6)
    hexpy = {n: c for n, _, c in HEXAGRAM_LIST}
    assert hexpy == classical
    assert len({c for _, _, c in HEXAGRAM_LIST}) == 64


# ── Доп.: нет подвижных -> результирующая None ────────────────────────────────
def test_no_moving_lines_resulting_none():
    a = base_answers(3)   # каждый блок: eff среднее 2.75 (реверс даёт 3,3,2,3) -> A, не подвижная
    r = compute_finance_result(a)
    assert r["moving_lines"] == []
    assert r["combination_resulting"] is None
    assert r["hexagram_resulting"] is None


# ── Доп.: STRAIGHTLINING ──────────────────────────────────────────────────────
def test_straightlining_all_same():
    r = compute_finance_result(base_answers(3))
    assert "STRAIGHTLINING" in r["quality_flags"]


# ── Доп.: валидация входа (§3.3) ──────────────────────────────────────────────
def test_invalid_missing_item():
    a = base_answers(3)
    del a["3.3"]
    with pytest.raises(InvalidAnswersError):
        compute_finance_result(a)


def test_invalid_value_out_of_range():
    a = base_answers(3)
    a["1.1"] = 5
    with pytest.raises(InvalidAnswersError):
        compute_finance_result(a)


# ── Мягкий лимит «не знаю» на анкету (план §8.2): ≥3 пропусков → флаг ─────────
def test_low_data_completeness_flag():
    a = base_answers(3)
    a["1.1"] = None; a["2.1"] = None; a["3.1"] = None   # по одному в трёх блоках
    r = compute_finance_result(a)
    assert "LOW_DATA_COMPLETENESS" in r["quality_flags"]


def test_no_low_data_flag_with_two_skips():
    a = base_answers(3)
    a["1.1"] = None; a["2.1"] = None
    r = compute_finance_result(a)
    assert "LOW_DATA_COMPLETENESS" not in r["quality_flags"]

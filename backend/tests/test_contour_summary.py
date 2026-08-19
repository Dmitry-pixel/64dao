# -*- coding: utf-8 -*-
"""
Сводная карта контуров: выбор ограничения, тай-брейки, разрыв зрелости.
Чистая логика, БД не нужна.
"""
from app.contour_summary import GAP_THRESHOLD, build_summary


def res(index: int, moving: int = 0, combo: str = "AAAAAA") -> dict:
    return {
        "combination_current": combo,
        "hexagram_current": {"code": combo, "number": 1, "name": "Творчество"},
        "hexagram_resulting": None,
        "maturity_index": index,
        "moving_lines": list(range(1, moving + 1)),
    }


def test_none_when_single_contour():
    assert build_summary({"finance": res(4)}) is None


def test_none_when_empty():
    assert build_summary({}) is None


def test_unknown_contours_ignored():
    assert build_summary({"finance": res(4), "нечто": res(1)}) is None


def test_constraint_is_lowest_maturity():
    s = build_summary({"finance": res(5), "product": res(2), "market": res(4)})
    assert s["constraint"] == "product"
    assert s["count"] == 3
    assert next(r for r in s["rows"] if r["contour"] == "product")["is_constraint"] is True


def test_rows_follow_report_order():
    s = build_summary({"market": res(5), "finance": res(2), "process": res(4)})
    assert [r["contour"] for r in s["rows"]] == ["finance", "process", "market"]


def test_tie_broken_by_moving_lines():
    """При равном индексе раньше идёт контур с бо́льшим числом подвижных линий:
    там изменение уже назрело."""
    s = build_summary({"finance": res(3, moving=1), "product": res(3, moving=4)})
    assert s["constraint"] == "product"


def test_full_tie_leaves_no_constraint():
    """Совпали и зрелость, и число подвижных линий — выбор между ними был бы
    произволен, поэтому ограничение не назначается (Поправка П5)."""
    s = build_summary({"finance": res(3, moving=2), "product": res(3, moving=2)})
    assert s["constraint"] is None
    assert sorted(s["tied"]) == ["finance", "product"]
    assert s["gap"] is None


def test_gap_significant_when_threshold_reached():
    s = build_summary({"finance": res(1), "product": res(1 + GAP_THRESHOLD), "market": res(6)})
    assert s["constraint"] == "finance"
    assert s["gap"] == GAP_THRESHOLD
    assert s["gap_significant"] is True


def test_gap_not_significant_when_close():
    s = build_summary({"finance": res(2), "product": res(3)})
    assert s["gap"] == 1
    assert s["gap_significant"] is False


def test_gap_measured_to_nearest_neighbour():
    """Разрыв считается до ближайшего по зрелости, а не до максимума."""
    s = build_summary({"finance": res(1), "product": res(2), "market": res(6)})
    assert s["gap"] == 1
    assert s["gap_significant"] is False


def test_stable_contours_listed():
    s = build_summary({"finance": res(4, moving=0), "product": res(2, moving=3)})
    assert s["stable"] == ["finance"]


def test_all_four_contours():
    s = build_summary({
        "finance": res(4, moving=1),
        "product": res(3, moving=2),
        "process": res(1, moving=4),
        "market": res(4, moving=0),
    })
    assert s["count"] == 4
    assert s["constraint"] == "process"
    assert s["gap"] == 2
    assert s["stable"] == ["market"]
    assert [r["contour"] for r in s["rows"]] == ["finance", "product", "process", "market"]

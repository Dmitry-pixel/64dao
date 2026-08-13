# -*- coding: utf-8 -*-
"""
Матрица «контуры x уровни» в сводной карте: пороги системности, порядок
колонок, поведение на legacy-снимке.

Асимметрия порогов проверяется отдельно: слабость системна с трёх контуров,
опора — только при полном совпадении. Иначе вывод дублирует контур-ограничение.
"""
from app.contour_summary import LEVEL_SYSTEMIC_MIN, build_summary
from app.contours import CONTOUR_ORDER, LINE_KEYS


def _res(combo: str) -> dict:
    lines = [{"line": i, "block": LINE_KEYS[i - 1], "score": 2.5,
              "symbol": combo[i - 1],
              "state": "young_yang" if combo[i - 1] == "A" else "young_yin",
              "moving": False, "flags": []} for i in range(1, 7)]
    return {"lines": lines, "combination_current": combo,
            "combination_resulting": None, "moving_lines": [],
            "maturity_index": combo.count("A"),
            "hexagram_current": {"code": combo, "number": 1, "name": "X"},
            "hexagram_resulting": None}


def _by_level(summary: dict) -> dict:
    return {r["level"]: r for r in summary["levels"]}


def test_matrix_shape_and_column_order():
    s = build_summary({k: _res("AAAAAA") for k in CONTOUR_ORDER})
    assert [r["level"] for r in s["levels"]] == ["earth", "human", "heaven"]
    for row in s["levels"]:
        assert [c["contour"] for c in row["cells"]] == list(CONTOUR_ORDER)


def test_only_passed_contours_get_columns():
    s = build_summary({"finance": _res("AAAAAA"), "market": _res("AAAAAA")})
    for row in s["levels"]:
        assert [c["contour"] for c in row["cells"]] == ["finance", "market"]
        assert row["total"] == 2


def test_weak_is_systemic_from_three_contours():
    weak, strong = _res("BBAAAA"), _res("AAAAAA")
    three = {"finance": weak, "product": weak, "process": weak, "market": strong}
    row = _by_level(build_summary(three))["earth"]
    assert row["weak"] == LEVEL_SYSTEMIC_MIN and row["systemic_weak"]
    assert "Земля" in row["reading"] and "3 контурах из 4" in row["reading"]


def test_two_weak_of_four_is_not_systemic():
    weak, strong = _res("BBAAAA"), _res("AAAAAA")
    two = {"finance": weak, "product": weak, "process": strong, "market": strong}
    row = _by_level(build_summary(two))["earth"]
    assert row["weak"] == 2 and not row["systemic_weak"] and row["reading"] is None


def test_full_coincidence_is_systemic_even_with_two_contours():
    weak = _res("BBAAAA")
    row = _by_level(build_summary({"finance": weak, "market": weak}))["earth"]
    assert row["systemic_weak"] and "2 контурах из 2" in row["reading"]


def test_support_requires_all_contours():
    strong, other = _res("AAAAAA"), _res("AABBAA")
    s = build_summary({"finance": strong, "product": strong,
                       "process": strong, "market": other})
    human = _by_level(s)["human"]
    assert human["strong"] == 3 and not human["systemic_strong"]
    earth = _by_level(s)["earth"]
    assert earth["strong"] == 4 and earth["systemic_strong"]
    assert "опереться" in earth["reading"]


def test_legacy_snapshot_without_lines_gives_empty_matrix():
    legacy = {"combination_current": "AAAAAA", "maturity_index": 6,
              "moving_lines": [], "hexagram_current": {}, "hexagram_resulting": None}
    s = build_summary({"finance": legacy, "market": legacy})
    assert s is not None and s["levels"] == []

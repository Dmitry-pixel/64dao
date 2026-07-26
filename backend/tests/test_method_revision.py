# -*- coding: utf-8 -*-
"""
Ревизия метода: зоны предупреждений, вклад линии 5, единый порог отрыва,
прогресс по контурам. БД не требуется.
"""
import pytest

from app.company_lifecycle import REQUIRED_CONTOURS, lifecycle_progress
from app.contour_scoring import (
    BORDERLINE_HIGH,
    BORDERLINE_LOW,
    NEAR_YANG_LOW,
    NEAR_YIN_HIGH,
    compute_contour_result,
)
from app.finance_interpret import ENVIRONMENT_YIN_NOTE, build_interpretation
from app.finance_items import FINANCE_SPEC


def answers(per_block: dict[int, list[int]]) -> dict[str, int]:
    out = {}
    for block, vals in per_block.items():
        for i, v in enumerate(vals, start=1):
            out[f"{block}.{i}"] = v
    return out


BASE = {1: [3, 3, 2, 3], 2: [3, 3, 2, 3], 3: [3, 3, 2, 3],
        4: [3, 3, 3, 2], 5: [3, 3, 2, 3], 6: [3, 3, 2, 3]}


def line(res, n):
    return next(l for l in res["lines"] if l["line"] == n)


# ── Пункт 2: расширенная зона неустойчивого определения ──────────────────────
def test_borderline_zone_widened():
    assert (BORDERLINE_LOW, BORDERLINE_HIGH) == (2.25, 2.75)


@pytest.mark.parametrize("vals,expected", [
    ([3, 3, 3, 3], 2.75),   # реверсивный 3 -> 2; среднее 2.75
    ([2, 2, 2, 2], 2.25),   # реверсивный 2 -> 3; среднее 2.25
])
def test_borderline_now_catches_quarter_steps(vals, expected):
    res = compute_contour_result(answers({**BASE, 1: vals}), FINANCE_SPEC)
    l = line(res, 1)
    assert l["score"] == expected
    assert "BORDERLINE_LINE" in l["flags"], "балл в зоне 2.25–2.75 обязан помечаться"


def test_clearly_strong_line_is_not_borderline():
    res = compute_contour_result(answers({**BASE, 1: [4, 4, 1, 4]}), FINANCE_SPEC)
    assert "BORDERLINE_LINE" not in line(res, 1)["flags"]


# ── Пункт 4: приближение к порогу подвижности ────────────────────────────────
def test_near_thresholds_are_symmetric():
    assert NEAR_YANG_LOW == 3.25 and NEAR_YIN_HIGH == 1.75


def test_near_old_yang_flag():
    # 1.3 реверсивный: 2 -> 3. Эффективные 4,3,3,3 -> среднее 3.25
    res = compute_contour_result(answers({**BASE, 1: [4, 3, 2, 3]}), FINANCE_SPEC)
    l = line(res, 1)
    assert l["score"] == 3.25 and not l["moving"]
    assert "NEAR_OLD_YANG" in l["flags"]


def test_near_old_yin_flag():
    res = compute_contour_result(answers({**BASE, 1: [2, 1, 3, 2]}), FINANCE_SPEC)
    l = line(res, 1)
    assert l["score"] == 1.75 and not l["moving"]
    assert "NEAR_OLD_YIN" in l["flags"]


def test_moving_line_is_not_flagged_as_near():
    res = compute_contour_result(answers({**BASE, 1: [4, 4, 1, 4]}), FINANCE_SPEC)
    l = line(res, 1)
    assert l["moving"] and "NEAR_OLD_YANG" not in l["flags"]


# ── Пункт 1: вклад линии 5 в индекс зрелости ─────────────────────────────────
def _interp(res):
    return build_interpretation(res, {})


def test_environment_yin_is_named_in_report():
    res = compute_contour_result(answers({**BASE, 5: [1, 1, 4, 1]}), FINANCE_SPEC)
    assert line(res, 5)["symbol"] == "B"
    interp = _interp(res)
    m = interp["maturity"]
    assert m["environment_turbulent"] is True
    assert m["index_excluding_environment"] == m["index"]
    assert m["note"] and "Линия 5" in m["note"]
    assert any("Линия 5" in c for c in interp["caveats"]), "примечание обязано попасть в оговорки"


def test_no_environment_note_when_context_is_stable():
    res = compute_contour_result(answers(BASE), FINANCE_SPEC)
    assert line(res, 5)["symbol"] == "A"
    interp = _interp(res)
    assert interp["maturity"]["environment_turbulent"] is False
    assert interp["maturity"]["note"] is None
    assert not any("Линия 5" in c for c in interp["caveats"])


def test_maturity_block_counts_correctly():
    res = compute_contour_result(answers(BASE), FINANCE_SPEC)
    m = _interp(res)["maturity"]
    assert m["index"] == res["maturity_index"]
    assert m["of"] == 6
    assert m["index_excluding_environment"] == m["index"] - 1
    assert ENVIRONMENT_YIN_NOTE.count("{excl}") == 1


# ── Пункт 8: единый порог отрыва ─────────────────────────────────────────────
def test_gap_threshold_has_single_source():
    from app.contour_route import GAP_THRESHOLD as route_gap
    from app.contour_summary import GAP_THRESHOLD as summary_gap
    from app.contours import GAP_THRESHOLD as source_gap
    assert source_gap == summary_gap == route_gap == 3


# ── Пункт 5: прогресс по контурам ────────────────────────────────────────────
def test_progress_reports_missing_contours():
    p = lifecycle_progress({"finance": {"lines": []}})
    assert p["passed"] == 1 and p["required"] == REQUIRED_CONTOURS == 4
    assert p["available"] is False
    assert set(p["missing_contours"]) == {"product", "process", "market"}
    assert len(p["missing_titles"]) == 3


def test_progress_available_when_all_four_passed():
    p = lifecycle_progress({k: {"lines": []} for k in
                            ("finance", "product", "process", "market")})
    assert p["passed"] == 4 and p["available"] is True and p["missing_contours"] == []


def test_all_contours_enabled_by_default():
    from app.contour_settings import _DEFAULTS
    assert all(_DEFAULTS.values()), "жизненный цикл требует всех четырёх контуров"

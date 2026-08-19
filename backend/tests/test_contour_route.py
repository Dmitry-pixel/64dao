# -*- coding: utf-8 -*-
"""
Маршрут перехода контура (роадмап 2.1): порядок шагов, инвариант «финал =
результирующая», сводный маршрут компании. Чистая логика, БД не нужна.
"""
from app.contour_route import GAP_THRESHOLD, build_route, build_summary_route
from app.contour_scoring import compute_contour_result
from app.finance_scoring import compute_finance_result


def _line(n, symbol, moving, block="processes"):
    state = (("old_yin" if symbol == "B" else "old_yang") if moving
             else ("young_yin" if symbol == "B" else "young_yang"))
    return {"line": n, "block": block, "score": 0.0, "symbol": symbol,
            "state": state, "moving": moving, "flags": []}


def _result(maturity, moving_set, combo=None):
    if combo is None:
        combo = "".join("B" if n in moving_set else "A" for n in range(1, 7))
    lines = [_line(n, combo[n - 1], n in moving_set) for n in range(1, 7)]
    return {"lines": lines, "combination_current": combo,
            "moving_lines": sorted(moving_set), "maturity_index": maturity,
            "hexagram_current": None, "hexagram_resulting": None}


# ── build_route ───────────────────────────────────────────────────────────────

def test_control_case_single_step():
    """Контрольный кейс §3.7: одна подвижная линия 6 (старый Инь) → 1 шаг,
    финал = результирующая (AAAABB → AAAABA, №14)."""
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    r = compute_finance_result(a)
    route = build_route(r["lines"], r["combination_current"])
    assert len(route) == 1
    assert route[0]["line"] == 6
    assert route[0]["from_state"] == "old_yin"
    assert route[0]["action_key"] == "line6_yin"
    assert route[0]["hexagram_after"]["code"] == r["combination_resulting"]
    assert route[0]["hexagram_after"]["number"] == 14


def test_step_order_yin_before_yang_then_by_line():
    """§4.2: подвижные 2 (старый Ян), 1 и 5 (старый Инь) → порядок 1 → 5 → 2."""
    combo = "BAAABA"  # line1=B,2=A,3=A,4=A,5=B,6=A
    lines = [
        _line(1, "B", True), _line(2, "A", True), _line(3, "A", False),
        _line(4, "A", False), _line(5, "B", True), _line(6, "A", False),
    ]
    route = build_route(lines, combo)
    assert [s["line"] for s in route] == [1, 5, 2]
    assert [s["hexagram_after"]["code"] for s in route] == ["AAAABA", "AAAAAA", "ABAAAA"]
    assert route[-1]["hexagram_after"]["code"] == "ABAAAA"  # = результирующая
    assert route[1]["from_state"] == "old_yin" and route[2]["from_state"] == "old_yang"
    assert route[2]["action_key"] == "line2_oldyang"


def test_no_moving_no_route():
    lines = [_line(n, "A", False) for n in range(1, 7)]
    assert build_route(lines, "AAAAAA") == []


def test_six_moving_six_steps():
    lines = [_line(n, "A", True) for n in range(1, 7)]  # все старый Ян
    route = build_route(lines, "AAAAAA")
    assert len(route) == 6
    assert [s["line"] for s in route] == [1, 2, 3, 4, 5, 6]
    assert route[-1]["hexagram_after"]["code"] == "BBBBBB"


def test_line_key_from_block_field():
    lines = [_line(1, "B", True, block="strategy")]
    lines += [_line(n, "A", False) for n in range(2, 7)]
    route = build_route(lines, "BAAAAA")
    assert route[0]["line_key"] == "strategy"


# ── build_summary_route ───────────────────────────────────────────────────────

def test_summary_none_when_single_contour():
    assert build_summary_route({"finance": _result(4, {6})}) is None


def test_summary_orders_stages_by_maturity_asc():
    s = build_summary_route({
        "finance": _result(5, {6}),
        "product": _result(2, {1, 2}),
    })
    assert [st["contour"] for st in s["stages"]] == ["product", "finance"]
    assert s["stages"][0]["stage"] == 1 and s["stages"][1]["stage"] == 2
    assert s["stages"][0]["entry_line"] == 1


def test_summary_stable_contour_excluded_from_stages():
    s = build_summary_route({
        "finance": _result(3, {2}),
        "product": _result(4, set()),   # без подвижных линий
    })
    assert [st["contour"] for st in s["stages"]] == ["finance"]
    assert s["stable"] == ["product"]


def test_summary_focus_when_gap_ge_threshold():
    s = build_summary_route({
        "finance": _result(1, {3}),
        "product": _result(1 + GAP_THRESHOLD, {1}),
    })
    assert s["focus_first"] is True
    assert s["stages"][0]["contour"] == "finance"


def test_summary_four_contours_tiebreak_and_stable():
    s = build_summary_route({
        "finance": _result(4, {1}),
        "product": _result(3, {1, 2}),
        "process": _result(3, {1, 2, 3}),   # тот же индекс, больше подвижных → раньше product
        "market":  _result(4, set()),        # стабильный
    })
    assert [st["contour"] for st in s["stages"]] == ["process", "product", "finance"]
    assert s["stable"] == ["market"]

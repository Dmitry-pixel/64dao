# -*- coding: utf-8 -*-
"""Тип перехода направления Метода 3 между двумя замерами (чистые функции).

Примеры совпадают с листом «Примеры» черновика правил
(claude/m3-transition-rules-draft.md): если правило меняется, меняются оба.
"""
import pytest

from app.m3_transition import TYPE_TITLES, classify

YIN_MAX, OLD_YIN, OLD_YANG = 2.5, 1.5, 3.5


def snap(scores):
    """Снимок как в m3_results: символ по 2,5, назревшее ≤ 1,5, риск ≥ 3,5."""
    return {
        "scores": scores,
        "symbols": "".join("A" if s >= YIN_MAX else "B" for s in scores),
        "target_lines": [i + 1 for i, s in enumerate(scores) if s <= OLD_YIN],
        "risk_lines": [i + 1 for i, s in enumerate(scores) if s >= OLD_YANG],
    }


def run(prev, now, intent=None):
    return classify(snap(prev), snap(now), intent)


CASES = [
    ("T1", [4, 4, 4, 3, 3, 3], [2, 2, 2, 1.5, 3, 3]),
    ("T2", [3, 3, 3, 3.5, 3, 3], [3, 3, 3, 2, 3, 3]),
    ("T3", [1.5, 3, 3, 3.5, 3, 3], [3, 3, 3, 2, 3, 3]),
    ("T4", [1.5, 3, 1, 3, 3, 3], [3, 3, 3, 3, 3, 3]),
    ("T5", [1.5, 3, 1, 3, 3, 3], [3, 3, 1.5, 3, 3, 3]),
    ("T6", [3, 3, 3, 2, 3, 2], [3, 3, 3, 3, 3, 3]),
    ("T7", [2, 3, 3, 3, 3, 3], [3, 3, 3, 3, 3, 3]),
    ("T8", [3, 3, 2.6, 3, 3, 3], [3, 3, 2.4, 3, 3, 3]),
    ("T9", [1.5, 3, 3, 3, 3, 3], [2, 3, 3, 3, 3, 3]),
    ("T10", [2, 3, 3, 3, 2, 3], [3, 3, 3, 3, 3, 2]),
]


@pytest.mark.parametrize("want,prev,now", CASES, ids=[c[0] for c in CASES])
def test_examples_match_rules_sheet(want, prev, now):
    r = run(prev, now)
    assert r["type"] == want
    assert r["type_title"] == TYPE_TITLES[want]


def test_borderline_flip_is_not_a_change():
    r = run([3, 3, 2.6, 3, 3, 3], [3, 3, 2.4, 3, 3, 3])
    assert r["changed"] == [] and r["borderline"] == [3] and r["scale"] == "0"


def test_exact_threshold_counts_despite_float_error():
    # 2.8 - 2.3 в float = 0.49999…: сдвиг ровно на порог обязан считаться.
    r = run([3, 3, 3, 3, 3, 2.3], [3, 3, 3, 3, 3, 2.8])
    assert r["changed"] == [6] and r["borderline"] == []


def test_axes():
    r = run([1.5, 3, 3, 3.5, 3, 3], [3, 3, 3, 2, 3, 3])
    assert (r["scale"], r["where"], r["direction"]) == ("2-3", "обе", "перераспределение")
    assert (r["target"], r["risk"]) == ("полностью", "реализовался")


def test_intent_axis():
    prev, now = [1.5, 1.5, 3, 3.5, 3, 3], [3, 1.5, 3, 3.5, 3, 3]
    assert run(prev, now)["intent"]["value"] == "нет данных"
    assert run(prev, now, {"strengthen": [1]})["intent"]["value"] == "совпало"
    r = run(prev, now, {"strengthen": [1, 2], "hold": [4]})
    assert r["intent"] == {"value": "частично", "met": [1, 4], "missed": [2]}
    assert run(prev, now, {"strengthen": [2]})["intent"]["value"] == "против"


def test_every_type_reachable_and_unique():
    import random
    random.seed(7)
    grid = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
    seen = set()
    for _ in range(20000):
        p = [random.choice(grid) for _ in range(6)]
        n = [min(5, max(1, x + random.choice([-1.5, -1, -0.5, 0, 0, 0.5, 1, 1.5]))) for x in p]
        seen.add(run(p, n)["type"])
    assert seen == set(TYPE_TITLES)

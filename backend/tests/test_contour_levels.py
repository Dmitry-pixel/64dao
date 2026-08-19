# -*- coding: utf-8 -*-
"""
Три уровня (сань-цай): таблица состояний, независимость от балла,
результирующее состояние, устойчивость к неполному снимку.
Чистая логика, БД не нужна.

Ключевой инвариант: состояние уровня определяют ТОЛЬКО символы пары.
Балл в него не входит — иначе разрез начнёт спорить с гексаграммой.
"""
import pytest

from app.contour_levels import LEVELS, STATE_LABELS, levels_of
from app.contour_scoring import compute_contour_result
from app.contours import LINE_KEYS, get_spec

# ── Хелперы ──────────────────────────────────────────────────────────────────

def _line(n: int, symbol: str, moving: bool, score: float = 2.5) -> dict:
    state = ("old_yang" if moving else "young_yang") if symbol == "A" else \
            ("old_yin" if moving else "young_yin")
    return {
        "line": n, "block": LINE_KEYS[n - 1], "score": score,
        "symbol": symbol, "state": state, "moving": moving, "flags": [],
    }


def res(combo: str = "AAAAAA", moving: list[int] | None = None,
        scores: dict[int, float] | None = None) -> dict:
    """Снимок result контура."""
    moving = moving or []
    scores = scores or {}
    lines = [_line(i, combo[i - 1], i in moving, scores.get(i, 2.5)) for i in range(1, 7)]
    resulting = "".join(
        ("B" if c == "A" else "A") if (i + 1) in moving else c
        for i, c in enumerate(combo)
    ) if moving else None
    return {
        "lines": lines,
        "combination_current": combo,
        "combination_resulting": resulting,
        "moving_lines": moving,
        "maturity_index": combo.count("A"),
    }


def _combo_for(level_index: int, code: str) -> str:
    """Комбинация, где у нужного уровня заданный код, у остальных Ян."""
    parts = ["AA", "AA", "AA"]
    parts[level_index] = code
    return "".join(parts)


# ── 1. Таблица состояний: 4 кода на каждом из 3 уровней ──────────────────────

@pytest.mark.parametrize("level_index", [0, 1, 2])
@pytest.mark.parametrize("code,label", sorted(STATE_LABELS.items()))
def test_state_table(level_index: int, code: str, label: str):
    got = levels_of(res(_combo_for(level_index, code)))[level_index]
    assert got["code"] == code
    assert got["label"] == label
    assert got["content_key"] == f"{LEVELS[level_index][0]}_{code}"


def test_level_order_and_pairs():
    got = levels_of(res())
    assert [l["level"] for l in got] == ["earth", "human", "heaven"]
    assert [l["lines"] for l in got] == [[1, 2], [3, 4], [5, 6]]


def test_line_titles_come_from_registry():
    earth = levels_of(res())[0]
    assert earth["line_titles"] == ["Процессы", "Технологии и системы"]


# ── 2. Состояние не зависит от балла ─────────────────────────────────────────

def test_state_independent_of_score():
    """Символы те же, баллы разные: код и ярлык обязаны совпасть."""
    low = levels_of(res("ABABAB", scores={i: 2.51 for i in range(1, 7)}))
    high = levels_of(res("ABABAB", scores={i: 4.00 for i in range(1, 7)}))
    assert [l["code"] for l in low] == [l["code"] for l in high]
    assert [l["label"] for l in low] == [l["label"] for l in high]
    assert low[0]["score"] != high[0]["score"]


def test_score_is_pair_average_rounded():
    got = levels_of(res("AAAAAA", scores={1: 3.33, 2: 2.00}))[0]
    assert got["score"] == 2.67


# ── 3. Результирующее состояние ──────────────────────────────────────────────

def test_no_resulting_without_moving():
    for lv in levels_of(res("ABABAB")):
        assert lv["moving"] == 0
        assert lv["code_resulting"] is None
        assert lv["label_resulting"] is None


def test_resulting_only_on_level_with_moving_line():
    earth, human, heaven = levels_of(res("BBAAAA", moving=[1]))
    assert earth["moving"] == 1 and earth["moving_lines"] == [1]
    assert earth["code"] == "BB" and earth["code_resulting"] == "AB"
    assert earth["label_resulting"] == "Импульс"
    assert human["code_resulting"] is None and heaven["code_resulting"] is None


def test_both_lines_moving():
    earth = levels_of(res("ABAAAA", moving=[1, 2]))[0]
    assert earth["moving"] == 2 and earth["moving_lines"] == [1, 2]
    assert earth["code"] == "AB" and earth["code_resulting"] == "BA"


# ── 4. Неполный снимок не ломает отчёт ───────────────────────────────────────

@pytest.mark.parametrize("bad", [
    {}, None,
    {"combination_current": "AAAAAA"},                  # нет lines
    {"lines": [], "combination_current": "AAAAAA"},
    {"lines": [_line(i, "A", False) for i in range(1, 5)],
     "combination_current": "AAAAAA"},                  # линий меньше шести
    {"lines": [_line(i, "A", False) for i in range(1, 7)],
     "combination_current": "AAA"},                     # обрезанная комбинация
    {"lines": [_line(i, "A", False) for i in range(1, 7)],
     "combination_current": "AAAAAX"},                  # чужой символ
])
def test_incomplete_snapshot_returns_empty(bad):
    assert levels_of(bad) == []


def test_broken_resulting_is_ignored_not_fatal():
    snap = res("BBAAAA", moving=[1])
    snap["combination_resulting"] = "XX"
    assert levels_of(snap)[0]["code_resulting"] is None


# ── 5. Оговорка про линию 5 ──────────────────────────────────────────────────

def test_caveat_only_on_heaven():
    earth, human, heaven = levels_of(res())
    assert earth["caveat"] is None and human["caveat"] is None
    assert heaven["caveat"] and "обстановку, а не компанию" in heaven["caveat"]


# ── 6. Интеграция с настоящим скорингом ──────────────────────────────────────

def test_on_real_scoring_output():
    spec = get_spec("finance")
    ans = {}
    for it in spec.items:
        v = 4 if it["block"] % 2 else 1
        ans[it["item_id"]] = 5 - v if it["reverse"] else v
    got = levels_of(compute_contour_result(ans, spec))
    assert len(got) == 3
    assert all(l["code"] in STATE_LABELS for l in got)

# -*- coding: utf-8 -*-
"""
Инварианты реестра контуров (план контуров §4.2).
Чистая логика, БД не нужна.
"""
import pytest

from app.contours import (
    CONTOURS, CONTOUR_ORDER, INTRO_TEXTS, LINE_KEYS, REVERSE_ITEMS,
)
from app.contour_scoring import compute_contour_result

KEYS = sorted(CONTOURS)


@pytest.mark.parametrize("key", KEYS)
def test_24_items_in_6_blocks(key):
    spec = CONTOURS[key]
    assert len(spec.items) == 24
    by_block: dict[int, list] = {}
    for it in spec.items:
        by_block.setdefault(it["block"], []).append(it)
    assert sorted(by_block) == [1, 2, 3, 4, 5, 6]
    assert all(len(v) == 4 for v in by_block.values())


@pytest.mark.parametrize("key", KEYS)
def test_reverse_exactly_one_per_block(key):
    rev = [i["item_id"] for i in CONTOURS[key].items if i["reverse"]]
    assert sorted(rev) == sorted(REVERSE_ITEMS)
    per_block: dict[int, int] = {}
    for iid in rev:
        b = int(iid.split(".")[0])
        per_block[b] = per_block.get(b, 0) + 1
    assert set(per_block.values()) == {1}
    assert sorted(per_block) == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize("key", KEYS)
def test_veto_only_4_1(key):
    assert [i["item_id"] for i in CONTOURS[key].items if i["veto"]] == ["4.1"]


@pytest.mark.parametrize("key", KEYS)
def test_line_keys_uniform(key):
    spec = CONTOURS[key]
    assert [spec.blocks[b]["key"] for b in sorted(spec.blocks)] == LINE_KEYS


@pytest.mark.parametrize("key", KEYS)
def test_item_ids_unique_and_texts_filled(key):
    spec = CONTOURS[key]
    ids = [i["item_id"] for i in spec.items]
    assert len(set(ids)) == 24
    assert all(len(i["text"].strip()) > 20 for i in spec.items)


@pytest.mark.parametrize("key", KEYS)
def test_scoring_runs_for_every_contour(key):
    spec = CONTOURS[key]
    r = compute_contour_result({i: 3 for i in spec.item_ids}, spec)
    assert len(r["combination_current"]) == 6
    assert 1 <= r["hexagram_current"]["number"] <= 64
    assert r["maturity_index"] in range(0, 7)


def test_order_covers_registry_and_starts_with_finance():
    assert set(CONTOUR_ORDER) == set(CONTOURS)
    assert CONTOUR_ORDER[0] == "finance"


def test_intro_text_for_every_contour():
    assert all(INTRO_TEXTS.get(k, "").strip() for k in CONTOURS)


def test_texts_differ_between_contours():
    """Формулировки не должны быть скопированы между контурами дословно:
    вся контурная специфика живёт именно в них."""
    for iid in ("1.1", "3.1", "6.1"):
        texts = {k: next(i["text"] for i in CONTOURS[k].items if i["item_id"] == iid)
                 for k in KEYS}
        assert len(set(texts.values())) == len(KEYS), f"дубли в {iid}: {texts}"

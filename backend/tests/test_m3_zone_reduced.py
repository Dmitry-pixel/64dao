# -*- coding: utf-8 -*-
"""
Резолюция вида zone_reduced с откатом к zone.

БД не нужна: compose_narrative — чистая функция от снимка и словаря контента.
"""
from types import SimpleNamespace

import pytest

from app.m3_service import compose_narrative


def block(title, body, mistake=None):
    """Заглушка M3Content: compose_narrative читает только эти три поля."""
    return SimpleNamespace(title=title, body=body, mistake=mistake)


def content():
    return {
        ("zone", "high_low"): block("Рынок исчерпан, удержание", "общий", "ошибка общая"),
        ("zone_reduced", "high_low"): block("Рынок исчерпан, удержание", "одиночный", "ошибка одиночная"),
        ("zone", "mid_high"): block("Незавершённое ядро", "общий", "ошибка общая"),
        ("weak_line", "weak_L3"): block("Слабая 3", "тело"),
        ("strong_line", "strong_L2"): block("Сильная 2", "тело"),
        ("tension", "P4"): block("P4", "тело"),
    }


def result(cell_key="high_low", reduced=False):
    return {"cell_key": cell_key, "weak_line": 3, "strong_line": 2,
            "tensions": ["P4"], "reduced": reduced}


def zone_of(narrative):
    zones = [b for b in narrative if b["kind"] == "zone"]
    assert len(zones) == 1
    return zones[0]


def test_full_mode_ignores_reduced_variant():
    z = zone_of(compose_narrative(result(reduced=False), content()))
    assert z["body"] == "общий"
    assert z["mistake"] == "ошибка общая"


def test_reduced_mode_prefers_reduced_variant():
    z = zone_of(compose_narrative(result(reduced=True), content()))
    assert z["body"] == "одиночный"
    assert z["mistake"] == "ошибка одиночная"


def test_reduced_mode_falls_back_to_zone():
    z = zone_of(compose_narrative(result("mid_high", reduced=True), content()))
    assert z["body"] == "общий"


def test_kind_stays_zone_outside():
    for reduced in (False, True):
        z = zone_of(compose_narrative(result(reduced=reduced), content()))
        assert z["kind"] == "zone"
        assert z["key"] == "high_low"


def test_missing_zone_does_not_break_narrative():
    only = {("weak_line", "weak_L3"): block("Слабая 3", "тело")}
    out = compose_narrative(result(reduced=True), only)
    assert [b["kind"] for b in out] == ["weak_line"]


def test_mistake_only_on_zone():
    out = compose_narrative(result(reduced=True), content())
    assert all(b["mistake"] is None for b in out if b["kind"] != "zone")


@pytest.mark.parametrize("reduced", [False, True])
def test_block_order_unchanged(reduced):
    out = compose_narrative(result(reduced=reduced), content())
    assert [b["kind"] for b in out] == ["zone", "weak_line", "strong_line", "tension"]

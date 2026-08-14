# -*- coding: utf-8 -*-
"""
Границы числа направлений на входе API.

Проверка жила литералом OBJECTS_MIN = 3 в схеме, когда расчёт уже работал
от единицы: сокращённый режим был недостижим через интерфейс, направления
не сохранялись. Существующие тесты этого не ловили, потому что звали
m3_service и m3_scoring напрямую, минуя схему.
"""
import pytest

from app.m3_config import DEFAULT_M3_CONFIG, read_m3_config
from app.m3_schemas import M3ObjectIn, M3ObjectsPut, _bounds


def obj(position: int, **kw) -> M3ObjectIn:
    return M3ObjectIn(position=position, name=f"Направление {position}", **kw)


def test_default_config_allows_single_object():
    assert DEFAULT_M3_CONFIG["objects_min"] == 1


def test_bounds_follow_config_not_literals():
    """Схема обязана брать границы оттуда же, откуда их берёт расчёт."""
    cfg = read_m3_config()
    assert _bounds() == (cfg["objects_min"], cfg["objects_max"])


@pytest.mark.parametrize("n", [1, 2, 3, 8])
def test_accepts_sizes_from_one(n):
    lo, hi = _bounds()
    if not lo <= n <= hi:
        pytest.skip(f"конфиг сузил границы до {lo}..{hi}")
    M3ObjectsPut(objects=[obj(i + 1) for i in range(n)])


@pytest.mark.parametrize("n", [0, 9])
def test_rejects_out_of_range(n):
    with pytest.raises(Exception):
        M3ObjectsPut(objects=[obj(i + 1) for i in range(n)])


def test_single_object_share_below_coverage_rejected():
    """
    Фиксирует действующее поведение, а не одобряет его. Одно направление
    с долей 20% отбивается проверкой покрытия: правило MIN_COVERAGE писалось
    под портфель. Для диагностики одного направления из большего бизнеса
    оно спорно, решение за владельцем. Обход есть: доля необязательна.
    """
    with pytest.raises(Exception):
        M3ObjectsPut(objects=[obj(1, revenue_share=20.0)])

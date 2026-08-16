# -*- coding: utf-8 -*-
"""
Границы и пороги на входе API направлений.

Проверка числа направлений жила литералом OBJECTS_MIN = 3 в схеме, когда
расчёт уже работал от единицы: сокращённый режим был недостижим через
интерфейс, направления не сохранялись. Существующие тесты этого не ловили,
потому что звали m3_service и m3_scoring напрямую, минуя схему.

Пороги долей — MIN_SHARE и MIN_COVERAGE — охраняют портфельные разделы
и ниже portfolio_min не применяются: см. test_coverage_applies_at_and_above.
"""
import pytest

from app.m3_config import DEFAULT_M3_CONFIG, read_m3_config
from app.m3_schemas import (
    MIN_COVERAGE, MIN_SHARE, M3ObjectIn, M3ObjectsPut, _bounds,
)


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


def test_single_object_share_below_coverage_accepted():
    """
    Раньше здесь фиксировалось обратное: одно направление с долей 20%
    отбивалось проверкой покрытия. Правило писалось под портфель и охраняет
    карту долей выручки, а ниже portfolio_min отчёт эту карту не печатает —
    ограничение работало ради раздела, которого не будет.

    Третий случай ловушки «подавление раздела не отменяет вопроса на входе»:
    до него были шаг Р* и порядок приоритетов.
    """
    M3ObjectsPut(objects=[obj(1, revenue_share=20.0)])


def test_single_object_share_below_min_share_accepted():
    """
    MIN_SHARE обоснована тем же самым: «не различимо на карте портфеля
    и искажает индекс защиты». Оба раздела подавлены вместе, значит и пороги
    снимаются вместе. Иначе обход половинчатый: направление на 2% выручки
    всей компании по-прежнему не ввести.
    """
    M3ObjectsPut(objects=[obj(1, revenue_share=2.0)])


def test_coverage_applies_at_and_above_portfolio_min():
    """
    Парный инвариант: проверка покрытия действует тогда и только тогда, когда
    отчёт печатает карту долей, то есть от portfolio_min и выше. Обе стороны
    границы проверяются одним тестом — как у test_ranks_asked_iff_comparison.
    """
    pmin = read_m3_config()["portfolio_min"]
    lo, hi = _bounds()
    share = MIN_COVERAGE / pmin / 2      # заведомо недобирает покрытие
    if share < MIN_SHARE:
        pytest.skip("конфиг сделал долю ниже MIN_SHARE, порог не различить")

    if pmin - 1 >= lo:
        M3ObjectsPut(objects=[obj(i + 1, revenue_share=share)
                              for i in range(pmin - 1)])
    if pmin <= hi:
        with pytest.raises(Exception, match="покрывают"):
            M3ObjectsPut(objects=[obj(i + 1, revenue_share=share)
                                  for i in range(pmin)])


def test_share_sum_over_100_rejected_below_portfolio_min():
    """
    Сумма долей выше 100% — арифметика, а не портфельное правило, и порогом
    не снимается. Иначе снятие превратилось бы в отключение проверки ввода.
    """
    with pytest.raises(Exception, match="превышает 100"):
        M3ObjectsPut(objects=[obj(1, revenue_share=60.0),
                              obj(2, revenue_share=60.0)])


def test_new_venture_limit_holds_without_shares():
    """
    Проверка «новым может быть отмечено только одно» стояла после раннего
    возврата по пустым долям: портфель без единой заполненной доли проходил
    с двумя новыми направлениями. Дыра закрыта переносом проверки вверх.
    """
    with pytest.raises(Exception, match="Новым направлением"):
        M3ObjectsPut(objects=[obj(1, is_new_venture=True),
                              obj(2, is_new_venture=True),
                              obj(3)])


async def test_limits_endpoint_exposes_share_constants():
    """
    Форма держала свои копии MIN_SHARE и MIN_COVERAGE, а /api/m3/limits их
    не отдавал. После снятия порога на сервере форма продолжила бы отбивать
    ввод: это третий случай расхождения копий, до него были objects_min
    и жёсткая тройка на фронте.
    """
    from app.routers.m3 import limits

    out = await limits()
    cfg = read_m3_config()
    assert out.min_share == MIN_SHARE
    assert out.min_coverage == MIN_COVERAGE
    assert out.portfolio_min == cfg["portfolio_min"]
    assert out.objects_min == cfg["objects_min"]

# -*- coding: utf-8 -*-
"""
Фабрика снимка не должна отставать от контракта.

За 8 августа контракт словаря результата расширялся дважды — `weights`
и `cell_breakdown`, — и оба раза синтетика в тестах отставала. Ловили это
уже после того, как работа объявлялась готовой.

Проверка здесь не сверяет список ключей: такой список сам стал бы третьей
копией контракта. Вместо этого результат фабрики прогоняется через всех
потребителей. Не хватило ключа — падение тут, а не в отчёте через месяц.
"""
import pytest

from app import m3_portfolio as pf
from app import m3_verdict as vd
from app.m3_config import industry_weights
from app.m3_map import layout, render_map_svg
from app.m3_pdf import (
    cell_breakdown_block, facts_line, hexagram_line, lines_block,
)
from tests import m3_factory as factory


MOVING = dict(
    symbols="BABAAA", cell_strength="low", cell_attract="high",
    mobility={"1": "old_yin", "6": "old_yang"},
    target_hex=10, target_lines=[1], risk_hex=41, risk_lines=[6],
)


class _Obj:
    revenue = 100
    revenue_dynamics = 5
    revenue_share = 45.0
    profitability = "profitable"


@pytest.mark.parametrize("over", [{}, MOVING])
def test_factory_result_survives_every_consumer(over):
    r = factory.result(**over)

    verdict = vd.verdict_for(r)
    assert verdict["verdict"]

    for kind in ("target", "risk"):
        move = vd.transition(r, kind)
        # None допустим — вектора может не быть; KeyError не допустим.
        assert move is None or move["phrase"]

    assert lines_block(r)
    assert hexagram_line(r)
    assert facts_line(r, _Obj())
    assert cell_breakdown_block(r)

    assert pf.yin_table([r])
    pf.constraints([r])
    assert pf.rank_comparison([r], [1])

    assert layout([r], {r["object_id"]: 45.0})
    assert render_map_svg([r], {r["object_id"]: 45.0})


def test_factory_rebuilds_breakdown_for_overridden_symbols():
    """
    Тест, задавший символы, не обязан помнить про cell_breakdown: иначе
    фабрика перекладывает контракт обратно на вызывающего.
    """
    r = factory.result(symbols="AAAAAA", cell_strength="high",
                       cell_attract="high", weights=industry_weights(2))
    assert r["cell_breakdown"]["strength"]["sum"] == 100
    assert r["cell_key"] == "high_high"


def test_factory_respects_explicit_breakdown():
    given = {"strength": {"level": "low", "sum": 0, "total": 100, "lines": []},
             "attract": {"level": "low", "sum": 0, "total": 100, "lines": []}}
    assert factory.result(cell_breakdown=given)["cell_breakdown"] is given

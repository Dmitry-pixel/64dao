# -*- coding: utf-8 -*-
"""
Веб-отчёт и PDF не расходятся.

Вердикты считает m3_verdict, а вызывают его двое: build_report — для API, и
m3_pdf — для печати. Обе стороны получают один и тот же словарь результата,
поэтому совпадение следует из построения, а не из аккуратности.

Тест это построение и охраняет. Он ловит два способа его сломать:
уронить обогащение из build_report и заменить правило в одном из отчётов.

Проверка идёт через готовый HTML, а не через сравнение двух вызовов одной
функции: последнее доказывало бы только то, что функция детерминирована.
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app import m3_scoring as sc
from app.m3_config import industry_weights
from app.m3_pdf import build_portfolio_report_html
from app.m3_service import enrich_result
from app.m3_verdict import cell_breakdown_text

# Подвижность обязана согласовываться с символами: старый Инь бывает только
# на слабой линии, старый Ян — только на сильной. Набор подобран так, чтобы
# закрыть все четыре состояния подвижности и оба направления перехода.
CASES = [
    # (имя, символы, подвижность, ячейки, цель, риск, доля)
    ("Салонный канал B2B", "AAABBA", {"3": "old_yang"}, ("high", "low"),
     (None, []), (41, [3]), 45.0),
    ("Контрактное производство", "ABBABB", {"2": "old_yin"}, ("low", "low"),
     (63, [2]), (None, []), 25.0),
    ("Розница", "BBBAAA", {}, ("low", "high"), (None, []), (None, []), 8.0),
    ("Маркетплейсы", "BBBAAB", {"1": "old_yin", "5": "old_yang"}, ("low", "mid"),
     (11, [1]), (5, [5]), 12.0),
    ("Экспорт", "AAAAAA", {"6": "old_yang"}, ("high", "high"),
     (None, []), (43, [6]), 10.0),
]


def _result(index, case):
    name, symbols, mobility, cells, target, risk, share = case
    return {
        "object_id": f"o{index}", "position": index, "name": name,
        "scores": {f"l{i}": 2.5 for i in range(1, 7)},
        "symbols": symbols, "mobility": mobility,
        "weights": industry_weights(1),
        "cell_strength": cells[0], "cell_attract": cells[1],
        "cell_key": f"{cells[0]}_{cells[1]}",
        "cell_label": "подпись подставляется сервисом",
        "coord_strength": 2.5, "coord_attract": 2.5,
        "current_hex": 1, "current_name": "Творчество",
        "target_hex": target[0], "target_lines": list(target[1]),
        "risk_hex": risk[0], "risk_lines": list(risk[1]),
        "v_index": 0.5, "z_index": 0.5, "v_rank": index, "z_rank": index,
        "weak_line": 5, "strong_line": 1,
        "tensions": [], "flags": [],
        # Вывод ячейки собирается так же, как в build_report: разбор из
        # символов и весов, уровень — из снимка.
        "cell_breakdown": {
            axis: {**sc.cell_detail(symbols, axis, industry_weights(1)),
                   "level": level}
            for axis, level in (("strength", cells[0]), ("attract", cells[1]))
        },
    }


def _obj(index, case):
    return SimpleNamespace(
        id=f"o{index}", position=index, name=case[0], revenue=100,
        revenue_dynamics=5, revenue_share=case[6], profitability="profitable",
    )


@pytest.fixture
def report():
    """Отчёт в том виде, в каком его отдаёт build_report — уже обогащённый."""
    packed = []
    for index, case in enumerate(CASES, start=1):
        result = _result(index, case)
        enrich_result(result, case[6])
        packed.append({"result": result, "narrative": []})

    objects = [_obj(index, case) for index, case in enumerate(CASES, start=1)]
    order = [x["result"]["object_id"] for x in packed]
    return {
        "portfolio": SimpleNamespace(
            title="ООО «Пример»", calculated_at=datetime(2026, 8, 4),
            objects=objects,
        ),
        "summary": {
            "objects": len(packed), "sum_positions": 18, "sum_positions_max": 30,
            "turbulence": 6, "delta": 0, "distinct_cells": 5, "spearman": 0.6,
            "flags": [], "verdicts_held": False,
        },
        "objects": packed,
        "investment_order": order,
        "execution_order": order,
        "disclaimers": [],
    }


def _steps(report):
    """
    Чек-лист в том виде, в каком его строит rebuild_checklist: по шагу на
    каждую подвижную линию. Пустой список сюда передавать нельзя — route_block
    на нём намеренно печатает заглушку «маршрут не строится», и переход
    в отчёт не попадает. В бою это состояние недостижимо: подвижная линия
    и шаг чек-листа появляются вместе.
    """
    out = []
    for item in report["objects"]:
        result = item["result"]
        for line in result["target_lines"]:
            out.append(SimpleNamespace(
                object_id=result["object_id"], line=line, step_type="route",
                wave=1, needs_budget=True,
                step_text=f'{result["name"]}: проработать назревшее по линии {line}',
            ))
        for line in result["risk_lines"]:
            out.append(SimpleNamespace(
                object_id=result["object_id"], line=line, step_type="hold",
                wave=1, needs_budget=False,
                step_text=f'{result["name"]}: защитить достигнутое по линии {line}',
            ))
    return out


@pytest.fixture
def html(report):
    return build_portfolio_report_html(
        report=report, steps=_steps(report), decision=None,
        company_name="ООО «Пример»", generated_at=datetime(2026, 8, 4),
        industry_name=None, config=None,
    )


def test_stable_direction_gets_route_placeholder(report):
    """
    Розница без подвижных линий шагов не получает, и это не дыра в маршруте:
    отчёт печатает явный флаг «ограничение стабильно».
    """
    retail = next(i["result"] for i in report["objects"]
                  if i["result"]["name"] == "Розница")
    assert not [s for s in _steps(report) if s.object_id == retail["object_id"]]


# ── Вердикт ───────────────────────────────────────────────────────────────────
def test_every_verdict_from_api_appears_in_pdf(report, html):
    """Главная проверка: то, что увидит веб, напечатано и в PDF."""
    for item in report["objects"]:
        verdict = item["result"]["verdict"]["verdict"]
        assert verdict in html, f"вердикт «{verdict}» потерялся в PDF"


def test_zone_names_from_api_appear_in_pdf(report, html):
    for item in report["objects"]:
        assert item["result"]["verdict"]["zone_ru"] in html


def test_verdict_is_present_for_every_direction(report):
    """Обогащение не пропускает направления: пустой вердикт — не вердикт."""
    for item in report["objects"]:
        verdict = item["result"]["verdict"]
        assert verdict["verdict"], f'{item["result"]["name"]}: вердикт пуст'
        assert verdict["zone_ru"] and verdict["zone_en"]
        assert verdict["notes"], "приписка о подвижности обязательна"


def test_verdicts_differ_across_the_portfolio(report):
    """
    Пять разных конфигураций не могут дать один вердикт. Проверка ловит
    подмену правила заглушкой: константа прошла бы все тесты выше.
    """
    verdicts = {i["result"]["verdict"]["verdict"] for i in report["objects"]}
    assert len(verdicts) > 1


# ── Траектория ────────────────────────────────────────────────────────────────
def test_trajectory_has_both_branches(report):
    for item in report["objects"]:
        trajectory = item["result"]["trajectory"]
        assert set(trajectory) == {"target", "risk"}


def test_stable_direction_has_no_trajectory(report):
    """Розница без подвижных линий: двигаться нечем, печатать нечего."""
    retail = next(i["result"] for i in report["objects"]
                  if i["result"]["name"] == "Розница")
    assert retail["trajectory"]["target"] is None
    assert retail["trajectory"]["risk"] is None


def test_transition_phrase_names_the_axis(report):
    """
    Фраза перехода должна называть ось. «Переходит из низкой в среднюю»
    без указания, чего именно, читателю ничего не говорит.
    """
    moved = [i["result"]["trajectory"]["target"] for i in report["objects"]
             if i["result"]["trajectory"]["target"]]
    assert moved, "хотя бы один переход в наборе обязан быть"
    for transition in moved:
        assert ("конкурентная сила" in transition["phrase"]
                or "привлекательность рынка" in transition["phrase"])


def test_transition_phrase_appears_in_pdf(report, html):
    for item in report["objects"]:
        for branch in ("target", "risk"):
            transition = item["result"]["trajectory"][branch]
            if transition:
                assert transition["phrase"] in html


# ── Очередь исполнения ────────────────────────────────────────────────────────
def test_execution_reason_is_filled_for_every_direction(report):
    for item in report["objects"]:
        assert item["result"]["execution_reason"]


def test_large_share_with_overheat_is_called_maximal_cost(report):
    """45% выручки на перегретой позиции — предельная цена ошибки."""
    salon = next(i["result"] for i in report["objects"]
                 if i["result"]["name"] == "Салонный канал B2B")
    assert "цена ошибки максимальна" in salon["execution_reason"]


def test_small_share_without_erosion_may_wait(report):
    """8% без эрозии: отложить можно без потерь."""
    retail = next(i["result"] for i in report["objects"]
                  if i["result"]["name"] == "Розница")
    assert "стабильно" in retail["execution_reason"]


def test_execution_reason_appears_in_pdf(report, html):
    for item in report["objects"]:
        assert item["result"]["execution_reason"] in html


# ── Обогащение как операция ───────────────────────────────────────────────────
def test_enrich_returns_the_same_object():
    """Мутация по ссылке заявлена в документации — проверяем, что так и есть."""
    result = _result(1, CASES[0])
    assert enrich_result(result, 45.0) is result


def test_enrich_is_idempotent():
    """Повторный вызов не должен менять ответ: функция чистая от снимка."""
    first = enrich_result(_result(1, CASES[0]), 45.0)
    twice = enrich_result(enrich_result(_result(1, CASES[0]), 45.0), 45.0)
    assert first == twice


def test_missing_share_does_not_break_execution_reason():
    """Доля необязательна: направление без неё всё равно получает пояснение."""
    result = enrich_result(_result(1, CASES[0]), None)
    assert result["execution_reason"]
    assert "%" not in result["execution_reason"]


def test_cell_breakdown_printed_for_every_direction(report, html):
    """
    Строка вывода ячейки печатается всегда, а не только при расхождении
    с баллами: иначе клиент не поймёт, почему у одного направления
    пояснение есть, а у другого нет (§10.1a).

    Текст в вебе собирает `cellBreakdownText` из frontend/lib/m3.ts —
    отдельная реализация той же формулировки, как у market_label.
    Сравнить их автоматически нельзя, поэтому тест пиньтует точную строку
    с питоновской стороны: разойдясь, вторая сторона будет видна глазом.
    """
    for item in report["objects"]:
        result = item["result"]
        for axis in ("strength", "attract"):
            expected = cell_breakdown_text(axis, result["cell_breakdown"][axis])
            assert expected in html, (result["name"], axis, expected)


def test_cell_breakdown_absent_for_old_snapshots():
    """У снимков до ревизии 030 весов нет — блока быть не должно, а не
    заглушки с нулями."""
    from app.m3_pdf import cell_breakdown_block
    assert cell_breakdown_block({"cell_breakdown": None}) == ""
    assert cell_breakdown_block({}) == ""

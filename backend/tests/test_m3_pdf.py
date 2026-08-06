# -*- coding: utf-8 -*-
"""
Метод 3 — сборщик HTML для PDF: шапка и разделы 00–01.

Тесты проверяют строку HTML, а не картинку: Chromium здесь не нужен.
Геометрия карты проверяется отдельно в test_m3_map против эталона веба.

Числа контрольного кейса взяты из образца 64dao-portfolio-report-sample.html
версии 0.2 и из metod-3-pilot-template.xlsx.
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.m3_pdf import (
    banner, data_status_banner, map_section, num, objects_section, page,
    report_header, section_title, signed, signed_percent, table,
)

PORTFOLIO_FLAG_LABELS = {
    "UNIFORM_PORTFOLIO": "все направления в одной ячейке",
    "SELF_INFLATION": "оценки систематически завышены",
    "RANK_MISMATCH": "расчёт расходится с порядком собственника",
}


def _portfolio(title="Портфель ООО «Пример»", calculated=datetime(2026, 8, 2)):
    return SimpleNamespace(title=title, calculated_at=calculated)


def _summary(**over):
    base = {
        "objects": 5, "sum_positions": 18, "sum_positions_max": 30,
        "turbulence": 4, "delta": 0, "distinct_cells": 4, "spearman": 0.60,
        "flags": [], "verdicts_held": False,
    }
    base.update(over)
    return base


def _obj(oid="o1", position=1, name="Салонный канал B2B", revenue=180,
         dynamics=-5, share=45, profitability="profitable"):
    return SimpleNamespace(
        id=oid, position=position, name=name, revenue=revenue,
        revenue_dynamics=dynamics, revenue_share=share,
        profitability=profitability,
    )


def _result(oid="o1", position=1, name="Салонный канал B2B", cs="high", ca="low",
            symbols="AAABBA", current=26, target=None, risk=41,
            target_lines=(), risk_lines=(3,), mobility=None):
    return {
        "object_id": oid, "position": position, "name": name,
        "cell_strength": cs, "cell_attract": ca,
        "cell_label": "Высокая / Низкая",
        "coord_strength": 3.33, "coord_attract": 2.33,
        "symbols": symbols, "current_hex": current,
        "target_hex": target, "risk_hex": risk,
        "target_lines": list(target_lines), "risk_lines": list(risk_lines),
        "mobility": mobility if mobility is not None else {"3": "old_yang"},
    }


# ── Числа ─────────────────────────────────────────────────────────────────────
def test_decimal_separator_is_comma_like_in_sample():
    """Образец печатает 0,619 и 0,60 — запятая, а не точка."""
    assert num(0.619, 3) == "0,619"
    assert num(0.60, 2) == "0,60"
    assert num(18) == "18"


def test_missing_number_shows_dash_not_zero():
    """Незаполненное и ноль — разные вещи; ноль выручки не то же, что «не знаю»."""
    assert num(None) == "—"
    assert num(0) == "0"


def test_dynamics_always_carries_sign():
    """Без знака падение выручки читается как рост."""
    assert signed_percent(-5) == "-5%"
    assert signed_percent(60) == "+60%"
    assert signed_percent(0) == "0%"
    assert signed_percent(None) == "—"


def test_delta_sign_is_explicit():
    assert signed(0) == "0"
    assert signed(3) == "+3"
    assert signed(-2) == "-2"


# ── Шапка ─────────────────────────────────────────────────────────────────────
def test_header_carries_report_name_and_company():
    """
    Заголовок — название отчёта плюс название компании. Правило то же, что
    в Методе 1, и оно не зависит от заполненности других полей.
    """
    html = report_header("ООО «Ромашка»", _portfolio(), _summary())
    assert "Матрица силы · ООО «Ромашка»" in html


def test_header_does_not_repeat_matrix_in_overline():
    """«Матрица силы» стоит один раз — в заголовке, а не ещё и над ним."""
    html = report_header("ООО «Ромашка»", _portfolio(), _summary())
    assert html.count("Матрица силы") == 1
    assert "64DAO · Метод 3<" in html


def test_header_shows_portfolio_title_as_subtitle():
    html = report_header("Компания", _portfolio(title="Портфель 2026"), _summary())
    assert "Портфель 2026" in html


def test_header_falls_back_when_portfolio_unnamed():
    html = report_header("Компания", _portfolio(title=None), _summary())
    assert "Портфель без названия" in html


def test_header_metrics_match_control_case():
    """18 позиций из 30, T = 4, Δ = 0 — числа контрольного кейса."""
    html = report_header("Компания", _portfolio(), _summary())
    assert "Сумма позиций: 18 из 30" in html
    assert "Подвижных линий: 4" in html
    assert "Δ: 0" in html
    assert "Рассчитано 02.08.2026" in html


def test_header_shows_industry_when_known():
    html = report_header("Компания", _portfolio(), _summary(),
                         industry_name="производство FMCG")
    assert "Веса: производство FMCG" in html


def test_header_omits_calculation_date_when_not_calculated():
    html = report_header("Компания", _portfolio(calculated=None), _summary())
    assert "Рассчитано" not in html


def test_header_escapes_company_name():
    html = report_header("<script>alert(1)</script>", _portfolio(), _summary())
    assert "<script>" not in html


# ── Статус данных ─────────────────────────────────────────────────────────────
def test_status_banner_reports_agreement_with_owner_order():
    html = data_status_banner(_summary(), PORTFOLIO_FLAG_LABELS)
    assert "0,60" in html
    assert "Вердикты выданы" in html


def test_status_banner_switches_to_held_verdicts():
    """
    При портфельном флаге вердикты аллокации удерживаются: диагноз есть,
    распределение ресурса — нет. Это разные состояния отчёта.
    """
    html = data_status_banner(
        _summary(verdicts_held=True, flags=["RANK_MISMATCH"]),
        PORTFOLIO_FLAG_LABELS,
    )
    assert "Вердикты аллокации удержаны" in html
    assert "расчёт расходится с порядком собственника" in html
    assert "распределение ресурса — нет" in html


def test_status_banner_omits_spearman_when_absent():
    html = data_status_banner(_summary(spearman=None), PORTFOLIO_FLAG_LABELS)
    assert "Корреляция" not in html


# ── 00 Исходные данные ────────────────────────────────────────────────────────
def test_objects_section_renders_control_case_row():
    html = objects_section([_obj()])
    assert "Салонный канал B2B" in html
    assert "180" in html
    assert "-5%" in html
    assert "45%" in html
    assert "прибыльно" in html


def test_objects_section_hides_market_column_without_data():
    """
    Колонка «Рынок» требует знания, заполнены ли переопределения Р*. Флаг
    скрининга говорит лишь о том, что вопрос задали. Расчёт эти данные
    отдаёт (m3_scoring.market_override_count), но сама сборщица таблицы
    без словаря столбца не рисует: столбец, который врёт, хуже отсутствующего.
    """
    assert "Рынок" not in objects_section([_obj()])


def test_objects_section_shows_market_column_when_supplied():
    html = objects_section([_obj(oid="o2")], {"o2": "базовый, своя линия 5"})
    assert "Рынок" in html
    assert "базовый, своя линия 5" in html


def test_objects_section_handles_unknown_numbers():
    html = objects_section([_obj(revenue=None, dynamics=None, share=None,
                                 profitability="unknown")])
    assert "не указана" in html
    assert html.count("—") >= 3


def test_objects_section_escapes_direction_name():
    html = objects_section([_obj(name="<b>Канал</b>")])
    assert "<b>Канал</b>" not in html
    assert "&lt;b&gt;" in html


# ── 01 Карта портфеля ─────────────────────────────────────────────────────────
def test_map_section_contains_svg_and_table():
    html = map_section([_result()], {"o1": 45}, _summary())
    assert "<svg" in html
    assert "AAABBA" in html, "код гексаграммы в таблице под картой"
    assert "Высокая конкурентоспособность бизнеса / Низкая привлекательность рынка" in html


def test_map_section_marks_absent_target_and_risk():
    """
    Прочерк в колонке цели означает «старых Инь нет», а не «данных нет».
    Направления 3 и 4 образца не имеют ни цели, ни риска.
    """
    html = map_section(
        [_result(target=None, risk=None, target_lines=(), risk_lines=(), mobility={})],
        {"o1": 12}, _summary(),
    )
    assert html.count("—") >= 2


def test_map_section_counts_moving_lines_from_mobility():
    html = map_section(
        [_result(mobility={"3": "old_yin", "4": "old_yang"})],
        {"o1": 30}, _summary(),
    )
    assert ">2</td>" in html


def test_map_section_reports_distinct_cells():
    html = map_section([_result()], {"o1": 45}, _summary())
    assert "4 из 9" in html


def test_map_section_survives_missing_share():
    html = map_section([_result()], {}, _summary())
    assert "<circle" in html


# ── Каркас ────────────────────────────────────────────────────────────────────
def test_first_page_has_no_page_break_before_it():
    """Разрыв перед первым листом дал бы пустую страницу в начале документа."""
    assert "page-break-before" not in page("<p></p>", "Компания", "стр. 1", first=True)
    assert "page-break-before" in page("<p></p>", "Компания", "стр. 2")


def test_page_shows_company_and_note_in_running_head():
    html = page("<p></p>", "ООО «Ромашка»", "карта портфеля", first=True)
    assert "ООО «Ромашка»" in html
    assert "карта портфеля" in html
    assert "Конфиденциально" in html


def test_table_aligns_numeric_columns_right():
    html = table([("Направление", False), ("Доля", True)], [["Канал", "45%"]])
    assert "text-align:right" in html
    assert "text-align:left" in html


def test_section_title_carries_number_in_accent():
    html = section_title("01", "Карта портфеля")
    assert ">01</span>" in html
    assert "Карта портфеля" in html


def test_banner_variants_differ_by_border_colour():
    assert banner("Заголовок", "текст", warn=True) != banner("Заголовок", "текст")


def test_no_react_only_attributes_leak_into_html():
    """Playwright печатает обычный HTML; camelCase-атрибуты React ему чужие."""
    html = (report_header("Компания", _portfolio(), _summary())
            + objects_section([_obj()])
            + map_section([_result()], {"o1": 45}, _summary()))
    for attribute in ("className", "strokeWidth", "textAnchor", "borderCollapse"):
        assert attribute not in html


# ── 02 Разбор направлений ─────────────────────────────────────────────────────
from types import SimpleNamespace as _NS  # noqa: E402

from app.m3_pdf import (  # noqa: E402
    hexagram_line, line_glyph, lines_block, object_card, route_block,
    verdict_block,
)
from app.m3_verdict import verdict_for  # noqa: E402


def _full_result(**over):
    base = {
        "object_id": "o5", "position": 5, "name": "Обучение мастеров",
        "cell_strength": "low", "cell_attract": "high",
        "cell_label": "Низкая / Высокая",
        "coord_strength": 2.0, "coord_attract": 3.0,
        "symbols": "BABAAA", "current_hex": 6, "current_name": "Шесть",
        "target_hex": 10, "target_lines": [1], "risk_hex": None, "risk_lines": [],
        "mobility": {"1": "old_yin"},
        "scores": {"l1": 1.0, "l2": 3.0, "l3": 2.0, "l4": 3.0, "l5": 2.67, "l6": 3.33},
        "v_index": 0.619, "z_index": 0.030, "v_rank": 1, "z_rank": 5,
        "weak_line": 1, "strong_line": 6, "tensions": ["P1", "P3"], "flags": [],
    }
    base.update(over)
    return base


def _step(text="Пересчитать юнит-экономику курса", line=1, kind="route", budget=True):
    return _NS(step_text=text, line=line, step_type=kind, needs_budget=budget)


NARRATIVE = [
    {"kind": "zone", "key": "low_high", "title": "Суть ситуации",
     "body": "Внешний контур сильный во всех трёх слоях.",
     "mistake": "Наращивать объём на неподтверждённой экономике."},
    {"kind": "weak_line", "key": "weak_L1", "title": "Ведущая слабость",
     "body": "Ресурсная база не построена.", "mistake": None},
    {"kind": "tension", "key": "P1", "title": "Напряжение P1",
     "body": "Продукт лучше, чем способность его продать.", "mistake": None},
    {"kind": "tension", "key": "P3", "title": "Напряжение P3",
     "body": "Спрос есть, экономика его не выдерживает.", "mistake": None},
]


def test_lines_render_top_down_from_six():
    """Л6 первой, как в гексаграмме: снизу вверх читается только сама фигура."""
    html = lines_block(_full_result())
    assert html.index("Л6") < html.index("Л1")


def test_moving_line_is_marked_red_and_named():
    html = lines_block(_full_result())
    assert "Старый Инь · подвижная" in html
    assert "#c0392b" in html


def test_static_lines_named_by_symbol():
    html = lines_block(_full_result())
    assert "Ян" in html and "Инь" in html


def test_line_scores_use_two_decimals_with_comma():
    html = lines_block(_full_result())
    assert "1,00" in html and "2,67" in html


def test_yin_glyph_is_broken_and_yang_is_solid():
    assert line_glyph(True, False).count("<span") == 1
    assert line_glyph(False, False).count("<span") == 3


def test_hexagram_line_shows_only_existing_vectors():
    only_target = hexagram_line(_full_result())
    assert "цель № 10" in only_target
    assert "риск" not in only_target

    both = hexagram_line(_full_result(risk_hex=4, risk_lines=[4]))
    assert "цель № 10" in both and "риск № 4" in both


def test_hexagram_line_states_stability_when_nothing_moves():
    html = hexagram_line(_full_result(target_hex=None, target_lines=[],
                                      risk_hex=None, risk_lines=[]))
    assert "ограничение стабильно" in html


def test_route_uses_checklist_steps_not_a_second_copy():
    html = route_block([_step()], _full_result())
    assert "Пересчитать юнит-экономику курса" in html
    assert "Шаг маршрута · линия 1" in html
    assert "требует бюджета" in html


def test_route_states_target_transition_with_zone_move():
    """
    Образец: «Целевое состояние: № 6 → № 10, конкурентная сила переходит из
    низкой в среднюю». Ячейка целевой гексаграммы считается точно — её
    задаёт число Ян в триграмме, а символы получаются инверсией старых Инь.
    """
    html = route_block([_step()], _full_result())
    assert "№ 6 → № 10" in html
    assert "конкурентная сила переходит из низкой в среднюю" in html


def test_route_states_erosion_transition_separately():
    result = _full_result(symbols="BABABA", current_hex=64, target_hex=50,
                          target_lines=[3], risk_hex=4, risk_lines=[4],
                          mobility={"3": "old_yin", "4": "old_yang"})
    html = route_block([_step(line=3), _step(line=4, kind="hold", budget=False)],
                       result)
    assert "Целевое состояние: № 64 → № 50" in html
    assert "Сценарий эрозии без закрепления: № 64 → № 4" in html
    assert "привлекательность рынка падает со средней до низкой" in html


def test_route_omits_zone_phrase_when_zone_does_not_move():
    """
    Инверсия всегда меняет число Ян в триграмме на единицу, но ячейку — не
    всегда: 0 и 1 Ян обе дают «низкую». Значит проработка назревшей слабости
    в совсем слабой триграмме зону не сдвигает, и фраза о переходе была бы
    неправдой. Печатается только номер.
    """
    result = _full_result(symbols="BBBAAA", current_hex=12, target_hex=45,
                          target_lines=[1], mobility={"1": "old_yin"})
    html = route_block([_step(line=1)], result)
    assert "№ 12 → № 45" in html
    assert "переходит" not in html and "падает" not in html


def test_route_says_so_when_there_is_none():
    html = route_block([], _full_result(target_hex=None, target_lines=[]))
    assert "маршрут не строится" in html
    assert "ограничение стабильно" in html


def test_verdict_block_carries_zone_and_english_name():
    html = verdict_block(verdict_for(_full_result()))
    assert "Инвестировать точечно" in html
    assert "Избирательно развивать" in html
    assert "Selectively Build" in html


def test_card_groups_tensions_under_one_heading():
    html = object_card(_full_result(), NARRATIVE, _obj(oid="o5"), [_step()],
                       verdict_for(_full_result()))
    assert html.count("Напряжения") == 1
    assert "P1" in html and "P3" in html
    assert "Напряжение P1" not in html, "заголовок каждого напряжения не нужен"


def test_card_shows_mistake_as_banner_once():
    html = object_card(_full_result(), NARRATIVE, _obj(oid="o5"), [_step()],
                       verdict_for(_full_result()))
    assert html.count("Типичная ошибка") == 1


def test_card_facts_line_matches_sample():
    html = object_card(_full_result(), NARRATIVE,
                       _obj(oid="o5", revenue=20, dynamics=40, share=5),
                       [_step()], verdict_for(_full_result()))
    assert "Низкая конкурентоспособность бизнеса" in html
    assert "Высокая привлекательность рынка" in html
    assert "20 млн ₽" in html
    assert "+40% за год" in html
    assert "5% выручки" in html
    assert "V = 0,619 (ранг 1)" in html
    assert "Z = 0,030 (ранг 5)" in html


def test_card_shows_direction_flags_when_present():
    result = _full_result(flags=["SCALE_CONTRADICTION"])
    html = object_card(result, NARRATIVE, _obj(oid="o5"), [_step()],
                       verdict_for(result))
    assert "крупная доля выручки при слабом канале" in html


def test_card_omits_flag_banner_when_clean():
    html = object_card(_full_result(), NARRATIVE, _obj(oid="o5"), [_step()],
                       verdict_for(_full_result()))
    assert "Оговорки по данным направления" not in html


def test_card_escapes_narrative_text():
    poisoned = [{"kind": "zone", "key": "z", "title": "Суть",
                 "body": "<script>alert(1)</script>", "mistake": None}]
    html = object_card(_full_result(), poisoned, _obj(oid="o5"), [],
                       verdict_for(_full_result()))
    assert "<script>" not in html


def test_card_avoids_page_break_inside():
    html = object_card(_full_result(), NARRATIVE, _obj(oid="o5"), [_step()],
                       verdict_for(_full_result()))
    assert "page-break-inside:avoid" in html


# ── 03 Портфельные ограничения ────────────────────────────────────────────────
from app.m3_pdf import constraints_section  # noqa: E402

CONTROL_RESULTS = [
    {"name": "Салонный канал B2B", "symbols": "AAABBA",
     "mobility": {"3": "old_yang"}, "target_lines": [], "risk_lines": [3]},
    {"name": "Маркетплейсы", "symbols": "BABABA",
     "mobility": {"3": "old_yin", "4": "old_yang"},
     "target_lines": [3], "risk_lines": [4]},
    {"name": "Интернет-магазин", "symbols": "ABBABA",
     "mobility": {}, "target_lines": [], "risk_lines": []},
    {"name": "Контрактное производство", "symbols": "ABAABA",
     "mobility": {}, "target_lines": [], "risk_lines": []},
    {"name": "Обучение мастеров", "symbols": "BABAAA",
     "mobility": {"1": "old_yin"}, "target_lines": [1], "risk_lines": []},
]


def test_constraints_section_names_two_constraints():
    html = constraints_section(CONTROL_RESULTS, _summary())
    assert "Ограничение 1 · структурное" in html
    assert "Ограничение 2 · компетенция" in html


def test_constraints_section_shows_yin_table_header_with_total():
    html = constraints_section(CONTROL_RESULTS, _summary())
    assert "Инь из 5" in html
    assert "Дельта линии" in html


def test_constraints_section_lists_lines_by_frequency():
    html = constraints_section(CONTROL_RESULTS, _summary())
    assert html.index("Структура рынка, маржа") < html.index("Каналы и доля")
    assert html.index("Каналы и доля") < html.index("Макро и регулирование")


def test_constraints_section_carries_metric_readings():
    html = constraints_section(CONTROL_RESULTS, _summary())
    assert "18 / 30" in html
    assert "Дельта портфеля Δ" in html
    assert "Портфель чуть выше середины" in html
    assert "Умеренная энергия перехода" in html


def test_constraints_section_states_tact_rule():
    html = constraints_section(CONTROL_RESULTS, _summary())
    assert "не более двух направлений" in html
    assert "управленческий ресурс" in html


def test_constraints_section_says_so_when_nothing_repeats():
    """
    Отсутствие общего ограничения — содержательный вывод, а не пустой блок:
    он означает, что работать нужно по направлениям.
    """
    strong = [dict(r, symbols="AAAAAA", mobility={}) for r in CONTROL_RESULTS]
    html = constraints_section(strong, _summary())
    assert "общего ограничения компании расчёт не фиксирует" in html
    assert "Ограничение 1" not in html


def test_constraints_section_escapes_direction_names():
    poisoned = [dict(r) for r in CONTROL_RESULTS]
    poisoned[0]["name"] = "<script>alert(1)</script>"
    poisoned[0]["symbols"] = "AAAAAA"
    for r in poisoned[1:]:
        r["symbols"] = "BAAAAA"
    html = constraints_section(poisoned, _summary())
    assert "<script>" not in html


# ── 04 Решение о распределении ────────────────────────────────────────────────
from app.m3_pdf import checklist_table, decision_section  # noqa: E402


def _res(oid, position, name, cs, ca, v, z, vr, zr, target=(), risk=()):
    return {
        "object_id": oid, "position": position, "name": name,
        "cell_strength": cs, "cell_attract": ca, "cell_label": "—",
        "v_index": v, "z_index": z, "v_rank": vr, "z_rank": zr,
        "target_lines": list(target), "risk_lines": list(risk),
    }


CONTROL_BY_ID = {
    "o5": _res("o5", 5, "Обучение мастеров", "low", "high", 0.619, 0.030, 1, 5, (1,)),
    "o2": _res("o2", 2, "Маркетплейсы", "low", "mid", 0.547, 0.380, 2, 2, (3,), (4,)),
    "o4": _res("o4", 4, "Контрактное производство", "mid", "mid", 0.535, 0.072, 3, 3),
    "o3": _res("o3", 3, "Интернет-магазин", "low", "mid", 0.508, 0.048, 4, 4),
    "o1": _res("o1", 1, "Салонный канал B2B", "high", "low", 0.491, 0.470, 5, 1, (), (3,)),
}
INVEST_ORDER = ["o5", "o2", "o4", "o3", "o1"]
EXEC_ORDER = ["o1", "o2", "o4", "o3", "o5"]
OBJECTS_BY_ID = {
    "o1": _obj("o1", 1, "Салонный канал B2B", 180, -5, 45),
    "o2": _obj("o2", 2, "Маркетплейсы", 120, 60, 30),
    "o3": _obj("o3", 3, "Интернет-магазин", 32, 10, 8),
    "o4": _obj("o4", 4, "Контрактное производство", 48, 15, 12),
    "o5": _obj("o5", 5, "Обучение мастеров", 20, 40, 5),
}


def _cl_step(oid="o1", text="Описать процесс", line=3, kind="hold",
             wave=1, budget=False, done=False):
    return SimpleNamespace(object_id=oid, step_text=text, line=line,
                           step_type=kind, wave=wave, needs_budget=budget, done=done)


def _decision(option="method", waves=None, cost="Обучение ждёт полгода.",
              triggers=("Закрытие маршрута направления 2",)):
    return SimpleNamespace(
        accepted_option=option,
        waves=waves if waves is not None else {"1": ["o1", "o2"], "2": ["o5"]},
        cost_accepted=cost, review_triggers=list(triggers),
        decided_at=datetime(2026, 8, 2),
    )


def _section(**over):
    kwargs = dict(
        results_by_id=CONTROL_BY_ID, objects_by_id=OBJECTS_BY_ID,
        investment_order=INVEST_ORDER, execution_order=EXEC_ORDER,
        steps=[_cl_step()], decision=_decision(),
        generated_at=datetime(2026, 8, 3, 14, 30),
    )
    kwargs.update(over)
    return decision_section(**kwargs)


def test_both_orders_are_printed_with_indices():
    html = _section()
    assert "0,619" in html and "0,470" in html


def test_investment_table_carries_verdicts():
    html = _section()
    assert "Инвестировать точечно" in html
    assert "Не инвестировать в рост. Закрепить" in html


def test_execution_table_explains_each_position():
    html = _section()
    assert "цена ошибки максимальна" in html
    assert "отложить можно без потерь" in html


def test_cash_cow_divergence_is_named():
    """
    Последнее по V и первое по Z — денежная корова. Единый показатель это
    различие уничтожил бы, поэтому оно вынесено в отдельный баннер.
    """
    html = _section()
    assert "Ключевой trade-off" in html
    assert "денежная корова" in html
    assert "Салонный канал B2B" in html


def test_no_tradeoff_banner_when_orders_agree():
    same = ["o5", "o2", "o4", "o3", "o1"]
    html = _section(investment_order=same, execution_order=same)
    assert "Ключевой trade-off" not in html


def test_accepted_decision_lists_waves():
    html = _section()
    assert "Принята рекомендация метода" in html
    assert "решение от 02.08.2026" in html
    assert "волна 1" in html and "волна 2" in html


def test_custom_option_is_named_differently():
    html = _section(decision=_decision(option="custom"))
    assert "Принят собственный порядок" in html


def test_cost_of_decision_is_printed_with_its_consequence():
    html = _section()
    assert "Обучение ждёт полгода" in html
    assert "теряет энергию перехода" in html


def test_review_triggers_are_listed():
    html = _section()
    assert "Условия пересмотра решения" in html
    assert "Закрытие маршрута направления 2" in html
    assert "продолжать по инерции" in html


def test_missing_decision_is_flagged_not_hidden():
    """
    Без записанного решения повторная диагностика истолкует неизменившееся
    направление как невыполнение рекомендаций. Молчать об этом нельзя.
    """
    html = _section(decision=None)
    assert "Решение по волнам не зафиксировано" in html
    assert "невыполнение рекомендаций" in html


def test_held_verdicts_add_a_warning_to_the_lists():
    html = _section(verdicts_held=True)
    assert "Вердикты удержаны" in html
    assert "не как рекомендация" in html


# ── Чек-лист ──────────────────────────────────────────────────────────────────
def test_checklist_groups_steps_by_wave():
    html = checklist_table(
        [_cl_step(wave=1), _cl_step(oid="o5", text="Пересчитать", line=1,
                                    kind="route", wave=2, budget=True)],
        OBJECTS_BY_ID, None,
    )
    assert "Волна 1" in html and "Волна 2" in html
    assert html.index("Волна 1") < html.index("Волна 2")


def test_decision_step_goes_outside_the_route():
    """
    Шаг типа «решение» не меняет ни одной линии и в правиле такта не
    участвует, поэтому стоит отдельной группой.
    """
    html = checklist_table(
        [_cl_step(), _cl_step(oid="o3", text="Стратегическая сессия", line=None,
                              kind="decision")],
        OBJECTS_BY_ID, None,
    )
    assert "Вне маршрута" in html
    assert html.index("Волна 1") < html.index("Вне маршрута")


def test_done_steps_are_struck_through():
    html = checklist_table([_cl_step(done=True)], OBJECTS_BY_ID, None)
    assert "☑" in html
    assert "line-through" in html


def test_pending_steps_show_empty_box():
    html = checklist_table([_cl_step(done=False)], OBJECTS_BY_ID, None)
    assert "☐" in html
    assert "line-through" not in html


def test_checklist_stamps_the_moment_of_generation():
    """
    Отметки меняются после скачивания. Без времени формирования распечатанный
    файл выглядит как вечная истина.
    """
    html = checklist_table([_cl_step()], OBJECTS_BY_ID, datetime(2026, 8, 3, 14, 30))
    assert "03.08.2026 14:30" in html
    assert "личном кабинете" in html


def test_checklist_marks_budget_requirement():
    html = checklist_table([_cl_step(budget=True)], OBJECTS_BY_ID, None)
    assert ">да</td>" in html


def test_empty_checklist_says_so():
    html = checklist_table([], OBJECTS_BY_ID, None)
    assert "Чек-лист пуст" in html


def test_checklist_escapes_step_text():
    html = checklist_table([_cl_step(text="<script>alert(1)</script>")],
                           OBJECTS_BY_ID, None)
    assert "<script>" not in html


# ── Оговорки и сборка документа ───────────────────────────────────────────────
from app.m3_pdf import (  # noqa: E402
    build_portfolio_report_html, disclaimers_section, flag_location,
)
from app.m3_pdf import FLAG_LABELS, PORTFOLIO_FLAG_LABELS as PFL  # noqa: E402


def _scored(**over):
    base = dict(_result())
    base["scores"] = {"l1": 3.0, "l2": 3.0, "l3": 4.0, "l4": 2.0, "l5": 2.0, "l6": 3.0}
    base["flags"] = []
    base.update(over)
    return base


def test_flag_location_names_direction_and_line():
    """
    «Направление 4, линия 3 (2,67)» проверяемо, «Направление 4» — нет.
    Линия восстанавливается по баллу и порогу: в снимке хранится факт
    срабатывания, но не место.
    """
    result = _scored(scores={"l1": 3.0, "l2": 2.67, "l3": 4.0,
                             "l4": 2.0, "l5": 2.0, "l6": 3.0})
    where = flag_location(result, "BORDERLINE_LINE")
    assert "линия 2 (2,67)" in where
    assert "Салонный канал B2B" in where


def test_flag_location_falls_back_to_direction_for_object_wide_flags():
    where = flag_location(_scored(), "SCALE_CONTRADICTION")
    assert where == "1 · Салонный канал B2B"


def test_flag_location_uses_config_thresholds_when_given():
    result = _scored(scores={"l1": 3.0, "l2": 3.0, "l3": 3.9,
                             "l4": 2.0, "l5": 2.0, "l6": 3.0})
    assert "линия 3" not in flag_location(result, "NEAR_OLD_YANG")
    wide = flag_location(result, "NEAR_OLD_YANG", {"near_old_yang": [3.80, 3.95]})
    assert "линия 3 (3,90)" in wide


def test_disclaimers_table_carries_portfolio_and_object_flags():
    html = disclaimers_section(
        [{"result": _scored(flags=["SCALE_CONTRADICTION"])}],
        _summary(flags=["RANK_MISMATCH"]),
        ["Отраслевые веса — экспертные оценки."],
        FLAG_LABELS, PFL,
    )
    assert "RANK_MISMATCH" in html and "Портфель целиком" in html
    assert "SCALE_CONTRADICTION" in html
    assert "Отраслевые веса" in html


def test_disclaimers_section_says_so_when_clean():
    html = disclaimers_section([{"result": _scored()}], _summary(), [],
                               FLAG_LABELS, PFL)
    assert "без замечаний" in html


def test_disclaimers_always_state_the_limits_of_self_assessment():
    html = disclaimers_section([{"result": _scored()}], _summary(), [],
                               FLAG_LABELS, PFL)
    assert "не заменяет финансовый анализ" in html
    assert "одного респондента" in html


# ── Документ целиком ──────────────────────────────────────────────────────────
def _full_report():
    objects = [
        SimpleNamespace(id="o1", position=1, name="Салонный канал B2B",
                        revenue=180, revenue_dynamics=-5, revenue_share=45,
                        profitability="profitable"),
        SimpleNamespace(id="o2", position=2, name="Маркетплейсы",
                        revenue=120, revenue_dynamics=60, revenue_share=30,
                        profitability="marginal"),
        SimpleNamespace(id="o5", position=5, name="Обучение мастеров",
                        revenue=20, revenue_dynamics=40, revenue_share=5,
                        profitability="marginal"),
    ]
    portfolio = SimpleNamespace(title="Портфель пилота",
                                calculated_at=datetime(2026, 8, 2), objects=objects)
    def res(oid, pos, name, cs, ca, sym, cur, v, z, vr, zr, t=(), r=(), mob=None):
        return {"object_id": oid, "position": pos, "name": name,
                "cell_strength": cs, "cell_attract": ca, "cell_label": "—",
                "coord_strength": 2.5, "coord_attract": 2.5, "symbols": sym,
                "current_hex": cur, "current_name": "—",
                "target_hex": 10 if t else None, "risk_hex": 41 if r else None,
                "target_lines": list(t), "risk_lines": list(r),
                "mobility": mob or {}, "flags": [],
                "scores": {f"l{i}": 2.5 for i in range(1, 7)},
                "v_index": v, "z_index": z, "v_rank": vr, "z_rank": zr}
    return {
        "portfolio": portfolio,
        "summary": _summary(objects=3, sum_positions=11, sum_positions_max=18),
        "objects": [
            {"result": res("o5", 5, "Обучение мастеров", "low", "high", "BABAAA",
                           6, 0.619, 0.030, 1, 3, t=(1,), mob={"1": "old_yin"}),
             "narrative": [{"kind": "zone", "key": "low_high", "title": "Суть",
                            "body": "Текст", "mistake": "Ошибка"}]},
            {"result": res("o2", 2, "Маркетплейсы", "low", "mid", "BABABA",
                           64, 0.547, 0.380, 2, 2, t=(3,), r=(4,),
                           mob={"3": "old_yin", "4": "old_yang"}),
             "narrative": []},
            {"result": res("o1", 1, "Салонный канал B2B", "high", "low", "AAABBA",
                           26, 0.491, 0.470, 3, 1, r=(3,), mob={"3": "old_yang"}),
             "narrative": []},
        ],
        "investment_order": ["o5", "o2", "o1"],
        "execution_order": ["o1", "o2", "o5"],
        "disclaimers": ["Номер гексаграммы — идентификатор конфигурации."],
    }


def _document(**over):
    kwargs = dict(report=_full_report(), steps=[], decision=None,
                  company_name="ООО «Пример»", generated_at=datetime(2026, 8, 3, 14, 30))
    kwargs.update(over)
    return build_portfolio_report_html(**kwargs)


def test_document_is_valid_standalone_html():
    html = _document()
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert 'lang="ru"' in html and 'charset="UTF-8"' in html


def test_document_starts_with_the_header_not_a_cover():
    """Титульной страницы у Метода 3 нет — документ начинается шапкой."""
    html = _document()
    assert html.index("Матрица силы · ООО «Пример»") < html.index("Исходные данные")


def test_document_keeps_the_sample_section_order():
    html = _document()
    order = ["Исходные данные", "Карта портфеля", "Разбор направлений",
             "Портфельные ограничения", "Решение о распределении", "Оговорки по данным"]
    positions = [html.index(s) for s in order]
    assert positions == sorted(positions), "порядок разделов разошёлся с образцом"


def test_each_direction_gets_its_own_sheet():
    """Направление начинается с нового листа: три направления — три разрыва."""
    html = _document()
    assert html.count("· направление ") == 3, "в колонтитуле по разу на направление"


def test_section_title_is_printed_once_not_on_every_sheet():
    """
    Пять повторов заголовка съедали по трети листа и ничего не сообщали:
    номер направления и так стоит в колонтитуле каждого листа.
    """
    html = _document()
    assert html.count("Разбор направлений") == 1


def test_direction_card_does_not_forbid_breaking_inside_itself():
    """
    Карточка выше листа. Запрет разрыва заставлял браузер переносить её
    целиком — первый лист оставался пустым, а карточка всё равно ломалась.
    Разрыв запрещён только неделимым кускам внутри.
    """
    html = object_card(_full_result(), NARRATIVE, _obj(oid="o5"), [_step()],
                       verdict_for(_full_result()))
    section = html[:html.index(">")]
    assert "page-break-inside" not in section
    assert "page-break-inside:avoid" in html, "внутренние блоки защищены"


def test_first_sheet_has_no_page_break_before_it():
    html = _document()
    assert html.index("page-break-before") > html.index("Матрица силы")


def test_document_prints_map_once():
    html = _document()
    assert html.count("<svg") == 1


def test_document_carries_generation_stamp_only_with_checklist():
    without = _document()
    assert "Чек-лист пуст" in without

    step = SimpleNamespace(object_id="o1", step_text="Шаг", line=3,
                           step_type="hold", wave=1, needs_budget=False, done=False)
    with_steps = _document(steps=[step])
    assert "03.08.2026 14:30" in with_steps


def test_document_survives_portfolio_without_industry():
    assert "Веса:" not in _document()
    assert "Веса: Производство" in _document(industry_name="Производство")


def test_document_escapes_company_name_everywhere():
    html = _document(company_name="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in html


# ── Колонка «Рынок» ───────────────────────────────────────────────────────────
from app.m3_pdf import market_label  # noqa: E402


def test_market_label_wording():
    """Формулировка одна на веб и PDF: расхождение читатель заметит сразу."""
    assert market_label(0) == "Общий"
    assert market_label(3) == "Свой (3 из 6)"
    assert market_label(6) == "Свой (6 из 6)"


def test_market_label_treats_zero_and_negative_as_common():
    """Отрицательного числа быть не может, но подпись не должна ломаться."""
    assert market_label(-1) == "Общий"


def test_objects_section_prints_market_labels_when_given():
    """Колонка появляется только с данными — решение не отменялось."""
    obj = _obj()
    html = objects_section([obj], {str(obj.id): market_label(3)})
    assert "Рынок" in html
    assert "Свой (3 из 6)" in html

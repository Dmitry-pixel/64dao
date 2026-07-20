# -*- coding: utf-8 -*-
"""
Этап 5: рендер PDF-раздела «Финансовая функция».
Проверяем сборку HTML (без Playwright/браузера и без БД) на контрольном кейсе §5.8
и регресс legacy (finance_result отсутствует → раздел не выводится, ошибок нет).
"""
from types import SimpleNamespace
from app.pdf import build_report_html
from app.finance_scoring import compute_finance_result
from app.finance_interpret import build_interpretation


def control_answers() -> dict:
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    return a


def control_content() -> dict:
    return {
        "tonality": {"transitional": {"title": "Переходное состояние", "text": "Язык приоритизации."}},
        "quadrant": {"power_no_direction": {"title": "Сила без направления", "text": "Двигатель есть, руля нет."}},
        "trigram": {"AAA_lower": {"title": "Цянь", "text": "Двигатель на пике."},
                    "ABB_upper": {"title": "Чжэнь", "text": "Поддержка без направления."}},
        "tension_rule": {"R1": {"text": "Поддержка без стратегии."},
                         "R6": {"text": "Трансформация в турбулентной среде."},
                         "R8": {"text": "Рутина без развития."}},
        "action_package": {"line6_yin": {"title": "6. Стратегия", "text": "Стратегическая сессия, целевая модель, KPI."}},
        "fin_pattern": {
            "AAAABB": {"essence": "Ресурс превышает ясность его применения.", "mistake": "Активность ради активности."},
            "AAAABA": {"essence": "Ресурс на службе ясной цели.", "mistake": "Прекращение инвестиций на фоне успеха."},
        },
    }


def fake_finance_strategy():
    return SimpleNamespace(
        combination="AAAABB",
        stratagema_title="ФИН-стратагема",
        title="ФИН заголовок гексаграммы",
        lifecycle_stage="Расцвет-ФИН",
        scenario_text="ФИН сценарий развития — уникальный текст.",
        marketing_text="ФИН маркетинг — уникальный текст.",
        management_text="ФИН управление — уникальный текст.",
        assm_planning="ФИН планирование — предположение.",
    )


def _render_control() -> str:
    result = compute_finance_result(control_answers())
    interp = build_interpretation(result, control_content())
    return build_report_html(
        company_name="Компания X", user_name="CFO", date_str="16 июля 2026",
        combination="AAAABB", strategy=None, method2_data=None,
        finance_result=result, finance_interpretation=interp,
        finance_strategy=fake_finance_strategy(),
    )


def test_finance_section_present_and_complete():
    html = _render_control()
    assert "Финансовая функция" in html
    assert "№ 34" in html and "Сила" in html
    for h in ("Диагноз", "Профиль линий", "Ресурс и направление", "Ключевые напряжения",
              "Приоритеты вмешательства", "Траектория", "Оговорки по данным", "Следующие шаги"):
        assert h in html, f"нет подраздела: {h}"
    assert "Переходное состояние" in html
    assert "Ресурс превышает ясность его применения." in html
    assert "Поддержка без стратегии." in html
    assert "Трансформация в турбулентной среде." in html
    assert "Рутина без развития." in html
    assert "3.25" in html and "1.00" in html
    assert "Сила без направления" in html and "Цянь" in html and "Чжэнь" in html
    assert "Стратегическая сессия, целевая модель, KPI." in html
    assert "№ 14" in html
    assert "Прекращение инвестиций на фоне успеха." in html
    assert "противоречив" in html
    assert "Ответы диагностики" in html
    assert "Где сейчас фокус усилий компании?" in html
    assert "Рост выручки и объёма продаж" in html
    fin_idx = html.index("Финансовая функция")
    assert html.index("ФИН сценарий развития — уникальный текст.") > fin_idx
    assert html.index("ФИН маркетинг — уникальный текст.") > fin_idx
    assert "Расцвет-ФИН" in html and html.index("Расцвет-ФИН") > fin_idx
    assert "Сценарий развития" not in html[:fin_idx]


def test_legacy_without_finance_no_section_no_error():
    html = build_report_html(
        company_name="Old Co", user_name="", date_str="01 января 2025",
        combination="AAAABB", strategy=None, method2_data=None,
    )
    assert "Финансовая функция" not in html
    assert "<!DOCTYPE html>" in html


def test_method2_ignores_finance_section():
    result = compute_finance_result(control_answers())
    interp = build_interpretation(result, control_content())
    html = build_report_html(
        company_name="Co", user_name="", date_str="d",
        combination="AAAAAA", strategy=None, method2_data={},
        finance_result=result, finance_interpretation=interp,
    )
    assert "Финансовая функция" not in html


def test_no_moving_lines_stable_config_text():
    flat = {i: 3 for b in range(1, 7) for i in [f"{b}.{p}" for p in range(1, 5)]}
    result = compute_finance_result(flat)
    interp = build_interpretation(result, control_content())
    html = build_report_html(
        company_name="Co", user_name="", date_str="d",
        combination=result["combination_current"], strategy=None, method2_data=None,
        finance_result=result, finance_interpretation=interp,
    )
    assert "Финансовая функция" in html
    assert "конфигурация стабильна" in html

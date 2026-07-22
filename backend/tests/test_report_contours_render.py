# -*- coding: utf-8 -*-
"""
Этап 5 — фикстурный рендер полного 4-контурного отчёта.

Проверяет сборку HTML отчёта Метода 1 со всеми четырьмя контурами
(finance + product + process + market) и сводной картой: состав и порядок
разделов, что каждая контурная секция использует СВОИ названия линий (а не
финансовые), что сводная карта содержит все контуры и её вердикт согласован
с build_summary, и что разрывы страниц расставлены на каждой секции.

Чистый рендер: без Playwright-браузера и без БД. Повторяет сборку
`load_report_contours` (section_no 05/06/07, порядок CONTOUR_ORDER), но собирает
вход руками, чтобы не поднимать асинхронную сессию.
"""
from app.pdf import build_report_html
from app.finance_scoring import compute_finance_result
from app.contour_scoring import compute_contour_result
from app.finance_interpret import build_interpretation
from app.contours import get_spec, CONTOUR_ORDER, CONTOURS
from app.contour_summary import build_summary


# ── Вход ──────────────────────────────────────────────────────────────────────

def _finance_control_answers() -> dict:
    """Контрольный кейс §5.8: индекс зрелости 4, комбинация AAAABB → №34."""
    a = {}
    for b, raws in {1: [3, 4, 2, 3], 2: [3, 3, 1, 3], 3: [3, 2, 1, 3],
                    4: [4, 3, 3, 2], 5: [2, 2, 4, 2], 6: [1, 1, 4, 1]}.items():
        for p, v in enumerate(raws, 1):
            a[f"{b}.{p}"] = v
    return a


def _uniform_answers(spec, value: int) -> dict:
    """Все пункты контура заполнены одним баллом (реверс учитывает скоринг)."""
    return {it["item_id"]: value for it in spec.items}


def _build_inputs():
    """Возвращает (finance_result, extra_contours, summary) как в
    load_report_contours, но без БД. Контент пустой — рендер каркаса от него
    не зависит (build_interpretation подставляет заглушки)."""
    finance_result = compute_finance_result(_finance_control_answers())

    # Разные заполнения → разная зрелость, чтобы сводная карта выбирала
    # ограничение не вслепую. Конкретные баллы: product сильнее, process слабее.
    fills = {"product": 4, "process": 2, "market": 3}

    extra = []
    all_results = {"finance": finance_result}
    no = 5
    for key in CONTOUR_ORDER:
        if key == "finance":
            continue
        spec = get_spec(key)
        result = compute_contour_result(_uniform_answers(spec, fills[key]), spec)
        all_results[key] = result
        extra.append({
            "contour": key,
            "title": spec.title,
            "result": result,
            "combination": result["combination_current"],
            "interp": build_interpretation(result, {}, spec.blocks),
            "section_no": f"{no:02d}",
        })
        no += 1

    summary = build_summary(all_results)
    return finance_result, extra, summary


def _render_full() -> str:
    finance_result, extra, summary = _build_inputs()
    finance_interp = build_interpretation(finance_result, {})
    return build_report_html(
        company_name="Компания X", user_name="CEO", date_str="22 июля 2026",
        combination="AAAABB", strategy=None, method2_data=None,
        finance_result=finance_result, finance_interpretation=finance_interp,
        finance_strategy=None,
        extra_contours=extra, summary=summary,
    )


# ── Тесты ─────────────────────────────────────────────────────────────────────

CONTOUR_TITLES = ("Финансовая функция", "Продукт/Сервис",
                  "Операционные процессы", "Рынок и продажи")

SUBSECTIONS = ("Диагноз", "Профиль линий", "Ресурс и направление",
               "Ключевые напряжения", "Приоритеты вмешательства",
               "Маршрут перехода", "Оговорки по данным", "Следующие шаги")


def test_all_four_contour_sections_present():
    html = _render_full()
    for title in CONTOUR_TITLES:
        assert title in html, f"нет секции контура: {title}"
    assert "Сводная карта контуров" in html


def test_section_order_matches_report_structure():
    """01 Текущее состояние → 03 Финансы → 04 Сводная карта → 05–07 контуры."""
    html = _render_full()
    i_state = html.index("Текущее состояние")
    i_fin = html.index("Финансовая функция")
    i_sum = html.index("Сводная карта контуров")
    i_prod = html.index("Продукт/Сервис")
    i_proc = html.index("Операционные процессы")
    i_mkt = html.index("Рынок и продажи")
    assert i_state < i_fin < i_sum < i_prod < i_proc < i_mkt


def test_each_contour_uses_its_own_line_titles():
    """Названия линий контуров должны отличаться от финансовых: секция строится
    по blocks своего контура, а не по _FIN_BLOCKS (регресс параметра `blocks`)."""
    html = _render_full()
    assert "Продуктовые процессы" in html            # product, линия 1
    assert "Основные операционные процессы" in html   # process, линия 1
    assert "Коммерческие процессы" in html            # market, линия 1


def test_all_subsections_render_in_each_contour():
    html = _render_full()
    # Заголовки подразделов одинаковы для всех контуров — их должно быть минимум
    # по одному на каждый из четырёх (finance + 3), т.е. не меньше 4 вхождений.
    for h in SUBSECTIONS:
        assert html.count(h) >= 4, f"подраздел «{h}» встречается {html.count(h)}<4 раз"


def test_summary_lists_all_four_contours_and_verdict():
    _fin, _extra, summary = _build_inputs()
    html = _render_full()
    for key in CONTOUR_ORDER:
        assert CONTOURS[key].title in html
    # Вердикт согласован с расчётом: назван контур-ограничение либо честная
    # формулировка о сопоставимости при полном равенстве.
    if summary["constraint"]:
        assert CONTOURS[summary["constraint"]].title in html
        assert "зона системного ограничения" in html
    else:
        assert "сопоставимы по зрелости" in html


def test_page_breaks_on_every_section():
    """Финансовая секция, сводная карта и три контура открываются с новой
    страницы; карточки внутри не разрываются."""
    html = _render_full()
    # finance + summary + 3 контура = 5 секций с page-break-before
    assert html.count("page-break-before:always") >= 5
    assert "page-break-inside:avoid" in html


# ── Регресс: отчёт без контуров не должен приобретать лишних разделов ──────────

def test_legacy_report_without_contours():
    finance_result = compute_finance_result(_finance_control_answers())
    interp = build_interpretation(finance_result, {})
    html = build_report_html(
        company_name="Компания Y", user_name="CFO", date_str="22 июля 2026",
        combination="AAAABB", strategy=None, method2_data=None,
        finance_result=finance_result, finance_interpretation=interp,
        finance_strategy=None,
    )
    assert "Финансовая функция" in html       # финансовая секция остаётся
    assert "Сводная карта контуров" not in html
    assert "Продукт/Сервис" not in html


def test_summary_hidden_with_single_contour():
    """При одном пройденном контуре сводной карты нет (build_summary → None)."""
    finance_result = compute_finance_result(_finance_control_answers())
    assert build_summary({"finance": finance_result}) is None

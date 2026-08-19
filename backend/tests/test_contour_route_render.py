# -*- coding: utf-8 -*-
"""
Рендер маршрута перехода (роадмап 2.1, PR2): сводный маршрут в карте и
цепочка шагов в секции контура. Без Playwright и БД.
"""
from app.contour_route import build_route, build_summary_route
from app.contour_summary import build_summary
from app.contours import get_spec
from app.finance_pdf import contour_section_html, summary_card_html


def _line(n, symbol, moving, block="processes"):
    state = (("old_yin" if symbol == "B" else "old_yang") if moving
             else ("young_yin" if symbol == "B" else "young_yang"))
    return {"line": n, "block": block, "score": 0.0, "symbol": symbol,
            "state": state, "moving": moving, "flags": []}


def _result(maturity, moving_set, combo=None):
    if combo is None:
        combo = "".join("B" if n in moving_set else "A" for n in range(1, 7))
    lines = [_line(n, combo[n - 1], n in moving_set) for n in range(1, 7)]
    res_code = "".join(
        ("B" if combo[n - 1] == "A" else "A") if n in moving_set else combo[n - 1]
        for n in range(1, 7)
    )
    from app.contour_scoring import _lookup
    return {"lines": lines, "combination_current": combo,
            "combination_resulting": res_code, "moving_lines": sorted(moving_set),
            "maturity_index": maturity, "quadrant": "power_no_direction",
            "quality_flags": [], "hexagram_current": _lookup(combo),
            "hexagram_resulting": _lookup(res_code)}


def _enrich(route):
    for i, st in enumerate(route):
        st["action_text"] = "Пакет действий по линии."
        st["after_essence"] = "Промежуточное состояние."
        st["is_last"] = i == len(route) - 1
        st["mistake"] = "Типичная ошибка." if st["is_last"] else None
        st["is_veto"] = False
    return route


def test_summary_route_renders_stages():
    results = {"finance": _result(2, {6}), "product": _result(4, {1, 2})}
    summary = build_summary(results)
    summary["route"] = build_summary_route(results)
    html = summary_card_html(summary, "Компания X")
    assert "Сводный маршрут компании" in html
    assert "Этап 1" in html and "Этап 2" in html
    assert "точка входа" in html
    # порядок этапов по возрастанию зрелости: finance(2) раньше product(4)
    assert html.index("Финансовая функция") < html.index("Продукт/Сервис")


def test_six_step_route_renders_and_page_breaks():
    spec = get_spec("product")
    res = _result(0, {1, 2, 3, 4, 5, 6}, combo="AAAAAA")  # все 6 старый Ян
    route = _enrich(build_route(res["lines"], res["combination_current"]))
    interp = {"route": route}
    html = contour_section_html(
        res, interp, "Компания X",
        blocks=spec.blocks, title="Продукт/Сервис", section_no="05",
    )
    assert "Маршрут перехода" in html
    for n in range(1, 7):
        assert f"Шаг {n}. Линия {n}" in html
    # карточки шагов защищены от разрыва страницы
    assert html.count("page-break-inside:avoid") >= 6
    assert "Последовательность — рекомендуемая логика" in html


def test_no_moving_route_falls_back_to_stable_text():
    spec = get_spec("product")
    res = _result(6, set(), combo="AAAAAA")
    interp = {"route": []}
    html = contour_section_html(
        res, interp, "Компания X",
        blocks=spec.blocks, title="Продукт/Сервис", section_no="05",
    )
    assert "конфигурация стабильна" in html

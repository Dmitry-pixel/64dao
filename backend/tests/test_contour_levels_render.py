# -*- coding: utf-8 -*-
"""
Раздел «Три уровня» в отчёте: сквозная нумерация, место раздела, поведение
на снимке без уровней.

Заголовки разбираются структурно, а не поиском подстроки: тест про вёрстку,
проверяющий подстроку, ловит сам себя (napkin, 2026-07-28).
"""
import re

import pytest

from app.contour_levels import CUTS_CAVEAT
from app.contour_scoring import compute_contour_result
from app.contours import get_spec
from app.finance_interpret import build_interpretation
from app.finance_pdf import finance_section_html


def _answers(veto: bool) -> dict:
    spec = get_spec("finance")
    out = {}
    for it in spec.items:
        v = 4 if it["block"] % 2 else 1
        if it["item_id"] == "4.1":
            v = 1 if veto else 4
        out[it["item_id"]] = 5 - v if it["reverse"] else v
    return out


def _render(veto: bool = False, content: dict | None = None, strip: bool = False):
    spec = get_spec("finance")
    r = compute_contour_result(_answers(veto), spec)
    interp = build_interpretation(r, content if content is not None else {})
    if strip:
        interp["levels"] = []
        interp["levels_caveat"] = None
    return interp, finance_section_html(r, interp, "ООО Пример")


def _headings(html: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", html, re.S):
        inner = m.group(1)
        sp = re.search(r"<span[^>]*>(.*?)</span>", inner, re.S)
        num = sp.group(1).strip() if sp else ""
        text = re.sub(r"<[^>]+>", "", inner)
        out.append((num, text.replace(num, "", 1).strip()))
    return out


@pytest.mark.parametrize("veto", [True, False])
def test_numbering_is_sequential(veto):
    nums = [n for n, _ in _headings(_render(veto)[1])[1:]]
    assert nums == [f"{i:02d}" for i in range(1, len(nums) + 1)]


def test_veto_section_does_not_leave_a_gap():
    with_veto = [t for _, t in _headings(_render(True)[1])]
    without = [t for _, t in _headings(_render(False)[1])]
    assert "Условие, блокирующее трансформацию" in with_veto
    assert "Условие, блокирующее трансформацию" not in without
    assert len(with_veto) == len(without) + 1


def test_levels_sit_between_trigrams_and_tensions():
    titles = [t for _, t in _headings(_render()[1])]
    assert titles.index("Три уровня") == titles.index("Ресурс и направление") + 1
    assert titles.index("Ключевые напряжения") == titles.index("Три уровня") + 1


def test_absent_without_data_and_numbering_still_solid():
    titles_nums = _headings(_render(strip=True)[1])
    assert "Три уровня" not in [t for _, t in titles_nums]
    nums = [n for n, _ in titles_nums[1:]]
    assert nums == [f"{i:02d}" for i in range(1, len(nums) + 1)]


def test_caveat_and_titles_rendered():
    interp, html = _render()
    assert interp["levels_caveat"] == CUTS_CAVEAT
    assert CUTS_CAVEAT[:40] in html
    for lv in interp["levels"]:
        assert lv["title"] in html


def test_placeholder_when_content_missing():
    interp, _ = _render(content={})
    assert [lv["text"] for lv in interp["levels"]] == ["Не заполнено"] * 3

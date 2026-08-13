# -*- coding: utf-8 -*-
"""
Сквозная нумерация верхних разделов отчёта.

Номера видны клиенту. Раньше они раздавались арифметикой от наличия соседей,
а «Динамика» имела жёсткое 09: при трёх дополнительных контурах это сходилось
случайно, при другом их числе между контурами и динамикой оставалась дыра.

Верхний уровень опознаётся по плашке, а не по тексту: это единственный
признак, отличающий его от заголовков внутри секции.

Жизненный цикл здесь не покрыт: company_lifecycle_html требует структуру,
которую вслепую собирать нельзя.
"""
import re

from app.contour_scoring import compute_contour_result
from app.contour_summary import build_summary
from app.contours import get_spec
from app.finance_interpret import build_interpretation
from app.pdf import build_report_html


def _result(contour: str = "finance") -> dict:
    spec = get_spec(contour)
    ans = {}
    for it in spec.items:
        v = 4 if it["block"] % 2 else 1
        ans[it["item_id"]] = 5 - v if it["reverse"] else v
    return compute_contour_result(ans, spec)


def _entry(key: str) -> dict:
    r = _result(key)
    return {"contour": key, "title": get_spec(key).title, "result": r,
            "interp": build_interpretation(r, {}),
            "combination": r["combination_current"]}


def _html(**kw) -> str:
    base = dict(company_name="ООО Пример", user_name="Иван", date_str="1 января 2026",
                combination="ABABAB", strategy=None, method2_data=None, is_method2=False)
    base.update(kw)
    return build_report_html(**base)


def _top(html: str) -> list:
    out = []
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", html, re.S):
        inner = m.group(1)
        sp = re.search(r"<span[^>]*background:#c0392b[^>]*>(.*?)</span>", inner, re.S)
        if not sp:
            continue
        num = sp.group(1).strip()
        out.append((num, re.sub(r"<[^>]+>", "", inner).replace(num, "", 1).strip()))
    return out


def _assert_sequential(pairs):
    nums = [n for n, _ in pairs]
    assert nums == [f"{i:02d}" for i in range(1, len(nums) + 1)], nums


def test_minimal_report_starts_with_two_fixed_sections():
    pairs = _top(_html())
    _assert_sequential(pairs)
    assert [t for _, t in pairs][:2] == ["Текущее состояние", "Сценарий стратагемы"]


def test_finance_summary_and_contours_are_sequential():
    fin = _result()
    entries = [_entry("product"), _entry("process")]
    summary = build_summary({"finance": fin, "product": entries[0]["result"]})
    pairs = _top(_html(finance_result=fin,
                       finance_interpretation=build_interpretation(fin, {}),
                       summary=summary, extra_contours=entries))
    _assert_sequential(pairs)
    assert [t for _, t in pairs][-2:] == ["Продукт/Сервис", "Операционные процессы"]


def test_dynamics_number_follows_contours_and_is_not_hardcoded():
    fin = _result()
    interp = build_interpretation(fin, {})
    seen = {}
    for n in (1, 2, 3):
        entries = [_entry(k) for k in ("product", "process", "market")][:n]
        summary = build_summary({"finance": fin, "product": entries[0]["result"]})
        pairs = _top(_html(finance_result=fin, finance_interpretation=interp,
                           summary=summary, extra_contours=entries,
                           dynamics={"available": True}))
        _assert_sequential(pairs)
        seen[n] = pairs[-1][0]
    assert len(set(seen.values())) == 3, f"номер последнего раздела не сдвигается: {seen}"

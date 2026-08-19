# -*- coding: utf-8 -*-
"""Раздел 09 «Динамика» и строка сдвига в шапке разделов контуров — PDF.

Данные приходят из app/dynamics.py через build_report_html(dynamics=...).
Экранные аналоги — frontend/components/ContourShiftLine.tsx и
DynamicsSection.tsx; состав блоков держим одинаковым (правило паритета).

Формулировки собраны в TEXT одним словарём: следующий шаг — вынести их в
JSON-конфиг в volume по образцу contour_settings.py, чтобы правка текста не
требовала пересборки бэкенда.

Модуль намеренно не импортирует pdf.py: там импортируется он сам.
"""
import html as _html

from app.finance_pdf import section_badge

TEXT = {
    "maturity": "зрелость",
    "strengthen": "Инь → Ян (укрепление)",
    "weaken": "Ян → Инь (ослабление)",
    "moving_closed_lines": "Закрытые точки роста",
    "moving_new_lines": "Новые",
    "no_line_changes": "Без изменений в линиях.",
    "reached_target": "✓ Достигнута целевая гексаграмма предыдущего прогона",
    "title": "Динамика",
    "compared_with": "Сравнение с замером от",
    "maturity_up": "зрелость выросла",
    "maturity_down": "зрелость снизилась",
    "maturity_same": "зрелость не изменилась",
    "lines_changed": "изменились линии",
    "moving_new": "новые подвижные линии",
    "moving_closed": "закрылись подвижные линии",
    "reached": "достигнута результирующая гексаграмма предыдущего прогона",
    "improved": "Улучшилось",
    "degraded": "Ухудшилось",
    "unchanged": "Без изменений",
    "constraint_changed": "Контур-ограничение сместился",
    "constraint_same": "Контур-ограничение не изменился",
    "base_changed": "Базовая гексаграмма изменилась",
    "base_same": "Базовая гексаграмма прежняя",
}

_INK = "#1a2540"
_ACCENT = "#c0392b"
_BODY = (
    "font-size:12px;font-family:Arial,sans-serif;color:rgba(26,37,64,0.72);"
    "line-height:1.7;margin:0 0 8px;"
)
_LABEL = (
    "font-size:10px;color:rgba(26,37,64,0.45);text-transform:uppercase;"
    "letter-spacing:1px;font-family:Arial,sans-serif;margin:14px 0 6px;"
)


def _e(value) -> str:
    if value is None or value == "":
        return ""
    return _html.escape(str(value))


def _fmt_date(iso: str | None) -> str:
    if not iso or len(iso) < 10:
        return ""
    return iso[8:10] + "." + iso[5:7] + "." + iso[0:4]


def shift_summary(diff: dict | None) -> list[str]:
    """Фразы о сдвиге одного контура. Состав и формулировки совпадают со
    страницей /companies/[id]/dynamics и ContourShiftLine.tsx (правило паритета).
    Каждый элемент списка — отдельная строка вывода."""
    if not diff:
        return []
    out: list[str] = []
    delta = diff.get("maturity_delta") or 0
    out.append(
        TEXT["maturity"] + " " + str(diff.get("maturity_from")) + "/6 → "
        + str(diff.get("maturity_to")) + "/6 "
        + "(" + ("+" + str(delta) if delta > 0 else str(delta)) + ")"
    )
    if diff.get("reached_prev_target"):
        out.append(TEXT["reached_target"])
    changes = diff.get("line_changes") or []
    for ch in changes:
        key = ch.get("line_key") or ""
        out.append(
            "Линия " + str(ch.get("line")) + " (" + str(ch.get("line_title") or key) + "): "
            + (TEXT["strengthen"] if ch.get("direction") == "yin_to_yang"
               else TEXT["weaken"])
        )
    closed = diff.get("moving_closed") or []
    if closed:
        out.append(TEXT["moving_closed_lines"] + ": линии "
                   + ", ".join(str(n) for n in closed) + ".")
    new_moving = diff.get("moving_new") or []
    if new_moving:
        out.append(TEXT["moving_new_lines"] + ": линии "
                   + ", ".join(str(n) for n in new_moving) + ".")
    if not changes and not closed and not new_moving:
        out.append(TEXT["no_line_changes"])
    return out



def _contour_list(keys, titles: dict) -> str:
    names = [titles.get(k, k) for k in (keys or [])]
    return _e(", ".join(names)) if names else "<em style='opacity:0.4;'>—</em>"


def dynamics_section_html(dyn: dict | None, section_no: str = "09",
                          titles: dict | None = None) -> str:
    """Раздел 09 в конце повторного отчёта. Пустая строка, если сравнивать не с чем."""
    if not dyn or not dyn.get("available"):
        return ""
    titles = titles or {}
    compare_from = (dyn.get("compare_from") or {}).get("created_at")

    out = [
        "<h2 style='font-size:18px;font-weight:400;color:" + _INK + ";margin:26px 0 12px;'>"
        + section_badge(section_no)
        + _e(TEXT["title"]) + "</h2>"
    ]

    date_str = _fmt_date(compare_from)
    if date_str:
        out.append("<p style='" + _BODY + "'>" + _e(TEXT["compared_with"] + " " + date_str) + "</p>")

    contours = dyn.get("contours") or {}
    for key in sorted(contours):
        parts = shift_summary(contours[key])
        if not parts:
            continue
        out.append("<div style='" + _LABEL + "'>" + _e(titles.get(key, key)) + "</div>")
        out.append("<p style='" + _BODY + "'>"
                   + "<br>".join(_e(x) for x in parts) + "</p>")

    summary = dyn.get("summary") or {}
    if summary:
        out.append("<div style='" + _LABEL + "'>" + _e(TEXT["improved"]) + "</div>")
        out.append("<p style='" + _BODY + "'>" + _contour_list(summary.get("improved"), titles) + "</p>")
        out.append("<div style='" + _LABEL + "'>" + _e(TEXT["degraded"]) + "</div>")
        out.append("<p style='" + _BODY + "'>" + _contour_list(summary.get("degraded"), titles) + "</p>")
        out.append("<div style='" + _LABEL + "'>" + _e(TEXT["unchanged"]) + "</div>")
        out.append("<p style='" + _BODY + "'>" + _contour_list(summary.get("unchanged"), titles) + "</p>")

    constraint = dyn.get("constraint") or {}
    if constraint:
        if constraint.get("changed"):
            text = (TEXT["constraint_changed"] + ": "
                    + str(titles.get(constraint.get("from"), constraint.get("from") or "—"))
                    + " → "
                    + str(titles.get(constraint.get("to"), constraint.get("to") or "—")))
        else:
            text = (TEXT["constraint_same"] + ": "
                    + str(titles.get(constraint.get("to"), constraint.get("to") or "—")))
        out.append("<p style='" + _BODY + "'>" + _e(text) + "</p>")

    base_pair = dyn.get("base_pair") or {}
    if base_pair.get("combination_from") or base_pair.get("combination_to"):
        if base_pair.get("changed"):
            text = (TEXT["base_changed"] + ": "
                    + str(base_pair.get("combination_from") or "—")
                    + " → " + str(base_pair.get("combination_to") or "—"))
        else:
            text = TEXT["base_same"] + ": " + str(base_pair.get("combination_to") or "—")
        out.append("<p style='" + _BODY + "'>" + _e(text) + "</p>")

    return ("<div style='page-break-inside:avoid;'>" + "".join(out) + "</div>")

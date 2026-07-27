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

TEXT = {
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
_SHIFT = "#166534"

_SHIFT_STYLE = (
    "font-size:11px;font-family:Arial,sans-serif;color:" + _SHIFT + ";"
    "background:rgba(22,101,52,0.06);border:1px solid rgba(22,101,52,0.2);"
    "border-radius:6px;padding:8px 12px;margin:0 0 14px;line-height:1.6;"
)
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
    """Фразы о сдвиге одного контура. Общий источник для строки и раздела 09."""
    if not diff:
        return []
    out: list[str] = []
    delta = diff.get("maturity_delta") or 0
    m_from = diff.get("maturity_from")
    m_to = diff.get("maturity_to")
    if delta > 0:
        out.append(TEXT["maturity_up"] + ": " + str(m_from) + " → " + str(m_to))
    elif delta < 0:
        out.append(TEXT["maturity_down"] + ": " + str(m_from) + " → " + str(m_to))
    else:
        out.append(TEXT["maturity_same"])

    changes = diff.get("line_changes") or []
    if changes:
        names = [str(c.get("line_key") or c.get("line")) for c in changes]
        out.append(TEXT["lines_changed"] + ": " + ", ".join(names))

    new_moving = diff.get("moving_new") or []
    if new_moving:
        out.append(TEXT["moving_new"] + ": " + ", ".join(str(n) for n in new_moving))

    closed_moving = diff.get("moving_closed") or []
    if closed_moving:
        out.append(TEXT["moving_closed"] + ": " + ", ".join(str(n) for n in closed_moving))

    if diff.get("reached_prev_target"):
        out.append(TEXT["reached"])
    return out


def shift_line_html(diff: dict | None) -> str:
    """Строка сдвига под шапкой раздела контура."""
    parts = shift_summary(diff)
    if not parts:
        return ""
    return "<p style='" + _SHIFT_STYLE + "'>" + _e("; ".join(parts)) + "</p>"


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
        "<span style='font-size:11px;color:" + _ACCENT + ";margin-right:10px;'>"
        + _e(section_no) + "</span>" + _e(TEXT["title"]) + "</h2>"
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
        out.append("<p style='" + _BODY + "'>" + _e("; ".join(parts)) + "</p>")

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

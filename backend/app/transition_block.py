# -*- coding: utf-8 -*-
"""Раздел 02 «Целевой сценарий»: целевая гексаграмма и описание перехода.

Целевая гексаграмма приходит из БД (strategies.target_combination, миграция
020), а не из констант: маппинг правится в админке. Если цель не задана или
запись не найдена, выводится только описание перехода.

Модуль намеренно не импортирует pdf.py: там импортируется он сам.
"""
import html as _html
from typing import Any

_BOX = ("padding:16px 20px;border:1px solid rgba(192,57,43,0.2);"
        "border-radius:6px;background:rgba(192,57,43,0.04);")
_HEAD = ("font-size:10px;color:#c0392b;letter-spacing:2px;"
         "text-transform:uppercase;font-family:Arial,sans-serif;"
         "margin-bottom:12px;")
_LABEL = ("font-size:10px;color:rgba(26,37,64,0.45);text-transform:uppercase;"
          "letter-spacing:1px;font-family:Arial,sans-serif;margin-bottom:6px;")
_TEXT = ("font-size:12px;color:rgba(26,37,64,0.65);"
         "font-family:Arial,sans-serif;line-height:1.7;margin:0;")
_TARGET = ("font-size:13px;color:#1a2540;font-family:Arial,sans-serif;"
           "line-height:1.6;margin:0 0 16px;")

_PLACEHOLDER = ("<em style=\"opacity:0.4;\">Описание перехода будет добавлено "
                "при публикации стратегии.</em>")


def _e(text: str | None) -> str:
    return _html.escape(text) if text else ""


def transition_block(strategy: Any, target: Any | None, target_svg: str = '') -> str:
    """HTML раздела 02. target — запись Strategy целевой гексаграммы или None."""
    if not strategy:
        return ""
    desc = _e(strategy.transition_description) or _PLACEHOLDER
    parts = ["<div style=\"" + _BOX + "\">",
             "<div style=\"" + _HEAD + "\">",
             "<span style=\"margin-right:8px;\">02</span>Целевой сценарий</div>"]
    if target is not None and target.hexagram_number:
        parts.append("<div style=\"" + _LABEL + "\">Целевая гексаграмма</div>")
        if target_svg:
            parts.append(target_svg)
        parts.append("<p style=\"" + _TARGET + "\">"
                     + str(target.hexagram_number) + " &middot; "
                     + _e(target.title) + "</p>")
    parts.append("<div style=\"" + _LABEL + "\">Описание перехода</div>")
    parts.append("<p style=\"" + _TEXT + "\">" + desc + "</p>")
    parts.append("</div>")
    return "".join(parts)

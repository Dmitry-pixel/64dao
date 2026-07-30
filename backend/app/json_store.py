# -*- coding: utf-8 -*-
"""Общая механика рантайм-настроек: JSON-файл в volume uploads.

Семь модулей — pricing_store, tax_settings, tochka_settings,
contour_settings, reminders_settings, email_templates_store,
credits_settings — повторяли одно и то же: прочитать файл, слить с
дефолтами, проглотить отсутствие и битый JSON, создать каталог, записать.

Путь сюда передаётся аргументом и остаётся константой модуля-обёртки:
тесты подменяют именно её, а функция читает значение в момент вызова.

Запись атомарна: временный файл рядом и rename. Прежняя схема «открыть и
писать» при падении посреди записи оставляла обрезанный файл, и настройка
молча уезжала в дефолт — для цены диагностики или токена банка это дорого.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def read_json(path: str | Path, defaults: dict[str, Any] | None = None) -> dict:
    """Содержимое файла поверх дефолтов. Нет файла или битый JSON — дефолты."""
    base = dict(defaults or {})
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return base
    if not isinstance(data, dict):
        return base
    return {**base, **data}


def write_json(path: str | Path, data: dict) -> dict:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)
    return data

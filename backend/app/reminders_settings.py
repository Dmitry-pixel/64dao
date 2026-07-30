# -*- coding: utf-8 -*-
"""
Runtime-настройки email-напоминаний: включение и периодичность.

Раньше жили в config.py, то есть менялись только правкой .env и пересборкой
образа. Теперь это JSON в volume, как contour_settings и pricing: владелец
меняет их в админке без деплоя.

Расписание запуска остаётся в host cron (deploy/scripts/reminders.sh):
планировщик внутри приложения запрещён правилом проекта, иначе рассылка
будет дублироваться при каждом рестарте контейнера.

REMINDERS_ENABLED в .env остаётся аварийным выключателем на уровне сервера
и имеет приоритет над настройкой из админки.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from app.json_store import read_json, write_json

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/var/www/64dao/uploads")
SETTINGS_FILE = Path(UPLOAD_DIR) / "reminders_settings.json"

# Нижняя граница не даёт превратить напоминание в спам, верхняя ловит опечатки.
REPEAT_DAYS_MIN = 7
REPEAT_DAYS_MAX = 3650

_DEFAULTS: dict = {
    "enabled": True,         # общий выключатель всей рассылки
    "repeat_enabled": True,  # письмо «пора повторить диагностику»
    "repeat_days": 90,       # через сколько дней после последней диагностики
}


def normalize(data: dict) -> dict:
    """Приводит произвольный ввод к валидным значениям.

    Настройки приходят из админки и из файла на диске: доверять нельзя ни
    тому, ни другому.
    """
    out = dict(_DEFAULTS)
    out["enabled"] = bool(data.get("enabled", _DEFAULTS["enabled"]))
    out["repeat_enabled"] = bool(
        data.get("repeat_enabled", _DEFAULTS["repeat_enabled"]))
    try:
        days = int(data.get("repeat_days", _DEFAULTS["repeat_days"]))
    except (TypeError, ValueError):
        days = _DEFAULTS["repeat_days"]
    out["repeat_days"] = max(REPEAT_DAYS_MIN, min(REPEAT_DAYS_MAX, days))
    return out


def read() -> dict:
    # normalize приводит к умолчаниям всё, чего нет или что испорчено,
    # поэтому отдельные ветки «файла нет» и «не словарь» не нужны.
    return normalize(read_json(SETTINGS_FILE, _DEFAULTS))


def write(data: dict) -> dict:
    clean = normalize(data)
    write_json(SETTINGS_FILE, clean)
    return clean

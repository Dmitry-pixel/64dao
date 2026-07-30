# -*- coding: utf-8 -*-
"""Флаг обязательной оплаты диагностик — переключается из админки.

Тот же паттерн, что pricing.json / tax_settings.json / contour_settings.json:
JSON в volume dao64_uploads, значение из .env остаётся дефолтом, пока файл
не создан (обратная совместимость: ничего не меняется, если админкой ещё
не пользовались).

Зачем файл, а не только .env: это аварийный выключатель. Если после
включения оплаты что-то пойдёт не так у живых пользователей, правка .env
требует доступа к серверу и перезапуска backend, а переключатель в
админке — одного клика.
"""
import os
from pathlib import Path

from app.config import get_settings
from app.json_store import read_json, write_json

# conftest подменяет UPLOAD_DIR на временный каталог: с жёстким путём тесты
# читали бы боевой флаг обязательной оплаты и падали бы на 403.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
CREDITS_SETTINGS_FILE = Path(UPLOAD_DIR) / "credits_settings.json"


def read_credits_settings() -> dict:
    """{"enforce_credits": bool, "source": "admin" | "env"}.

    source показывает, откуда реально взято значение — чтобы в админке было
    видно, действует сохранённое здесь или запасное из .env.
    """
    data = read_json(CREDITS_SETTINGS_FILE)
    if "enforce_credits" not in data:
        return {"enforce_credits": bool(get_settings().enforce_credits),
                "source": "env"}
    return {"enforce_credits": bool(data["enforce_credits"]), "source": "admin"}


def enforce_credits_enabled() -> bool:
    return read_credits_settings()["enforce_credits"]


def set_enforce_credits(value: bool) -> dict:
    write_json(CREDITS_SETTINGS_FILE, {"enforce_credits": bool(value)})
    return read_credits_settings()

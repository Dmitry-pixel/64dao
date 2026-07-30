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
import json
from pathlib import Path

from app.config import get_settings

CREDITS_SETTINGS_FILE = Path("/var/www/64dao/uploads/credits_settings.json")


def read_credits_settings() -> dict:
    """{"enforce_credits": bool, "source": "admin" | "env"}.

    source показывает, откуда реально взято значение — чтобы в админке было
    видно, действует сохранённое здесь или запасное из .env.
    """
    try:
        data = json.loads(CREDITS_SETTINGS_FILE.read_text(encoding="utf-8"))
        value = data["enforce_credits"]
    except Exception:
        return {"enforce_credits": bool(get_settings().enforce_credits), "source": "env"}
    return {"enforce_credits": bool(value), "source": "admin"}


def enforce_credits_enabled() -> bool:
    return read_credits_settings()["enforce_credits"]


def set_enforce_credits(value: bool) -> dict:
    CREDITS_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDITS_SETTINGS_FILE.write_text(
        json.dumps({"enforce_credits": bool(value)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return read_credits_settings()

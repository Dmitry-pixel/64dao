"""
Переключатель НДС в чеках Точки.

Сейчас ИП освобождён от НДС (доход не превышает лимит по УСН). Когда это
изменится — не нужен редеплой кода, достаточно переключить флаг:

    docker compose exec backend python3 -c \
        "from app.tax_settings import set_vat_enabled; print(set_vat_enabled(True))"

Настройка хранится в JSON-файле в volume dao64_uploads (тот же паттерн,
что и social_links.json) — переживает пересборку образа.
"""
import json
import os

# Каталог берётся из UPLOAD_DIR (тот же приём, что в contour_settings.py и
# site_mode.py). Дефолт совпадает с прежним жёстким путём, поэтому в проде
# файл tax_settings.json резолвится ровно туда же, а тесты (conftest ставит
# UPLOAD_DIR на временную папку) больше не пишут флаг НДС в боевой том — F9.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
TAX_SETTINGS_PATH = os.path.join(UPLOAD_DIR, "tax_settings.json")

_DEFAULTS = {
    "vat_enabled": False,   # False = НДС не облагается (текущий статус)
    "vat_type": "vat20",    # ставка, которая применится, когда vat_enabled=True
}


def get_tax_settings() -> dict:
    if not os.path.exists(TAX_SETTINGS_PATH):
        return dict(_DEFAULTS)
    try:
        with open(TAX_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)


def _save(data: dict) -> dict:
    os.makedirs(os.path.dirname(TAX_SETTINGS_PATH), exist_ok=True)
    with open(TAX_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def set_vat_enabled(enabled: bool, vat_type: str = "vat20") -> dict:
    data = get_tax_settings()
    data["vat_enabled"] = enabled
    data["vat_type"] = vat_type
    return _save(data)


def current_vat_type() -> str:
    """Значение для поля Items[].vatType в запросе к Точке."""
    settings = get_tax_settings()
    return settings["vat_type"] if settings["vat_enabled"] else "none"

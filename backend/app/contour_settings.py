"""
Runtime-флаги контуров диагностики Метода 1.

Включение контура не требует пересборки образа: настройка лежит JSON-файлом
в volume dao64_uploads — тот же паттерн, что tax_settings.json и social_links.json.
Требование MANDATORY RULE №4 мастер-документа: feature-флаги живут в runtime-конфиге,
а не в env, иначе включение контура означает пересборку и перезапуск backend.

    docker compose exec backend python3 -c \\
        "from app.contour_settings import set_contour_enabled; print(set_contour_enabled('product', True))"
"""
import json
import os

# Каталог берётся из UPLOAD_DIR — тот же приём, что в site_mode.py.
# conftest подменяет её на временную папку, иначе тесты писали бы
# флаги контуров в боевой том и меняли поведение сайта.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
CONTOUR_SETTINGS_PATH = os.path.join(UPLOAD_DIR, "contour_settings.json")

# finance включён всегда: он часть обязательной анкеты Метода 1, а не
# дополнительный контур, проходимый из кабинета.
# Жизненный цикл компании считается только по всем четырём контурам: диагноз
# по одному контуру был бы однобоким. Поэтому все четыре включены — финансовый
# входит в обязательную анкету, остальные три проходятся из кабинета.
_DEFAULTS = {
    "finance": True,
    "product": True,
    "market": True,
    "process": True,
}


def get_contour_settings() -> dict:
    if not os.path.exists(CONTOUR_SETTINGS_PATH):
        return dict(_DEFAULTS)
    try:
        with open(CONTOUR_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)


def _save(data: dict) -> dict:
    os.makedirs(os.path.dirname(CONTOUR_SETTINGS_PATH), exist_ok=True)
    with open(CONTOUR_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def is_contour_enabled(contour: str) -> bool:
    return bool(get_contour_settings().get(contour, False))


def set_contour_enabled(contour: str, enabled: bool) -> dict:
    if contour not in _DEFAULTS:
        raise ValueError(f"Неизвестный контур: {contour}")
    if contour == "finance" and not enabled:
        raise ValueError("Финансовый контур — часть обязательной анкеты, отключать нельзя")
    data = get_contour_settings()
    data[contour] = bool(enabled)
    return _save(data)

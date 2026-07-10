"""
JWT-токен и Client ID Точки — редактируются из админки без редеплоя.

Раньше TOCHKA_JWT_TOKEN менялся только через .env + пересборку backend.
Теперь основное значение хранится в tochka_settings.json (volume
dao64_uploads, тот же паттерн, что pricing.json/tax_settings.json);
.env остаётся резервным значением на случай, если файл ещё не создан
(обратная совместимость — ничего не сломается, если админка ещё не
использовалась).

Client ID нигде в .env не хранился — использовался только вручную (curl)
для регистрации вебхука. Теперь тоже сохраняется здесь для админки.
"""
import json
from pathlib import Path

from app.config import get_settings

TOCHKA_SETTINGS_FILE = Path("/var/www/64dao/uploads/tochka_settings.json")

DEFAULTS = {
    "jwt_token": "",
    "client_id": "",
}


def read_tochka_settings() -> dict:
    try:
        data = json.loads(TOCHKA_SETTINGS_FILE.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except Exception:
        return dict(DEFAULTS)


def write_tochka_settings(data: dict) -> dict:
    """
    Обновляет только переданные непустые поля — пустая строка в запросе
    НЕ затирает уже сохранённое значение. Это важно для формы в админке:
    можно поменять только Client ID, оставив поле токена пустым, и наоборот.
    """
    current = read_tochka_settings()
    for key in ("jwt_token", "client_id"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            current[key] = value.strip()
    TOCHKA_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOCHKA_SETTINGS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def get_jwt_token() -> str:
    """Действующий JWT: из tochka_settings.json, иначе — запасной из .env."""
    stored = read_tochka_settings().get("jwt_token", "")
    if stored:
        return stored
    return get_settings().tochka_jwt_token


def get_client_id() -> str:
    return read_tochka_settings().get("client_id", "")


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 14:
        return value[:2] + "..." + value[-2:]
    return value[:6] + "..." + value[-6:]


def masked_view() -> dict:
    """
    Для GET /api/admin/tochka-settings — никогда не отдаёт значения целиком.
    jwt_token_source показывает, откуда реально берётся действующий токен:
    "admin" (сохранён через эту форму) или "env" (из .env на сервере, форма
    ещё не использовалась).
    """
    stored = read_tochka_settings()
    effective_jwt = get_jwt_token()
    client_id = stored.get("client_id", "")

    if stored.get("jwt_token"):
        source = "admin"
    elif effective_jwt:
        source = "env"
    else:
        source = "none"

    return {
        "jwt_token_masked": _mask(effective_jwt) if effective_jwt else None,
        "jwt_token_set": bool(effective_jwt),
        "jwt_token_source": source,
        "client_id_masked": _mask(client_id) if client_id else None,
        "client_id_set": bool(client_id),
    }

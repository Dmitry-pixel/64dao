import os
from pathlib import Path

from pydantic import BaseModel

from app.json_store import read_json, write_json

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
SITE_MODE_FILE = Path(UPLOAD_DIR) / "site_mode.json"

DEFAULT_SITE_MODE = {
    "enabled": False,
    "title": "Ведутся технические работы",
    "text": "Мы обновляем контент сайта. Это временно — скоро всё вернётся в обычный режим.",
}


class SiteMode(BaseModel):
    enabled: bool = False
    title: str = DEFAULT_SITE_MODE["title"]
    text: str = DEFAULT_SITE_MODE["text"]


def get_site_mode() -> SiteMode:
    try:
        return SiteMode(**read_json(SITE_MODE_FILE, DEFAULT_SITE_MODE))
    except Exception:
        # Файл мог накопить посторонние или несовместимые поля: режим
        # обслуживания не должен ронять сайт из-за собственной настройки.
        return SiteMode(**DEFAULT_SITE_MODE)


def set_site_mode(mode: SiteMode) -> SiteMode:
    write_json(SITE_MODE_FILE, mode.model_dump())
    return mode

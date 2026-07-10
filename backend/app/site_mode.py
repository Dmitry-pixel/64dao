import json
import os
from pathlib import Path
from pydantic import BaseModel

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
        if not SITE_MODE_FILE.exists():
            return SiteMode(**DEFAULT_SITE_MODE)
        with open(SITE_MODE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SiteMode(**{**DEFAULT_SITE_MODE, **data})
    except Exception:
        return SiteMode(**DEFAULT_SITE_MODE)


def set_site_mode(mode: SiteMode) -> SiteMode:
    SITE_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_MODE_FILE, "w", encoding="utf-8") as f:
        json.dump(mode.model_dump(), f, ensure_ascii=False, indent=2)
    return mode

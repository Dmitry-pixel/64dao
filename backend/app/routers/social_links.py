"""
Публичный доступ к ссылкам на соц.сети.
GET /api/social-links — текущие ссылки (без авторизации).
"""
import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/social-links", tags=["social-links"])

SOCIAL_LINKS_FILE = Path("/var/www/64dao/uploads/social_links.json")

DEFAULT_LINKS = {
    "telegram": "",
    "vk": "",
    "max": "",
}


@router.get("")
async def get_public_social_links():
    try:
        return json.loads(SOCIAL_LINKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_LINKS.copy()

"""
Ссылки на соц.сети.
GET /api/social-links — публичные, без авторизации (для футера).
GET/PUT /api/admin/social-links — управление, требует прав администратора.
Хранение: JSON-файл, по образцу pricing.py.
"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_admin
from app.json_store import read_json, write_json
from app.models import User

router = APIRouter(tags=["social-links"])

# Каталог из UPLOAD_DIR, как в остальных модулях настроек. С зашитым путём
# тесты писали бы в боевой том — ровно то, от чего защищает
# test_tax_settings.py для соседнего файла настроек.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
SOCIAL_LINKS_FILE = Path(UPLOAD_DIR) / "social_links.json"

DEFAULT_LINKS = {
    "telegram": "https://t.me/64dao_blog",
    "vk": "https://vk.com/64dao",
    "max": "https://max.ru/64dao_max",
}


class SocialLinks(BaseModel):
    telegram: str = ""
    vk: str = ""
    max: str = ""


def _read_links() -> dict:
    return read_json(SOCIAL_LINKS_FILE, DEFAULT_LINKS)


@router.get("/api/social-links")
async def get_public_social_links():
    """Публичный эндпоинт — используется футером на всех страницах."""
    return _read_links()


@router.get("/api/admin/social-links")
async def get_admin_social_links(admin: User = Depends(require_admin)):
    return _read_links()


@router.put("/api/admin/social-links")
async def update_social_links(
    body: SocialLinks,
    admin: User = Depends(require_admin),
):
    """
    Ссылки принимаются как есть, без валидации формата URL —
    решение подтверждено при проектировании фичи.
    """
    return write_json(SOCIAL_LINKS_FILE, body.model_dump())

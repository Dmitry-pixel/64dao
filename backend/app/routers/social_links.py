"""
Ссылки на соц.сети.
GET /api/social-links — публичные, без авторизации (для футера).
GET/PUT /api/admin/social-links — управление, требует прав администратора.
Хранение: JSON-файл, по образцу pricing.py.
"""
import json
from pathlib import Path
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_admin
from app.models import User

router = APIRouter(tags=["social-links"])
SOCIAL_LINKS_FILE = Path("/var/www/64dao/uploads/social_links.json")

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
    try:
        return json.loads(SOCIAL_LINKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_LINKS.copy()


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
    data = body.model_dump()
    SOCIAL_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOCIAL_LINKS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data

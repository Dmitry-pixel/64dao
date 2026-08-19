"""
Публичный доступ к юридическим документам.
GET /api/documents/{slug} — только опубликованные документы.
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/documents", tags=["documents"])

DOCS_DIR = Path("/var/www/64dao/uploads/docs")

ALLOWED_DOC_SLUGS = {
    "user-agreement",
    "privacy-policy",
    "personal-data-consent",
    "about",
}


@router.get("/{slug}")
async def get_public_document(slug: str):
    if slug not in ALLOWED_DOC_SLUGS:
        raise HTTPException(status_code=404, detail="Документ не найден")

    path = DOCS_DIR / f"{slug}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=404, detail="Документ не найден или не опубликован") from None

    if not data.get("published"):
        raise HTTPException(status_code=404, detail="Документ не опубликован")

    return data

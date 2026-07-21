# -*- coding: utf-8 -*-
"""
Публичные (для авторизованных) данные анкет Метода 1.
Единый источник текстов утверждений — app/contours.py, без дублирования во фронте.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.contours import CONTOURS, CONTOUR_ORDER, INTRO_TEXTS, get_spec
from app.contour_settings import get_contour_settings, is_contour_enabled
from app.finance_items import SCALE_LABELS
from app.models import User

router = APIRouter(prefix="/api/method1", tags=["method1"])


def _items_payload(contour: str) -> dict:
    spec = get_spec(contour)
    blocks = []
    for b in sorted(spec.blocks):
        blocks.append({
            "block": b,
            "title": spec.blocks[b]["title"],
            "items": [{"item_id": it["item_id"], "text": it["text"]}
                      for it in spec.items if it["block"] == b],
        })
    return {
        "contour": contour,
        "title": spec.title,
        "intro": INTRO_TEXTS.get(contour, ""),
        "max_unknowns": spec.max_unknowns,
        "scale_labels": SCALE_LABELS,
        "blocks": blocks,
    }


@router.get("/finance-items")
async def get_finance_items(user: User = Depends(get_current_user)):
    """24 пункта финансового блока. Алиас /contour-items/finance для текущего фронта."""
    return _items_payload("finance")


@router.get("/contours")
async def list_contours(user: User = Depends(get_current_user)):
    """Контуры с признаком включённости — для кабинета."""
    enabled = get_contour_settings()
    return {"contours": [
        {
            "contour": k,
            "title": CONTOURS[k].title,
            "intro": INTRO_TEXTS.get(k, ""),
            "enabled": bool(enabled.get(k, False)),
        }
        for k in CONTOUR_ORDER
    ]}


@router.get("/contour-items/{contour}")
async def get_contour_items(contour: str, user: User = Depends(get_current_user)):
    """Анкета контура. 404 для неизвестного и для выключенного — снаружи неразличимы."""
    if contour not in CONTOURS or not is_contour_enabled(contour):
        raise HTTPException(status_code=404, detail="Контур недоступен")
    return _items_payload(contour)

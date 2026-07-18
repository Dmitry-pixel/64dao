# -*- coding: utf-8 -*-
"""
Публичные (для авторизованных) данные анкеты Метода 1: финансовый блок.
Единый источник текстов 24 пунктов — app/finance_items.py (без дублирования во фронте).
"""
from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.finance_items import FINANCE_ITEMS, BLOCKS, SCALE_LABELS
from app.models import User

router = APIRouter(prefix="/api/method1", tags=["method1"])


@router.get("/finance-items")
async def get_finance_items(user: User = Depends(get_current_user)):
    """24 пункта финансового блока по 6 блокам + ярлыки шкалы 1–4."""
    blocks = []
    for b in sorted(BLOCKS):
        items = [{"item_id": it["item_id"], "text": it["text"]}
                 for it in FINANCE_ITEMS if it["block"] == b]
        blocks.append({"block": b, "title": BLOCKS[b]["title"], "items": items})
    return {"scale_labels": SCALE_LABELS, "blocks": blocks}

"""
Публичный доступ к тарифу/цене диагностики.
GET /api/pricing — текущая цена и условия (без авторизации).
"""
import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/pricing", tags=["pricing"])

PRICING_FILE = Path("/var/www/64dao/uploads/pricing.json")

DEFAULT_PRICING = {
    "title": "Полный отчёт 64 ДАО",
    "price": 14900,
    "currency": "₽",
    "description": "разовая оплата · НДС не облагается",
    "features": [
        {"label": "Диагностика", "value": "Метод 1 + Метод 2"},
        {"label": "PDF-отчёт", "value": "Включён"},
        {"label": "Онлайн-просмотр", "value": "Без ограничений"},
        {"label": "Срок готовности", "value": "До 30 минут"},
    ],
    "payment_enabled": False,
    "payment_note": "Платёжный шлюз (ЮKassa / Тинькофф) подключим после тестирования сайта. Пока что отчёты доступны в демо-режиме без оплаты.",
}


@router.get("")
async def get_public_pricing():
    try:
        return json.loads(PRICING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_PRICING.copy()

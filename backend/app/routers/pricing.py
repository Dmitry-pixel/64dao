"""
Публичный доступ к тарифам диагностики.
GET /api/pricing — цены и условия по продуктам (без авторизации).

Форма ответа:
    {...поля тарифа m12..., "products": {"m12": {...}, "m3": {...}}}

Плоские поля m12 сверху — ради лендинга (frontend/src/app/page.tsx), который
читает price/title/features напрямую. Новые экраны берут products. Дубль
временный: снимается, когда лендинг переедет на products.
"""
from fastapi import APIRouter

from app.pricing_store import read_pricing

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


@router.get("")
async def get_public_pricing():
    pricing = read_pricing()
    return {**pricing["m12"], "products": pricing}

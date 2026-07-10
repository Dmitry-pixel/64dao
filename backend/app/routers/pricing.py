"""
Публичный доступ к тарифу/цене диагностики.
GET /api/pricing — текущая цена и условия (без авторизации).
"""
from fastapi import APIRouter

from app.pricing_store import read_pricing

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


@router.get("")
async def get_public_pricing():
    return read_pricing()

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Assessment, Order, User

router = APIRouter(prefix="/api/payments", tags=["payments"])

REPORTS_PER_ORDER = 2


# TODO: Refund handling (when payment system is connected)
#   When Order.status changes to 'refunded', the linked Assessment should be:
#   1. Moved back to 'draft' status (so it doesn't count as used_assessments)
#   2. OR deleted entirely if user requests full cancellation
#   This way, calculate_credits() will automatically restore the balance.
#   Currently, refunds are not supported (stub payment system).


async def calculate_credits(user_id, db: AsyncSession) -> int:
    """
    Возвращает количество оплаченных, но ещё не использованных диагностик.

    Логика (stub до подключения реальной оплаты):
      credits = (paid orders * REPORTS_PER_ORDER) - completed/paid assessments
    Минимум 0 — не уходим в минус.

    Общая функция: используется эндпоинтом /credits и проверкой доступа
    при создании assessment / генерации отчёта (см. routers/assessments.py).
    """
    paid_orders = await db.scalar(
        select(func.count(Order.id))
        .where(Order.user_id == user_id, Order.status == "paid")
    ) or 0

    used_assessments = await db.scalar(
        select(func.count(Assessment.id))
        .where(
            Assessment.user_id == user_id,
            Assessment.status.in_(["completed", "paid"]),
        )
    ) or 0

    return max(0, paid_orders * REPORTS_PER_ORDER - used_assessments)


@router.get("/credits")
async def get_credits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    credits = await calculate_credits(user.id, db)
    return {"credits": credits}


@router.get("/orders")
async def list_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """История заказов пользователя."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.assessment))
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    out = []
    for o in orders:
        a = o.assessment
        out.append({
            "id": str(o.id),
            "assessment_id": str(o.assessment_id),
            "amount": float(o.amount),
            "currency": o.currency,
            "status": o.status,
            "payment_id": o.payment_id,
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "created_at": o.created_at.isoformat(),
            "assessment": {
                "method1_combination": a.method1_combination if a else None,
                "method2_data": a.method2_data if a else None,
                "reports": [{"id": str(r.id)} for r in a.reports] if a else [],
            } if a else None,
        })
    return out

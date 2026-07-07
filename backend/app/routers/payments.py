from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Assessment, Order, User
from app.tochka_client import get_tochka_client
from fastapi import Request, HTTPException

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


@router.post("/create")
async def create_payment(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.config import get_settings
    settings = get_settings()

    order = Order(
        user_id=user.id,
        assessment_id=assessment_id,
        amount=5500.00,
        currency="RUB",
        status="pending",
    )
    db.add(order)
    await db.flush()

    client = get_tochka_client()
    try:
        tochka_resp = await client.create_payment_with_receipt(
            amount=float(order.amount),
            purpose=f"Оплата диагностики 64 DAO, заказ {order.id}",
            order_id=str(order.id),
            customer_email=user.email,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=502, detail=f"Tochka API error: {e}")

    data = tochka_resp.get("Data", {})
    order.tochka_operation_id = data.get("operationId")
    order.tochka_payment_link = data.get("paymentLink")
    order.merchant_id = settings.tochka_merchant_id

    await db.commit()
    await db.refresh(order)

    return {
        "order_id": str(order.id),
        "payment_link": order.tochka_payment_link,
    }


@router.post("/webhook")
async def tochka_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    client = get_tochka_client()

    if not client.verify_webhook(dict(request.headers), body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    event_data = payload.get("Data", {})
    operation_id = event_data.get("operationId")
    status = event_data.get("status")

    if not operation_id:
        raise HTTPException(status_code=400, detail="Missing operationId")

    result = await db.execute(
        select(Order).where(Order.tochka_operation_id == operation_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "paid":
        return {"status": "already_processed"}

    order.webhook_payload = payload
    if status == "APPROVED":
        order.status = "paid"
        from datetime import datetime, timezone
        order.paid_at = datetime.now(timezone.utc)
    elif status in ("REJECTED", "DECLINED"):
        order.status = "failed"

    await db.commit()
    return {"status": "ok"}


@router.get("/{order_id}/status")
async def get_order_status(
    order_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "pending" and order.tochka_operation_id:
        client = get_tochka_client()
        try:
            resp = await client.get_payment_status(order.tochka_operation_id)
            remote_status = resp.get("Data", {}).get("status")
            if remote_status == "APPROVED":
                order.status = "paid"
                from datetime import datetime, timezone
                order.paid_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception:
            pass

    return {"status": order.status}

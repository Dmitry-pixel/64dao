import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, require_admin
from app.db import get_db
from app.models import Assessment, Order, User
from app.tochka_client import get_tochka_client
from app.config import get_settings
from app.tax_settings import get_tax_settings, set_vat_enabled, current_vat_type
from app.pricing_store import current_price, is_payment_enabled

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

REPORTS_PER_ORDER = 2
# Цена больше НЕ хардкодится здесь — берётся из pricing.json через
# app.pricing_store (тот же источник, что у лендинга и админки "Тариф и цена").
# Раньше тут было REPORT_PRICE = 5500.00, а реальная цена на сайте — 14900 ₽:
# создание платежа ушло бы на неверную сумму.


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
    if not is_payment_enabled():
        raise HTTPException(status_code=503, detail="Payment is currently disabled")

    settings = get_settings()
    price = current_price()

    order = Order(
        user_id=user.id,
        assessment_id=assessment_id,
        amount=price,
        currency="RUB",
        status="pending",
    )
    db.add(order)
    await db.flush()

    # Состав чека (54-ФЗ). Один товар — услуга диагностики.
    # vatType берётся динамически из tax_settings.json (переключатель НДС,
    # см. app/tax_settings.py) — сейчас ИП освобождён от НДС (vat_enabled=False
    # -> vatType="none"). Когда лимит по доходу будет превышен, переключить
    # флаг командой из app/tax_settings.py, без редеплоя.
    items = [
        {
            "name": "Стратегическая диагностика 64 DAO",
            "amount": float(order.amount),
            "quantity": 1,
            "vatType": current_vat_type(),
            "paymentMethod": "full_prepayment",
            "paymentObject": "service",
        }
    ]

    client = get_tochka_client()
    try:
        tochka_resp = await client.create_payment_with_receipt(
            amount=float(order.amount),
            purpose=f"Оплата диагностики 64 DAO, заказ {order.id}",
            order_id=str(order.id),
            customer_email=user.email,
            items=items,
        )
    except Exception as e:
        await db.rollback()
        body = getattr(getattr(e, "response", None), "text", None)
        raise HTTPException(status_code=502, detail=f"Tochka API error: {e} | body: {body}")

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


@router.post("/test-create")
async def create_test_payment(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Тестовый платёж на 1 ₽ (не полная цена) — проверить прохождение оплаты,
    чека и вебхука через реальный Точка API без списания полной суммы.
    Доступно только администратору.

    Order.assessment_id обязателен по схеме БД (NOT NULL) — создаём
    служебный Assessment (status='draft', без данных диагностики), он не
    расходует кредиты и не появляется как отчёт пользователя.

    Работает НЕЗАВИСИМО от pricing.payment_enabled — тестировать нужно
    именно до включения оплаты для обычных пользователей.
    """
    settings = get_settings()

    test_assessment = Assessment(
        user_id=admin.id,
        status="draft",
        company_name="[ТЕСТ ОПЛАТЫ] служебная запись, можно игнорировать",
    )
    db.add(test_assessment)
    await db.flush()

    order = Order(
        user_id=admin.id,
        assessment_id=test_assessment.id,
        amount=1.00,
        currency="RUB",
        status="pending",
    )
    db.add(order)
    await db.flush()

    items = [
        {
            "name": "ТЕСТ: проверка оплаты (1 ₽)",
            "amount": 1.00,
            "quantity": 1,
            "vatType": current_vat_type(),
            "paymentMethod": "full_prepayment",
            "paymentObject": "service",
        }
    ]

    client = get_tochka_client()
    try:
        tochka_resp = await client.create_payment_with_receipt(
            amount=1.00,
            purpose=f"ТЕСТ оплаты 64 DAO, заказ {order.id}",
            order_id=str(order.id),
            customer_email=admin.email,
            items=items,
        )
    except Exception as e:
        await db.rollback()
        body = getattr(getattr(e, "response", None), "text", None)
        raise HTTPException(status_code=502, detail=f"Tochka API error: {e} | body: {body}")

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
    """
    ВАЖНО: тело вебхука от Точки — НЕ JSON, а «голая» строка JWT (RS256),
    Content-Type: text/plain. Раньше здесь стоял request.json() — это
    падало бы 400/500 на первом же реальном вебхуке от банка.

    Подпись проверяется публичным ключом Точки (см. tochka_client.py).

    ВАЖНО #2: Точка при создании/редактировании вебхука сама шлёт тестовый
    запрос на этот URL и требует HTTP 200 в ответ — иначе подписку не
    создаст (см. документацию: "Если в ответ не придёт код HTTP 200...").
    Поэтому на непроверяемые/неопознанные запросы отвечаем 200 (просто
    игнорируем), а не 401/404 — но НИКОГДА не доверяем и не применяем
    данные, если подпись не прошла проверку или заказ не найден.
    """
    raw_body = await request.body()
    client = get_tochka_client()

    try:
        claims = await client.verify_and_decode_webhook(raw_body)
    except Exception as e:
        logger.warning("Tochka webhook: signature verification failed: %s", e)
        return {"status": "ignored", "reason": "invalid signature"}

    operation_id = claims.get("operationId")
    status = claims.get("status")

    if not operation_id:
        return {"status": "ignored", "reason": "no operationId"}

    result = await db.execute(
        select(Order).where(Order.tochka_operation_id == operation_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        logger.info("Tochka webhook: no order for operationId=%s (test/unknown webhook)", operation_id)
        return {"status": "ignored", "reason": "order not found"}

    if order.status == "paid":
        return {"status": "already_processed"}

    order.webhook_payload = claims
    if status == "APPROVED":
        order.status = "paid"
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
                order.paid_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception:
            pass

    return {"status": order.status}


@router.post("/{order_id}/refund")
async def refund_order(
    order_id: str,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Возврат оплаченного заказа. Доступно только администратору
    (ручной процесс — по обращению пользователя, см. Раздел 10
    Пользовательского соглашения о возврате).

    После возврата:
      1. Order.status -> 'refunded'
      2. Assessment (если есть и статус completed/paid) -> 'draft',
         чтобы calculate_credits() снова учёл этот кредит как свободный.

    Требует TOCHKA_MERCHANT_ID/JWT в .env и order.tochka_operation_id
    (т.е. платёж должен быть реально проведён через Точку).
    """
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.assessment))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "paid":
        raise HTTPException(status_code=400, detail=f"Order status is '{order.status}', not 'paid'")

    if not order.tochka_operation_id:
        raise HTTPException(status_code=400, detail="Order has no tochka_operation_id")

    client = get_tochka_client()
    try:
        await client.refund_payment(order.tochka_operation_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Tochka refund error: {e}")

    order.status = "refunded"

    if order.assessment and order.assessment.status in ("completed", "paid"):
        order.assessment.status = "draft"

    await db.commit()
    return {"status": "refunded"}


# ── НДС: переключатель (для будущего admin UI) ──────────────────────────────
# Быстрее всего переключить прямо из консоли, без похода через HTTP/UI:
#   docker compose exec backend python3 -c \
#     "from app.tax_settings import set_vat_enabled; print(set_vat_enabled(True))"
# Эндпоинты ниже — для тех же двух действий через API/будущую кнопку в админке.

@router.get("/admin/tax-settings")
async def get_tax_settings_endpoint(
    _admin: User = Depends(require_admin),
):
    return get_tax_settings()


@router.put("/admin/tax-settings")
async def update_tax_settings_endpoint(
    vat_enabled: bool,
    vat_type: str = "vat20",
    _admin: User = Depends(require_admin),
):
    return set_vat_enabled(vat_enabled, vat_type)

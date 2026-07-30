import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, require_admin
from app.db import get_db
from app.models import Assessment, Order, User
from app.tochka_client import get_tochka_client, extract_operation
from app.config import get_settings
from app.tax_settings import get_tax_settings, set_vat_enabled, current_vat_type
from app.pricing_store import current_price, is_payment_enabled
from app.credits_settings import read_credits_settings, set_enforce_credits
from app.access_grants import grant_credits, nearest_expiry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

REPORTS_PER_ORDER = 2

# Вебхука о возврате у Точки НЕ существует: банк шлёт вебхуки только об
# успешных операциях, событий ровно пять (incomingPayment, outgoingPayment,
# incomingSbpPayment, incomingSbpB2BPayment, acquiringInternetPayment) и
# возврата среди них нет. Возврат, проведённый в кабинете банка, виден
# приложению только опросом Get Payment Operation Info — см. reconcile
# и get_order_status. Ветка в вебхуке оставлена как страховка на случай,
# если Точка добавит такое событие: на платёжном вебхуке она не срабатывает
# (в его claims нет ни isRefund, ни этих статусов — проверено на боевом).
# Статус REFUNDED здесь тот же, что возвращает Get Payment Operation Info.
REFUND_STATUSES = {"REFUNDED", "REFUND", "REVERSED"}

# Статусы, в которых диагностика считается израсходованной — тот же набор,
# что в paid_credits и access_grants.USED_STATUSES.
USED_STATUSES = ("completed", "paid")


def _is_refund_event(claims: dict) -> bool:
    if str(claims.get("isRefund", "")).lower() == "true":
        return True
    return str(claims.get("status") or "").upper() in REFUND_STATUSES


async def revoke_order_access(db: AsyncSession, order: Order) -> dict:
    """Полный отзыв доступа по возвращённому заказу.

    Оплата покупает диагностику целиком: Метод 1, Метод 2 и повторный
    Метод 1. По частям она не продаётся, поэтому возврат закрывает всё,
    что было пройдено, — считать «использованную» долю не нужно.

    Неиспользованный остаток кредитов отзывать тоже не нужно: paid_credits
    учитывает только заказы в статусе 'paid', так что смена статуса на
    'refunded' сама снимает REPORTS_PER_ORDER из баланса.

    Все затронутые диагностики уходят в 'draft'. Это не только закрытие
    доступа, но и корректность счётчика: used_assessments считается
    глобально, и оставленная в 'completed' диагностика возвращённого
    заказа вычиталась бы из кредитов будущих покупок — пользователь
    заплатил бы за неё дважды.

    Отзываются диагностики, привязанные к заказу через assessments.order_id
    (миграция 022), их повторы и запись, из которой создан платёж. Раньше
    границей была компания: при нескольких платных заказах на одну компанию
    возврат одного закрывал доступ, оплаченный другим.
    """
    a = order.assessment
    if a is None:
        return {"assessments": 0, "followup_rights": 0}

    rows = list((await db.execute(
        select(Assessment).where(Assessment.order_id == order.id)
    )).scalars().all())
    # Запись, из которой создан платёж: у легаси-заказов и служебных
    # тестовых платежей привязки может не быть вовсе.
    if a not in rows:
        rows.append(a)
    # Повторы куплены вместе с основной диагностикой и отзываются с ней.
    followups = (await db.execute(
        select(Assessment).where(
            Assessment.parent_assessment_id.in_([r.id for r in rows])
        )
    )).scalars().all()
    rows += [f for f in followups if f not in rows]

    closed = 0
    rights = 0
    for row in rows:
        if row.status in USED_STATUSES:
            row.status = "draft"
            closed += 1
        # followup_used обнуляется вместе с followup_allowed: снять только
        # право нельзя — при пройденном повторе запись не пройдёт
        # chk_assessment_followup_used (used <= allowed).
        if row.followup_allowed or row.followup_used:
            row.followup_used = 0
            row.followup_allowed = 0
            rights += 1

    return {"assessments": closed, "followup_rights": rights}


async def pick_order(db: AsyncSession, user_id) -> Order | None:
    """Оплаченный заказ с непотраченным остатком — им и оплатится диагностика.

    Старейший первым. Аналог access_grants.pick_grant, только у платного
    кредита нет срока сгорания, поэтому порядок — по дате оплаты.
    """
    orders = (await db.execute(
        select(Order)
        .where(Order.user_id == user_id, Order.status == "paid")
        .order_by(func.coalesce(Order.paid_at, Order.created_at).asc(),
                  Order.id.asc())
    )).scalars().all()
    if not orders:
        return None

    rows = await db.execute(
        select(Assessment.order_id, func.count(Assessment.id))
        .where(Assessment.order_id.in_([o.id for o in orders]),
               Assessment.status.in_(USED_STATUSES),
               Assessment.is_followup.is_(False))
        .group_by(Assessment.order_id)
    )
    used = {oid: cnt for oid, cnt in rows.all()}
    for o in orders:
        if used.get(o.id, 0) < REPORTS_PER_ORDER:
            return o
    return None


# Цена больше НЕ хардкодится здесь — берётся из pricing.json через
# app.pricing_store (тот же источник, что у лендинга и админки "Тариф и цена").
# Раньше тут было REPORT_PRICE = 5500.00, а реальная цена на сайте — 14900 ₽:
# создание платежа ушло бы на неверную сумму.


async def paid_credits(user_id, db: AsyncSession) -> int:
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
        .join(Order, Order.id == Assessment.order_id)
        .where(
            Order.user_id == user_id,
            Order.status == "paid",
            Assessment.status.in_(["completed", "paid"]),
            # Повтор входит в стоимость основной диагностики и кредит не
            # тратит. Иначе на один заказ приходится 2 прогона из трёх
            # обещанных (Метод 1 + Метод 2 + повтор), и на третьем
            # пользователь получает 403. Лимит повторов держится на
            # followup_allowed/followup_used, а не на кредитах.
            Assessment.is_followup.is_(False),
        )
    ) or 0

    return max(0, paid_orders * REPORTS_PER_ORDER - used_assessments)


async def calculate_credits(user_id, db: AsyncSession) -> int:
    """Все доступные диагностики: оплаченные + выданные грантом.

    Имя сохранено ради существующих вызовов из routers/assessments.py.
    Там, где нужен именно платный остаток (ветка списания), вызывайте
    paid_credits(): грант списывается отдельно, через access_grants.
    """
    return await paid_credits(user_id, db) + await grant_credits(db, user_id)


async def credits_breakdown(user_id, db: AsyncSession) -> dict:
    """Разбивка для кабинета: платные, грантовые и дата сгорания гранта."""
    paid = await paid_credits(user_id, db)
    granted = await grant_credits(db, user_id)
    expires = await nearest_expiry(db, user_id)
    return {
        "credits": paid + granted,
        "paid_credits": paid,
        "grant_credits": granted,
        "grant_expires_at": expires.isoformat() if expires else None,
    }


@router.get("/credits")
async def get_credits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await credits_breakdown(user.id, db)


@router.get("/orders")
async def list_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """История заказов пользователя."""
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user.id)
        # reports грузим сразу: обращение к a.reports в цикле ниже уходит в
        # ленивую загрузку вне async-контекста и даёт greenlet_spawn -> 500
        # (воспроизведено на боевом после первой реальной оплаты).
        .options(selectinload(Order.assessment).selectinload(Assessment.reports))
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
        select(Order)
        .where(Order.tochka_operation_id == operation_id)
        # assessment грузим сразу: ветка возврата обращается к нему, а
        # ленивая загрузка вне async-контекста даёт greenlet_spawn -> 500
        # (ровно этот баг уже ловили в /api/payments/orders).
        .options(selectinload(Order.assessment))
    )
    order = result.scalar_one_or_none()
    if not order:
        logger.info("Tochka webhook: no order for operationId=%s (test/unknown webhook)", operation_id)
        return {"status": "ignored", "reason": "order not found"}

    # Сверка возврата с банком. Идемпотентно: повторный вебхук по уже
    # возвращённому заказу ничего не ломает.
    if _is_refund_event(claims):
        was_refunded = order.status == "refunded"
        order.webhook_payload = claims
        order.status = "refunded"
        revoked = await revoke_order_access(db, order)
        await db.commit()
        logger.info("Tochka webhook: refund confirmed for order %s (%s)", order.id, revoked)
        return {"status": "refunded", "was_refunded": was_refunded,
                "revoked_assessments": revoked["assessments"],
                "revoked_followup_rights": revoked["followup_rights"]}

    # Возвращённый заказ не воскрешаем. Ретрай вебхука или вебхук самой
    # операции возврата со статусом APPROVED иначе вернул бы 'paid', а с
    # ним REPORTS_PER_ORDER кредитов при возвращённых деньгах.
    if order.status == "refunded":
        logger.warning("Tochka webhook: status=%s for refunded order %s — ignored",
                       status, order.id)
        return {"status": "ignored", "reason": "order refunded"}

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
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        # assessment нужен ветке возврата (revoke_order_access); ленивая
        # загрузка вне async-контекста дала бы greenlet_spawn -> 500.
        .options(selectinload(Order.assessment))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ("pending", "paid") and order.tochka_operation_id:
        client = get_tochka_client()
        try:
            resp = await client.get_payment_status(order.tochka_operation_id)
            remote_status = extract_operation(resp).get("status")
            if remote_status == "APPROVED" and order.status == "pending":
                order.status = "paid"
                order.paid_at = datetime.now(timezone.utc)
                await db.commit()
            elif remote_status in REFUND_STATUSES and order.status != "refunded":
                # Единственный способ узнать о возврате из кабинета банка.
                order.status = "refunded"
                await revoke_order_access(db, order)
                await db.commit()
        except Exception:
            logger.exception("Не удалось сверить статус операции %s",
                             order.tochka_operation_id)

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
        await client.refund_payment(order.tochka_operation_id, float(order.amount))
    except Exception as e:
        # Тело ответа Точки обязательно в тексте ошибки: без него 400
        # выглядит как «Client error 400» без причины (потеряли час).
        body = getattr(getattr(e, "response", None), "text", None)
        raise HTTPException(status_code=502, detail=f"Tochka refund error: {e} | body: {body}")

    order.status = "refunded"

    revoked = await revoke_order_access(db, order)

    await db.commit()
    return {"status": "refunded",
            "revoked_assessments": revoked["assessments"],
            "revoked_followup_rights": revoked["followup_rights"]}


@router.post("/admin/reconcile")
async def reconcile_orders(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сверка заказов с банком: возвраты и недошедшие вебхуки.

    Вебхука о возврате не существует (см. комментарий к REFUND_STATUSES),
    поэтому возврат из кабинета Точки виден только здесь. Заодно
    подхватываются оплаты, чей вебхук не дошёл: банк повторяет отправку
    30 раз с интервалом 10 секунд и на этом останавливается.
    """
    rows = (await db.execute(
        select(Order)
        .where(Order.status.in_(("pending", "paid")),
               Order.tochka_operation_id.is_not(None))
        .options(selectinload(Order.assessment))
    )).scalars().all()

    client = get_tochka_client()
    marked_paid = marked_refunded = errors = 0
    for order in rows:
        try:
            resp = await client.get_payment_status(order.tochka_operation_id)
        except Exception:
            logger.exception("reconcile: нет статуса операции %s",
                             order.tochka_operation_id)
            errors += 1
            continue
        remote_status = extract_operation(resp).get("status")
        if remote_status in REFUND_STATUSES and order.status != "refunded":
            order.status = "refunded"
            await revoke_order_access(db, order)
            marked_refunded += 1
        elif remote_status == "APPROVED" and order.status == "pending":
            order.status = "paid"
            order.paid_at = datetime.now(timezone.utc)
            marked_paid += 1

    await db.commit()
    return {"checked": len(rows), "marked_paid": marked_paid,
            "marked_refunded": marked_refunded, "errors": errors}


# ── НДС: переключатель (для будущего admin UI) ──────────────────────────────
# Быстрее всего переключить прямо из консоли, без похода через HTTP/UI:
#   docker compose exec backend python3 -c \
#     "from app.tax_settings import set_vat_enabled; print(set_vat_enabled(True))"
# Эндпоинты ниже — для тех же двух действий через API/будущую кнопку в админке.

@router.get("/admin/credits-settings")
async def get_credits_settings_endpoint(
    _admin: User = Depends(require_admin),
):
    return read_credits_settings()


@router.put("/admin/credits-settings")
async def update_credits_settings_endpoint(
    enforce_credits: bool,
    _admin: User = Depends(require_admin),
):
    """Аварийный выключатель обязательной оплаты.

    Включённый флаг требует кредит или грант на создание завершённой
    диагностики и закрывает результат для черновиков. Выключение
    возвращает бесплатный доступ немедленно, без перезапуска backend.
    """
    return set_enforce_credits(enforce_credits)


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

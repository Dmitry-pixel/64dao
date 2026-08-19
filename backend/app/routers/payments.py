import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.access_grants import (
    M3_USED_STATUSES,
    grant_credits,
    nearest_expiry,
)
from app.auth import get_current_user, require_admin
from app.config import get_settings
from app.credits_settings import read_credits_settings, set_enforce_credits
from app.db import get_db
from app.m3_models import M3Portfolio
from app.models import Assessment, Order, User
from app.pricing_store import current_price, is_payment_enabled
from app.tax_settings import current_vat_type, get_tax_settings, set_vat_enabled
from app.tochka_client import extract_operation, get_tochka_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Сколько диагностик даёт один оплаченный заказ.
# Методы 1 и 2 продаются вместе: один заказ покрывает оба и повтор Метода 1.
REPORTS_PER_ORDER = 2
# Метод 3 — один портфель за заказ (решение владельца). Повтора у Метода 3
# нет, поэтому и права на него заказ не даёт.
M3_REPORTS_PER_ORDER = 1

PRODUCTS = ("m12", "m3")
DEFAULT_PRODUCT = "m12"


def reports_per_order(product: str) -> int:
    return M3_REPORTS_PER_ORDER if product == "m3" else REPORTS_PER_ORDER


def _check_product(product: str) -> str:
    if product not in PRODUCTS:
        raise HTTPException(status_code=400,
                            detail=f"Неизвестный продукт: {product}")
    return product

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
# Единица расхода Метода 3 — рассчитанный портфель (M3_USED_STATUSES из
# access_grants). Импортируется, а не объявляется второй раз: разъехавшиеся
# наборы статусов развели бы платный и грантовый контуры.


def _is_refund_event(claims: dict) -> bool:
    if str(claims.get("isRefund", "")).lower() == "true":
        return True
    return str(claims.get("status") or "").upper() in REFUND_STATUSES


async def _revoke_m3_order_access(db: AsyncSession, order: Order) -> dict:
    """Отзыв доступа по возвращённому заказу Метода 3.

    Портфели возвращаются в 'filled' — состояние «анкета заполнена, расчёта
    нет». Это и закрытие доступа к отчёту, и корректность счётчика: расход
    считается по рассчитанным портфелям, и оставленный 'calculated' портфель
    возвращённого заказа вычитался бы из кредитов будущих покупок.

    Снимок расчёта (m3_results) не удаляется: он детерминирован от ответов,
    повторный расчёт после новой оплаты его перезапишет. Удалять — значит
    терять историю без выигрыша.
    """
    rows = (await db.execute(
        select(M3Portfolio).where(M3Portfolio.order_id == order.id)
    )).scalars().all()
    closed = 0
    for portfolio in rows:
        if portfolio.status in M3_USED_STATUSES:
            portfolio.status = "filled"
            portfolio.calculated_at = None
            closed += 1
    # Ключи те же, что у контура Методов 1 и 2: вызывающий код (вебхук,
    # рефанд, сверка) один на оба продукта.
    return {"assessments": closed, "followup_rights": 0, "portfolios": closed}


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
    if order.product == "m3":
        return await _revoke_m3_order_access(db, order)

    a = order.assessment
    if a is None:
        return {"assessments": 0, "followup_rights": 0, "portfolios": 0}

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


async def pick_order(db: AsyncSession, user_id,
                     product: str = DEFAULT_PRODUCT) -> Order | None:
    """Оплаченный заказ этого продукта с непотраченным остатком — им и
    оплатится диагностика.

    Старейший первым. Аналог access_grants.pick_grant, только у платного
    кредита нет срока сгорания, поэтому порядок — по дате оплаты.

    Фильтр по продукту обязателен: без него дешёвый кредит Методов 1 и 2
    оплатил бы дорогой Метод 3.
    """
    orders = (await db.execute(
        select(Order)
        .where(Order.user_id == user_id, Order.status == "paid",
               Order.product == product)
        .order_by(func.coalesce(Order.paid_at, Order.created_at).asc(),
                  Order.id.asc())
    )).scalars().all()
    if not orders:
        return None

    order_ids = [o.id for o in orders]
    if product == "m3":
        rows = await db.execute(
            select(M3Portfolio.order_id, func.count(M3Portfolio.id))
            .where(M3Portfolio.order_id.in_(order_ids),
                   M3Portfolio.status.in_(M3_USED_STATUSES))
            .group_by(M3Portfolio.order_id)
        )
    else:
        rows = await db.execute(
            select(Assessment.order_id, func.count(Assessment.id))
            .where(Assessment.order_id.in_(order_ids),
                   Assessment.status.in_(USED_STATUSES),
                   Assessment.is_followup.is_(False))
            .group_by(Assessment.order_id)
        )
    used = {oid: cnt for oid, cnt in rows.all()}
    limit = reports_per_order(product)
    for o in orders:
        if used.get(o.id, 0) < limit:
            return o
    return None


# Цена больше НЕ хардкодится здесь — берётся из pricing.json через
# app.pricing_store (тот же источник, что у лендинга и админки "Тариф и цена").
# Раньше тут было REPORT_PRICE = 5500.00, а реальная цена на сайте — 14900 ₽:
# создание платежа ушло бы на неверную сумму.


async def paid_credits(user_id, db: AsyncSession,
                       product: str = DEFAULT_PRODUCT) -> int:
    """
    Оплаченные, но ещё не использованные диагностики одного продукта.

    Логика:
      credits = (оплаченные заказы продукта * reports_per_order)
                - использованные единицы этого продукта
    Минимум 0 — не уходим в минус.

    Балансы продуктов раздельные. Общий кошелёк при двух ценах даёт
    арбитраж: кредит Методов 1 и 2 куплен дешевле, а потратить его можно
    было бы на Метод 3.

    Общая функция: используется эндпоинтом /credits и проверкой доступа
    при создании assessment / расчёте портфеля (routers/assessments.py,
    routers/m3.py).
    """
    paid_orders = await db.scalar(
        select(func.count(Order.id))
        .where(Order.user_id == user_id, Order.status == "paid",
               Order.product == product)
    ) or 0

    if product == "m3":
        used = await db.scalar(
            select(func.count(M3Portfolio.id))
            .join(Order, Order.id == M3Portfolio.order_id)
            .where(
                Order.user_id == user_id,
                Order.status == "paid",
                M3Portfolio.status.in_(list(M3_USED_STATUSES)),
            )
        ) or 0
    else:
        used = await db.scalar(
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

    return max(0, paid_orders * reports_per_order(product) - used)


async def calculate_credits(user_id, db: AsyncSession,
                            product: str = DEFAULT_PRODUCT) -> int:
    """Все доступные диагностики продукта: оплаченные + выданные грантом.

    Имя сохранено ради существующих вызовов из routers/assessments.py.
    Там, где нужен именно платный остаток (ветка списания), вызывайте
    paid_credits(): грант списывается отдельно, через access_grants.
    """
    return (await paid_credits(user_id, db, product)
            + await grant_credits(db, user_id, product))


async def _product_breakdown(user_id, db: AsyncSession, product: str) -> dict:
    paid = await paid_credits(user_id, db, product)
    granted = await grant_credits(db, user_id, product)
    expires = await nearest_expiry(db, user_id, product)
    return {
        "credits": paid + granted,
        "paid_credits": paid,
        "grant_credits": granted,
        "grant_expires_at": expires.isoformat() if expires else None,
    }


async def credits_breakdown(user_id, db: AsyncSession) -> dict:
    """Разбивка для кабинета по обоим продуктам.

    Поля m12 продублированы на верхнем уровне: кабинет и админка читают
    credits/paid_credits/grant_credits напрямую, и ломать их отдельным
    деплоем незачем. Дубль снимается, когда фронт переедет на products.
    """
    per_product = {p: await _product_breakdown(user_id, db, p) for p in PRODUCTS}
    return {**per_product[DEFAULT_PRODUCT], "products": per_product}


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
            "product": o.product,
            # У заказов Метода 3 и у купленных заранее кредитов привязки нет:
            # str(None) вернул бы строку "None", и фронт принял бы её за id.
            "assessment_id": str(o.assessment_id) if o.assessment_id else None,
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


# Наименование услуги в чеке (54-ФЗ) — по продукту. Из pricing.json не
# берётся намеренно: заголовок тарифа правится в админке под витрину, а в
# фискальном документе должна стоять услуга, а не рекламный заголовок.
RECEIPT_NAME = {
    "m12": "Стратегическая диагностика 64 DAO",
    "m3": "Диагностика портфеля направлений 64 DAO (Метод 3)",
}


@router.post("/create")
async def create_payment(
    product: str = DEFAULT_PRODUCT,
    assessment_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создание платежа.

    Заказ — покупка кредита на продукт. Привязка к диагностике
    необязательна: из кабинета покупают заранее, до прохождения. Если
    привязка передана, она проверяется на принадлежность пользователю —
    иначе чужой id в query-параметре связал бы оплату с чужой записью.

    У Метода 3 привязки нет вовсе: обратной ссылки orders -> m3_portfolios
    в схеме нет (она образовала бы цикл внешних ключей), а списание
    отмечается на портфеле, в m3_portfolios.order_id.

    assessment_id остаётся первым необязательным параметром ради
    существующего вызова фронта /api/payments/create?assessment_id=...
    """
    _check_product(product)
    if product == "m3" and assessment_id:
        raise HTTPException(status_code=400,
                            detail="assessment_id недопустим для продукта m3")

    if not is_payment_enabled(product):
        raise HTTPException(status_code=503, detail="Payment is currently disabled")

    if assessment_id:
        owner_ok = await db.scalar(
            select(Assessment.user_id).where(Assessment.id == assessment_id))
        if owner_ok != user.id:
            raise HTTPException(status_code=404, detail="Диагностика не найдена")
    settings = get_settings()
    price = current_price(product)

    order = Order(
        user_id=user.id,
        product=product,
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
            "name": RECEIPT_NAME[product],
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
        raise HTTPException(status_code=502, detail=f"Tochka API error: {e} | body: {body}") from e

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
    product: str = DEFAULT_PRODUCT,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Тестовый платёж на 1 ₽ (не полная цена) — проверить прохождение оплаты,
    чека и вебхука через реальный Точка API без списания полной суммы.
    Доступно только администратору.

    Продукт обязателен по смыслу: у m12 и m3 разные наименования услуги
    в чеке (54-ФЗ). Пока продукт был захардкожен в 'm12', платёжный путь
    Метода 3 не проверялся живьём ни разу — при том что метод продаётся.

    Служебный Assessment больше не создаётся. Он заводился только потому,
    что Order.assessment_id считался NOT NULL; с появлением платёжного
    контура Метода 3 колонка стала nullable — у m3 привязки к диагностике
    нет вовсе. Служебная запись была мусором в таблице.

    Работает НЕЗАВИСИМО от pricing.payment_enabled — тестировать нужно
    и до включения оплаты, и после.

    ВНИМАНИЕ: оплаченный тестовый заказ засчитывается как полноценный
    кредит (paid_orders * reports_per_order), то есть рубль даёт 2 кредита
    Методов 1 и 2 либо 1 кредит Метода 3. Администратору это безразлично —
    он проходит мимо кассы, — но баланс в кабинете раздувается. Отдельного
    признака тестового заказа в схеме нет.
    """
    _check_product(product)
    settings = get_settings()

    order = Order(
        user_id=admin.id,
        product=product,
        amount=1.00,
        currency="RUB",
        status="pending",
    )
    db.add(order)
    await db.flush()

    items = [
        {
            "name": f"ТЕСТ (1 ₽): {RECEIPT_NAME[product]}",
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
            purpose=f"ТЕСТ оплаты 64 DAO ({product}), заказ {order.id}",
            order_id=str(order.id),
            customer_email=admin.email,
            items=items,
        )
    except Exception as e:
        await db.rollback()
        body = getattr(getattr(e, "response", None), "text", None)
        raise HTTPException(status_code=502, detail=f"Tochka API error: {e} | body: {body}") from e

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
        order.paid_at = datetime.now(UTC)
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
                order.paid_at = datetime.now(UTC)
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
    admin: User = Depends(require_admin),
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
        raise HTTPException(status_code=502, detail=f"Tochka refund error: {e} | body: {body}") from e

    order.status = "refunded"

    revoked = await revoke_order_access(db, order)

    await db.commit()
    # След в логах обязателен: возврат — движение денег, а таблица orders
    # хранит только итоговый статус и не помнит, кто его поставил.
    logger.info("Refund by admin %s: order %s, amount %s %s, operation %s",
                admin.email, order.id, order.amount, order.currency,
                order.tochka_operation_id)
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
            order.paid_at = datetime.now(UTC)
            marked_paid += 1

    await db.commit()
    return {"checked": len(rows), "marked_paid": marked_paid,
            "marked_refunded": marked_refunded, "errors": errors}


@router.get("/admin/orders")
async def admin_list_orders(
    status: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Все заказы с email покупателя — источник данных для кнопки возврата.

    До появления этого эндпоинта возврат существовал только как
    POST /{order_id}/refund без интерфейса, и операция выполнялась из консоли
    браузера. Для движения денег это недопустимо: ошибка в id возвращала
    средства не тому клиенту, без подтверждения и без следа в UI.

    q ищет по email покупателя и по идентификатору операции Точки. Поиск по
    id заказа не делаем: это UUID, который админ в глаза не видел, — email
    и сумма опознаются быстрее.

    can_refund считается здесь, а не на фронте: условия должны совпадать с
    проверками refund_order, иначе кнопка будет предлагать невозможное.
    """
    base = select(Order, User.email).join(User, User.id == Order.user_id)

    if status:
        base = base.where(Order.status == status)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        base = base.where(
            User.email.ilike(pattern)
            | func.coalesce(Order.tochka_operation_id, "").ilike(pattern)
        )

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar_one()

    rows = (await db.execute(
        base.order_by(Order.created_at.desc())
            .limit(max(1, min(limit, 500)))
            .offset(max(offset, 0))
    )).all()

    items = [{
        "id": str(o.id),
        "user_email": email,
        "product": o.product,
        "amount": float(o.amount),
        "currency": o.currency,
        "status": o.status,
        "tochka_operation_id": o.tochka_operation_id,
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        "created_at": o.created_at.isoformat(),
        "can_refund": o.status == "paid" and bool(o.tochka_operation_id),
    } for o, email in rows]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


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

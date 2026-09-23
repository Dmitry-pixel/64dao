# -*- coding: utf-8 -*-
"""
Метод 4 — доступ и списание.

Полная диагностика Метода 4 продаётся в одном пакете с Методом 3: один
заказ продукта m3 (или один грант m3) даёт один рассчитанный портфель
Метода 3 И один рассчитанный полный прогон Метода 4. Счётчики независимые:
пройденный Метод 3 не тратит Метод 4 и наоборот, порядок прохождения любой.

Единица расхода — полный прогон в статусе 'calculated', не повтор. Как у
Метода 3, списание стоит на расчёте: до него клиент не получил ничего,
что стоит денег. Экспресс бесплатный и не списывает ничего.

Приоритет тот же, что в m3_access: сначала грант (сгорает по сроку), потом
платный заказ (не сгорает). Администратор и выключенный флаг оплаты
проходят без списания.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.credits_settings import enforce_credits_enabled
from app.m4_models import M4Run
from app.models import AccessGrant, Order, User

PRODUCT = "m3"
USED_STATUSES = ("calculated",)

NO_CREDITS = ("Нет доступных полных диагностик Метода 4. Они входят в пакет "
              "«Метод 3 + Метод 4» — оплатите пакет, чтобы получить доступ.")
NOT_PAID = "Отчёт недоступен: диагностика не оплачена или оплата возвращена."


def free_pass(user: User) -> bool:
    return not enforce_credits_enabled() or user.role == "admin"


def _used_filter():
    return (M4Run.mode == "full", M4Run.status.in_(USED_STATUSES), M4Run.is_followup.is_(False))


async def used_by_orders(db: AsyncSession, order_ids: list[uuid.UUID]) -> dict:
    if not order_ids:
        return {}
    rows = await db.execute(
        select(M4Run.order_id, func.count(M4Run.id))
        .where(M4Run.order_id.in_(order_ids), *_used_filter())
        .group_by(M4Run.order_id)
    )
    return {oid: cnt for oid, cnt in rows.all()}


async def used_by_grants(db: AsyncSession, grant_ids: list[uuid.UUID]) -> dict:
    if not grant_ids:
        return {}
    rows = await db.execute(
        select(M4Run.grant_id, func.count(M4Run.id))
        .where(M4Run.grant_id.in_(grant_ids), *_used_filter())
        .group_by(M4Run.grant_id)
    )
    return {gid: cnt for gid, cnt in rows.all()}


async def pick_grant(db: AsyncSession, user_id) -> AccessGrant | None:
    """Действующий грант m3 с непотраченной квотой Метода 4; ближайший к
    истечению первым."""
    now = datetime.now(UTC)
    grants = (await db.execute(
        select(AccessGrant).where(
            AccessGrant.user_id == user_id, AccessGrant.product == PRODUCT,
            AccessGrant.revoked_at.is_(None),
            AccessGrant.starts_at <= now, AccessGrant.expires_at > now,
        ).order_by(AccessGrant.expires_at.asc())
    )).scalars().all()
    used = await used_by_grants(db, [g.id for g in grants])
    for g in grants:
        if used.get(g.id, 0) < g.quota:
            return g
    return None


async def pick_order(db: AsyncSession, user_id) -> Order | None:
    """Оплаченный заказ пакета с непотраченным Методом 4; старейший первым."""
    from app.routers.payments import reports_per_order  # тянет клиент банка — не на старте

    orders = (await db.execute(
        select(Order)
        .where(Order.user_id == user_id, Order.status == "paid", Order.product == PRODUCT)
        .order_by(func.coalesce(Order.paid_at, Order.created_at).asc(), Order.id.asc())
    )).scalars().all()
    used = await used_by_orders(db, [o.id for o in orders])
    limit = reports_per_order(PRODUCT)
    for o in orders:
        if used.get(o.id, 0) < limit:
            return o
    return None


async def credits(db: AsyncSession, user: User) -> int | None:
    """Сколько полных диагностик Метода 4 доступно. None — без ограничения."""
    if free_pass(user):
        return None
    from app.routers.payments import reports_per_order

    now = datetime.now(UTC)
    grants = (await db.execute(
        select(AccessGrant).where(
            AccessGrant.user_id == user.id, AccessGrant.product == PRODUCT,
            AccessGrant.revoked_at.is_(None),
            AccessGrant.starts_at <= now, AccessGrant.expires_at > now,
        )
    )).scalars().all()
    g_used = await used_by_grants(db, [g.id for g in grants])
    total = sum(max(0, g.quota - g_used.get(g.id, 0)) for g in grants)
    orders = (await db.execute(
        select(Order).where(Order.user_id == user.id, Order.status == "paid", Order.product == PRODUCT)
    )).scalars().all()
    o_used = await used_by_orders(db, [o.id for o in orders])
    limit = reports_per_order(PRODUCT)
    return total + sum(max(0, limit - o_used.get(o.id, 0)) for o in orders)


async def reserve_payment(db: AsyncSession, run: M4Run, user: User) -> tuple[AccessGrant | None, Order | None]:
    """Чем оплатить расчёт. Только выбирает — привязка после успешного
    расчёта (attach_payment), чтобы ошибка анкеты не съела кредит.

    Прогон, уже привязанный к оплате (расчёт после возврата и новой оплаты
    идёт через новую привязку), второй раз не списывает."""
    if run.mode != "full" or run.is_followup or free_pass(user) or run.order_id or run.grant_id:
        return None, None
    grant = await pick_grant(db, user.id)
    if grant is not None:
        return grant, None
    order = await pick_order(db, user.id)
    if order is None:
        raise HTTPException(status_code=403, detail=NO_CREDITS)
    return None, order


def attach_payment(run: M4Run, grant: AccessGrant | None, order: Order | None) -> None:
    if grant is not None:
        run.grant_id = grant.id
    if order is not None:
        run.order_id = order.id


def ensure_result_access(run: M4Run, user: User) -> None:
    """Результат есть только у рассчитанного прогона. Возврат заказа
    переводит прогон в 'filled' — эта проверка и закрывает отчёт."""
    if run.status != "calculated":
        raise HTTPException(status_code=403, detail=NOT_PAID)


async def revoke_order_runs(db: AsyncSession, order: Order) -> int:
    """Возврат заказа пакета: полные прогоны Метода 4 этого заказа — в
    'filled'. Снимок не удаляется: после новой оплаты расчёт его перепишет."""
    rows = (await db.execute(select(M4Run).where(M4Run.order_id == order.id))).scalars().all()
    closed = 0
    for run in rows:
        if run.status in USED_STATUSES:
            run.status = "filled"
            run.calculated_at = None
            # Привязку снимаем: иначе reserve_payment счёл бы прогон
            # оплаченным и пересчитал бы его без новой оплаты.
            run.order_id = None
            closed += 1
    return closed

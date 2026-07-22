# -*- coding: utf-8 -*-
"""
Подписка на раздел «Динамика» (роадмап 3.1).

Единый источник проверки доступа: is_active(session, user_id). Не дублировать
проверку по роутерам (правило проекта). Подписка — на аккаунт пользователя
(§0.3). Статус 'expired' проставляется лениво при проверке.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription
from app.config import get_settings

settings = get_settings()


def _period_days(days: int | None = None) -> int:
    return int(days) if days else int(getattr(settings, "subscription_period_days", 365))


async def _expire_stale(session: AsyncSession, user_id) -> None:
    """Ленивое протухание: активные с истёкшим ends_at → 'expired'."""
    now = datetime.now(timezone.utc)
    await session.execute(
        update(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.ends_at <= now,
        )
        .values(status="expired")
    )


async def _current(session: AsyncSession, user_id) -> Subscription | None:
    await _expire_stale(session, user_id)
    now = datetime.now(timezone.utc)
    return await session.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.ends_at > now,
        )
        .order_by(Subscription.ends_at.desc())
    )


async def is_active(session: AsyncSession, user_id) -> bool:
    return (await _current(session, user_id)) is not None


async def status_for(session: AsyncSession, user_id) -> dict:
    sub = await _current(session, user_id)
    return {
        "active": sub is not None,
        "starts_at": sub.starts_at if sub else None,
        "ends_at": sub.ends_at if sub else None,
    }


async def grant(session: AsyncSession, user_id, days: int | None = None,
                order_id=None) -> Subscription:
    """Выдать подписку (ручная выдача админом при order_id=None)."""
    now = datetime.now(timezone.utc)
    sub = Subscription(
        user_id=user_id,
        order_id=order_id,
        starts_at=now,
        ends_at=now + timedelta(days=_period_days(days)),
        status="active",
    )
    session.add(sub)
    await session.flush()
    return sub


async def revoke(session: AsyncSession, user_id) -> int:
    """Отозвать все активные подписки пользователя. Возвращает число отозванных."""
    res = await session.execute(
        update(Subscription)
        .where(Subscription.user_id == user_id, Subscription.status == "active")
        .values(status="revoked")
    )
    return res.rowcount or 0

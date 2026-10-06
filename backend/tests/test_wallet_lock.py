# -*- coding: utf-8 -*-
"""Блокировка кошелька при списании (аудит 2026-10-06, R002).

Сценарий: оплачен один заказ Методов 1-2 (2 диагностики), одна уже
использована. Два запроса одновременно тратят последнюю. Без блокировки оба
видят остаток 1 и оба привязывают диагностику к заказу: 3 диагностики за
заказ на 2. С блокировкой второй ждёт первого и видит остаток 0.

Тест работает на настоящих параллельных транзакциях: общий db_session из
conftest живёт на одном соединении и гонку не воспроизводит.
"""
import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Assessment, Order, User
from app.routers.payments import REPORTS_PER_ORDER, pick_order
from app.wallet_lock import lock_wallet
from tests.conftest import test_engine

Session = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


async def _seed() -> tuple[uuid.UUID, uuid.UUID]:
    async with Session() as s:
        user = User(email=f"wallet-{uuid.uuid4().hex[:8]}@example.com", role="user")
        s.add(user)
        await s.flush()
        order = Order(user_id=user.id, product="m12", amount=14900, currency="RUB",
                      status="paid", paid_at=datetime.now(UTC))
        s.add(order)
        await s.flush()
        # Оплачено REPORTS_PER_ORDER, использованы все, кроме одной.
        for _ in range(REPORTS_PER_ORDER - 1):
            s.add(Assessment(user_id=user.id, status="completed", order_id=order.id))
        await s.commit()
        return user.id, order.id


async def _consume(user_id, use_lock: bool) -> bool:
    """Одна попытка потратить диагностику. True — списано."""
    async with Session() as s:
        if use_lock:
            await lock_wallet(s, user_id, "m12")
        order = await pick_order(s, user_id, "m12")
        if order is None:
            await s.rollback()
            return False
        # Окно гонки: между чтением остатка и записью привязки.
        await asyncio.sleep(0.3)
        s.add(Assessment(user_id=user_id, status="completed", order_id=order.id))
        await s.commit()
        return True


async def _used(order_id) -> int:
    async with Session() as s:
        return await s.scalar(select(func.count(Assessment.id))
                              .where(Assessment.order_id == order_id))


@pytest.mark.asyncio
async def test_parallel_consume_without_lock_overdraws(setup_test_database):
    """Контрольный тест: гонка реальна, без блокировки остаток уходит в минус."""
    user_id, order_id = await _seed()
    results = await asyncio.gather(_consume(user_id, False), _consume(user_id, False))
    assert results == [True, True]
    assert await _used(order_id) == REPORTS_PER_ORDER + 1


@pytest.mark.asyncio
async def test_parallel_consume_with_lock_spends_once(setup_test_database):
    user_id, order_id = await _seed()
    results = await asyncio.gather(_consume(user_id, True), _consume(user_id, True))
    assert sorted(results) == [False, True]
    assert await _used(order_id) == REPORTS_PER_ORDER


@pytest.mark.asyncio
async def test_lock_is_per_user(setup_test_database):
    """Блокировка одного пользователя не задерживает другого."""
    a, _ = await _seed()
    b, _ = await _seed()
    async with Session() as s1, Session() as s2:
        await lock_wallet(s1, a, "m12")
        await asyncio.wait_for(lock_wallet(s2, b, "m12"), timeout=2)
        await s1.rollback()
        await s2.rollback()


@pytest.mark.asyncio
async def test_unknown_wallet_rejected(setup_test_database):
    async with Session() as s:
        with pytest.raises(ValueError):
            await lock_wallet(s, uuid.uuid4(), "m5")

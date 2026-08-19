"""Досверка зависших pending-заказов (app/jobs/reconcile_pending.py).

Сеть не участвует: клиент Точки подменяется моком. Проверяется ровно то,
из-за чего задача и появилась — оплата, о которой вебхук не доехал, не
должна оставаться pending, а брошенная корзина не должна дёргать банк.
"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

import app.jobs.reconcile_pending as job
from app.models import Assessment, Order
from app.routers.payments import paid_credits


async def _make_order(db, user, *, age_minutes: int, status="pending",
                      operation_id=None) -> Order:
    assessment = Assessment(user_id=user.id, status="completed",
                            method1_combination="AAABAA")
    db.add(assessment)
    await db.flush()
    order = Order(
        user_id=user.id, product="m12", assessment_id=assessment.id,
        amount=14900.00, currency="RUB", status=status,
        tochka_operation_id=operation_id or f"op-{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(UTC) - timedelta(minutes=age_minutes),
    )
    db.add(order)
    await db.flush()
    return order


def _client(status="APPROVED"):
    client = AsyncMock()
    client.get_payment_status = AsyncMock(
        return_value={"Data": {"Operation": [{"status": status}]}}
    )
    return client


@pytest.mark.asyncio
async def test_stale_pending_becomes_paid(db_session, test_user, monkeypatch):
    """Банк подтверждает оплату — заказ обязан закрыться без участия админа."""
    order = await _make_order(db_session, test_user, age_minutes=60)
    monkeypatch.setattr(job, "get_tochka_client", lambda: _client("APPROVED"))

    stats = await job.reconcile_pending(db_session)

    await db_session.refresh(order)
    assert order.status == "paid"
    assert order.paid_at is not None
    assert stats["marked_paid"] == 1


@pytest.mark.asyncio
async def test_fresh_order_is_left_alone(db_session, test_user, monkeypatch):
    """Свежий заказ ещё может закрыться штатным вебхуком — банк не дёргаем."""
    order = await _make_order(db_session, test_user, age_minutes=1)
    client = _client("APPROVED")
    monkeypatch.setattr(job, "get_tochka_client", lambda: client)

    stats = await job.reconcile_pending(db_session)

    await db_session.refresh(order)
    assert order.status == "pending"
    assert stats["checked"] == 0
    client.get_payment_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_ancient_order_is_left_alone(db_session, test_user, monkeypatch):
    """За горизонтом MAX_AGE_DAYS pending — это брошенная корзина."""
    order = await _make_order(db_session, test_user,
                              age_minutes=60 * 24 * (job.MAX_AGE_DAYS + 1))
    client = _client("APPROVED")
    monkeypatch.setattr(job, "get_tochka_client", lambda: client)

    stats = await job.reconcile_pending(db_session)

    await db_session.refresh(order)
    assert order.status == "pending"
    assert stats["checked"] == 0
    client.get_payment_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejected_order_becomes_failed(db_session, test_user, monkeypatch):
    order = await _make_order(db_session, test_user, age_minutes=60)
    monkeypatch.setattr(job, "get_tochka_client", lambda: _client("REJECTED"))

    stats = await job.reconcile_pending(db_session)

    await db_session.refresh(order)
    assert order.status == "failed"
    assert stats["marked_failed"] == 1


@pytest.mark.asyncio
async def test_one_failing_order_does_not_block_the_rest(db_session, test_user, monkeypatch):
    """Сбой по одному заказу не должен уносить остальные: иначе первая же
    ошибка API оставляла бы весь хвост очереди неразобранным."""
    bad = await _make_order(db_session, test_user, age_minutes=60, operation_id="op-bad")
    good = await _make_order(db_session, test_user, age_minutes=60, operation_id="op-good")

    client = AsyncMock()

    async def status_by_operation(operation_id):
        if operation_id == "op-bad":
            raise RuntimeError("tochka 500")
        return {"Data": {"Operation": [{"status": "APPROVED"}]}}

    client.get_payment_status = AsyncMock(side_effect=status_by_operation)
    monkeypatch.setattr(job, "get_tochka_client", lambda: client)

    stats = await job.reconcile_pending(db_session)

    await db_session.refresh(bad)
    await db_session.refresh(good)
    assert bad.status == "pending"
    assert good.status == "paid"
    assert stats["errors"] == 1
    assert stats["marked_paid"] == 1


@pytest.mark.asyncio
async def test_recovered_order_restores_access(db_session, test_user, monkeypatch):
    """Смысл всей задачи: после сверки клиент получает то, что оплатил.

    Кредиты не хранятся отдельной записью, а считаются по оплаченным
    заказам, поэтому незакрытый статус — это ровно один неоткрытый отчёт.
    """
    await _make_order(db_session, test_user, age_minutes=60)
    assert await paid_credits(test_user.id, db_session) == 0

    monkeypatch.setattr(job, "get_tochka_client", lambda: _client("APPROVED"))
    await job.reconcile_pending(db_session)

    assert await paid_credits(test_user.id, db_session) > 0

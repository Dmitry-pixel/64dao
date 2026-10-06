# -*- coding: utf-8 -*-
"""Журнал действий администратора и истории статусов заказов
(аудит 2026-10-06, R015, R006)."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit_models import AuditEvent
from app.models import Order
from tests.conftest import test_engine

Session = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


async def _admin_events() -> list[AuditEvent]:
    # Middleware пишет в собственной транзакции, мимо db_session теста.
    async with Session() as s:
        return list((await s.execute(
            select(AuditEvent).where(AuditEvent.kind == "admin")
            .order_by(AuditEvent.created_at))).scalars())


@pytest.mark.asyncio
async def test_admin_mutation_is_logged_with_body(admin_client, test_admin):
    resp = await admin_client.put("/api/admin/pricing", json={"m12": {"price": 15000}})
    assert resp.status_code == 200
    events = await _admin_events()
    assert len(events) == 1
    e = events[0]
    assert e.action == "PUT /api/admin/pricing"
    assert e.actor_email == test_admin.email
    assert e.status_code == 200
    assert e.after["body"] == {"m12": {"price": 15000}}


@pytest.mark.asyncio
async def test_secret_body_is_not_logged(admin_client):
    await admin_client.put("/api/admin/tochka-settings", json={"jwt_token": "secret-token-value"})
    events = await _admin_events()
    assert len(events) == 1
    assert "secret-token-value" not in str(events[0].after)


@pytest.mark.asyncio
async def test_path_param_becomes_entity(admin_client, test_user):
    resp = await admin_client.post(f"/api/admin/users/{test_user.id}/revoke-sessions")
    assert resp.status_code == 200
    e = (await _admin_events())[0]
    assert e.action == "POST /api/admin/users/{user_id}/revoke-sessions"
    assert (e.entity_type, e.entity_id) == ("user", str(test_user.id))


@pytest.mark.asyncio
async def test_regular_user_actions_not_logged(auth_client):
    await auth_client.put("/api/auth/profile", json={"full_name": "Имя", "company_name": ""})
    assert await _admin_events() == []


@pytest.mark.asyncio
async def test_reads_not_logged(admin_client):
    await admin_client.get("/api/admin/pricing")
    assert await _admin_events() == []


@pytest.mark.asyncio
async def test_order_status_history(db_session, test_user):
    o = Order(user_id=test_user.id, product="m12", amount=14900, currency="RUB", status="pending")
    db_session.add(o)
    await db_session.flush()
    o.status = "paid"
    o._status_source = "webhook"
    await db_session.flush()
    o.status = "refunded"
    o._status_source = "admin_refund"
    await db_session.flush()

    events = (await db_session.execute(
        select(AuditEvent).where(AuditEvent.entity_id == str(o.id))
        .order_by(AuditEvent.created_at, AuditEvent.id))).scalars().all()
    by_status = {e.after["status"]: e for e in events}
    assert set(by_status) == {"pending", "paid", "refunded"}
    assert by_status["paid"].before == {"status": "pending"}
    assert by_status["paid"].note == "webhook"
    assert by_status["refunded"].note == "admin_refund"


@pytest.mark.asyncio
async def test_audit_endpoint_lists_order_events_with_email(admin_client, db_session, test_user):
    o = Order(user_id=test_user.id, product="m12", amount=14900, currency="RUB", status="pending")
    db_session.add(o)
    await db_session.flush()
    resp = await admin_client.get("/api/admin/audit?kind=order")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["order"]["user_email"] == test_user.email
    assert items[0]["after"]["status"] == "pending"


@pytest.mark.asyncio
async def test_audit_endpoint_requires_admin(auth_client):
    resp = await auth_client.get("/api/admin/audit")
    assert resp.status_code == 403

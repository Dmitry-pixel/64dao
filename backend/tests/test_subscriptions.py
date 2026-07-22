# -*- coding: utf-8 -*-
"""
Подписка на «Динамику» (роадмап 3.1, PR1): сервис доступа + админ-выдача.
"""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select

from app.models import User, Subscription
from app import subscription_service as subs


async def _mk_user(db) -> User:
    u = User(email=f"sub-{uuid.uuid4()}@t.t", role="user")
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_grant_makes_active(db_session):
    u = await _mk_user(db_session)
    assert await subs.is_active(db_session, u.id) is False
    await subs.grant(db_session, u.id, days=30)
    assert await subs.is_active(db_session, u.id) is True
    st = await subs.status_for(db_session, u.id)
    assert st["active"] is True and st["ends_at"] is not None


@pytest.mark.asyncio
async def test_default_period_from_settings(db_session):
    u = await _mk_user(db_session)
    sub = await subs.grant(db_session, u.id)  # без days → период по умолчанию
    span = (sub.ends_at - sub.starts_at).days
    assert span >= 364  # 365 ± округление


@pytest.mark.asyncio
async def test_expired_lazily_flips_status(db_session):
    u = await _mk_user(db_session)
    sub = await subs.grant(db_session, u.id, days=30)
    sub.ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.flush()
    assert await subs.is_active(db_session, u.id) is False
    refreshed = await db_session.scalar(select(Subscription).where(Subscription.id == sub.id))
    assert refreshed.status == "expired"


@pytest.mark.asyncio
async def test_revoke_closes_access(db_session):
    u = await _mk_user(db_session)
    await subs.grant(db_session, u.id, days=30)
    n = await subs.revoke(db_session, u.id)
    assert n == 1
    assert await subs.is_active(db_session, u.id) is False


@pytest.mark.asyncio
async def test_admin_grant_status_revoke(admin_client, db_session):
    u = await _mk_user(db_session)
    r = await admin_client.post(f"/api/admin/users/{u.id}/subscription", json={"days": 30})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"

    s = await admin_client.get(f"/api/admin/users/{u.id}/subscription")
    assert s.json()["active"] is True

    d = await admin_client.delete(f"/api/admin/users/{u.id}/subscription")
    assert d.json()["revoked"] >= 1

    s2 = await admin_client.get(f"/api/admin/users/{u.id}/subscription")
    assert s2.json()["active"] is False


@pytest.mark.asyncio
async def test_admin_grant_unknown_user_404(admin_client):
    r = await admin_client.post(f"/api/admin/users/{uuid.uuid4()}/subscription", json={})
    assert r.status_code == 404

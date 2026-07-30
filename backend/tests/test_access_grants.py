# -*- coding: utf-8 -*-
"""test_access_grants.py — временный бесплатный доступ (партнёрские гранты).

Проверяется два контура: списание при создании диагностики (квота, срок,
отзыв, приоритет сгорающего гранта, независимость от платных кредитов) и
админский API выдачи/отзыва/переотправки письма.

Письмо мокается: реальный SMTP в тестах не нужен, а сбой отправки — часть
контракта (грант не откатывается).
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

import app.email as app_email
import app.routers.assessments as assessments_router
from app.models import AccessGrant, Assessment, Order

VALID_COMBINATION = "AABABA"
FINANCE_ANSWERS = {f"{b}.{p}": 3 for b in range(1, 7) for p in range(1, 5)}


def payload(**overrides) -> dict:
    body = {
        "method1_answers": {"goal": "A", "strategy": "B"},
        "method1_combination": VALID_COMBINATION,
        "method2_data": None,
        "finance_answers": FINANCE_ANSWERS,
        "company_name": "Партнёр",
        "status": "completed",
    }
    body.update(overrides)
    return body


@pytest.fixture
def enforce_credits_on(monkeypatch):
    # Флаг читается из credits_settings.py, а не из Settings: подменяем
    # функцию, иначе тест молча работал бы вхолостую.
    monkeypatch.setattr(assessments_router, "enforce_credits_enabled", lambda: True)


@pytest.fixture
def mock_grant_email(monkeypatch):
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(app_email, "send_access_grant_email", mock)
    return mock


async def _grant(db, user, quota=1, days=14, starts_in_days=0, revoked=False):
    now = datetime.now(timezone.utc)
    grant = AccessGrant(
        user_id=user.id,
        quota=quota,
        starts_at=now + timedelta(days=starts_in_days),
        expires_at=now + timedelta(days=days),
        reason="Пилот партнёра",
        revoked_at=now if revoked else None,
    )
    db.add(grant)
    await db.flush()
    return grant


async def _paid_order(db, user):
    """orders.assessment_id NOT NULL: заказ невозможен без диагностики.
    Заполнитель держим в draft — он не считается израсходованным ни в
    платном, ни в грантовом контуре."""
    filler = Assessment(user_id=user.id, method1_combination=VALID_COMBINATION,
                        status="draft", company_name="Оплаченная")
    db.add(filler)
    await db.flush()
    order = Order(user_id=user.id, assessment_id=filler.id, amount=14900.00,
                  currency="RUB", status="paid")
    db.add(order)
    await db.flush()
    return order


# ── Списание гранта ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_active_grant_allows_completed(auth_client, db_session, test_user, enforce_credits_on):
    grant = await _grant(db_session, test_user)
    resp = await auth_client.post("/api/assessments", json=payload())
    assert resp.status_code == 200
    saved = await db_session.scalar(
        select(Assessment).where(Assessment.id == resp.json()["id"]))
    assert saved.grant_id == grant.id


@pytest.mark.asyncio
async def test_grant_quota_exhausted_blocks(auth_client, db_session, test_user, enforce_credits_on):
    await _grant(db_session, test_user, quota=1)
    first = await auth_client.post("/api/assessments", json=payload())
    assert first.status_code == 200
    second = await auth_client.post("/api/assessments", json=payload())
    assert second.status_code == 403


@pytest.mark.asyncio
async def test_expired_grant_blocks(auth_client, db_session, test_user, enforce_credits_on):
    await _grant(db_session, test_user, quota=5, days=-1, starts_in_days=-10)
    resp = await auth_client.post("/api/assessments", json=payload())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_revoked_grant_blocks(auth_client, db_session, test_user, enforce_credits_on):
    await _grant(db_session, test_user, quota=5, revoked=True)
    resp = await auth_client.post("/api/assessments", json=payload())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_pending_grant_blocks(auth_client, db_session, test_user, enforce_credits_on):
    await _grant(db_session, test_user, quota=5, starts_in_days=1, days=30)
    resp = await auth_client.post("/api/assessments", json=payload())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_nearest_expiry_spent_first(auth_client, db_session, test_user, enforce_credits_on):
    soon = await _grant(db_session, test_user, quota=1, days=3)
    await _grant(db_session, test_user, quota=1, days=30)
    resp = await auth_client.post("/api/assessments", json=payload())
    assert resp.status_code == 200
    saved = await db_session.scalar(
        select(Assessment).where(Assessment.id == resp.json()["id"]))
    assert saved.grant_id == soon.id


@pytest.mark.asyncio
async def test_grant_does_not_consume_paid_credits(auth_client, db_session, test_user, enforce_credits_on):
    await _paid_order(db_session, test_user)      # 2 платных кредита
    await _grant(db_session, test_user, quota=1)
    resp = await auth_client.post("/api/assessments", json=payload())
    assert resp.status_code == 200
    credits = (await auth_client.get("/api/payments/credits")).json()
    assert credits["paid_credits"] == 2
    assert credits["grant_credits"] == 0


@pytest.mark.asyncio
async def test_grant_assessment_gets_no_followup_right(auth_client, db_session, test_user, enforce_credits_on):
    await _grant(db_session, test_user, quota=1)
    resp = await auth_client.post("/api/assessments", json=payload())
    saved = await db_session.scalar(
        select(Assessment).where(Assessment.id == resp.json()["id"]))
    assert saved.followup_allowed == 0


@pytest.mark.asyncio
async def test_paid_assessment_keeps_followup_right(auth_client, db_session, test_user, enforce_credits_on):
    await _paid_order(db_session, test_user)
    resp = await auth_client.post("/api/assessments", json=payload())
    assert resp.status_code == 200
    saved = await db_session.scalar(
        select(Assessment).where(Assessment.id == resp.json()["id"]))
    assert saved.grant_id is None
    assert saved.followup_allowed == 1


@pytest.mark.asyncio
async def test_refund_to_draft_returns_quota(auth_client, db_session, test_user, enforce_credits_on):
    await _grant(db_session, test_user, quota=1)
    resp = await auth_client.post("/api/assessments", json=payload())
    saved = await db_session.scalar(
        select(Assessment).where(Assessment.id == resp.json()["id"]))
    saved.status = "draft"
    await db_session.flush()
    credits = (await auth_client.get("/api/payments/credits")).json()
    assert credits["grant_credits"] == 1


@pytest.mark.asyncio
async def test_credits_breakdown_shape(auth_client, db_session, test_user):
    await _grant(db_session, test_user, quota=2, days=7)
    body = (await auth_client.get("/api/payments/credits")).json()
    assert set(body) == {"credits", "paid_credits", "grant_credits", "grant_expires_at"}
    assert body["grant_credits"] == 2
    assert body["grant_expires_at"] is not None


# ── Админский API ─────────────────────────────────────────────────────────────

def _create_body(days=14, quota=2, notify=True):
    return {
        "quota": quota,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(),
        "reason": "Перспективный партнёр, тест",
        "notify": notify,
    }


@pytest.mark.asyncio
async def test_admin_creates_grant_and_notifies(admin_client, db_session, test_user, mock_grant_email):
    resp = await admin_client.post(
        f"/api/admin/users/{test_user.id}/access-grants", json=_create_body())
    assert resp.status_code == 201
    body = resp.json()
    assert body["quota"] == 2
    assert body["remaining"] == 2
    assert body["status"] == "active"
    assert body["user_email"] == test_user.email
    assert body["email_sent_at"] is not None
    mock_grant_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_smtp_failure_does_not_rollback_grant(admin_client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(app_email, "send_access_grant_email",
                        AsyncMock(side_effect=RuntimeError("smtp down")))
    resp = await admin_client.post(
        f"/api/admin/users/{test_user.id}/access-grants", json=_create_body())
    assert resp.status_code == 201
    assert resp.json()["email_sent_at"] is None
    count = await db_session.scalar(
        select(AccessGrant).where(AccessGrant.user_id == test_user.id))
    assert count is not None


@pytest.mark.asyncio
async def test_create_grant_past_date_rejected(admin_client, test_user, mock_grant_email):
    resp = await admin_client.post(
        f"/api/admin/users/{test_user.id}/access-grants", json=_create_body(days=-1))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_grant_requires_admin(auth_client, test_user, mock_grant_email):
    resp = await auth_client.post(
        f"/api/admin/users/{test_user.id}/access-grants", json=_create_body())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_revoke_then_revoke_again_conflicts(admin_client, db_session, test_user):
    grant = await _grant(db_session, test_user, quota=3)
    first = await admin_client.post(f"/api/admin/access-grants/{grant.id}/revoke")
    assert first.status_code == 200
    assert first.json()["status"] == "revoked"
    second = await admin_client.post(f"/api/admin/access-grants/{grant.id}/revoke")
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_list_active_hides_expired_and_revoked(admin_client, db_session, test_user):
    await _grant(db_session, test_user, quota=2, days=10)
    await _grant(db_session, test_user, quota=2, days=-1, starts_in_days=-5)
    await _grant(db_session, test_user, quota=2, days=10, revoked=True)
    all_items = (await admin_client.get("/api/admin/access-grants")).json()
    active = (await admin_client.get("/api/admin/access-grants?status=active")).json()
    assert len(all_items) == 3
    assert len(active) == 1
    assert active[0]["status"] == "active"


@pytest.mark.asyncio
async def test_notify_revoked_grant_rejected(admin_client, db_session, test_user, mock_grant_email):
    grant = await _grant(db_session, test_user, quota=2, revoked=True)
    resp = await admin_client.post(f"/api/admin/access-grants/{grant.id}/notify")
    assert resp.status_code == 400
    mock_grant_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_user_grants_list_returns_own_only(admin_client, db_session, test_user, test_admin):
    await _grant(db_session, test_user, quota=1)
    await _grant(db_session, test_admin, quota=1)
    items = (await admin_client.get(f"/api/admin/users/{test_user.id}/access-grants")).json()
    assert len(items) == 1
    assert items[0]["user_id"] == str(test_user.id)

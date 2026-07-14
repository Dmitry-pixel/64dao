"""
test_payments.py — smoke-тесты платёжного роутера (routers/payments.py).

Внешний API Точки НЕ вызывается: get_tochka_client подменяется моком
(fixture mock_tochka), поэтому тесты детерминированы и не ходят в сеть.
Так же подменяются pricing-хелперы (is_payment_enabled/current_price),
чтобы не зависеть от pricing.json в volume.
"""
import uuid
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

import app.routers.payments as payments_router
from app.models import Assessment, Order


@pytest.fixture
def mock_tochka(monkeypatch):
    tochka = AsyncMock()
    tochka.create_payment_with_receipt = AsyncMock(return_value={
        "Data": {"operationId": "op-test-123", "paymentLink": "https://pay.tochka.test/abc"}
    })
    tochka.get_payment_status = AsyncMock(return_value={"Data": {"status": "APPROVED"}})
    tochka.refund_payment = AsyncMock(return_value={"Data": {"status": "REFUNDED"}})
    tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": "op-test-123", "status": "APPROVED"}
    )
    monkeypatch.setattr(payments_router, "get_tochka_client", lambda: tochka)
    return tochka


@pytest.fixture
def payment_enabled(monkeypatch):
    monkeypatch.setattr(payments_router, "is_payment_enabled", lambda: True)
    monkeypatch.setattr(payments_router, "current_price", lambda: 14900.0)


async def _make_assessment(db, user, status="completed", combination="AAABAA"):
    a = Assessment(user_id=user.id, method1_combination=combination, status=status, company_name="Test Co")
    db.add(a)
    await db.flush()
    return a


async def _make_order(db, user, assessment, status="pending", operation_id="op-test-123"):
    o = Order(user_id=user.id, assessment_id=assessment.id, amount=14900.00,
              currency="RUB", status=status, tochka_operation_id=operation_id)
    db.add(o)
    await db.flush()
    return o


@pytest.mark.asyncio
async def test_create_payment_disabled_returns_503(auth_client, monkeypatch):
    monkeypatch.setattr(payments_router, "is_payment_enabled", lambda: False)
    resp = await auth_client.post("/api/payments/create", params={"assessment_id": str(uuid.uuid4())})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_create_payment_requires_auth(client, payment_enabled):
    resp = await client.post("/api/payments/create", params={"assessment_id": str(uuid.uuid4())})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_payment_success(auth_client, db_session, test_user, mock_tochka, payment_enabled):
    assessment = await _make_assessment(db_session, test_user)
    resp = await auth_client.post("/api/payments/create", params={"assessment_id": str(assessment.id)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["payment_link"] == "https://pay.tochka.test/abc"
    assert "order_id" in body
    mock_tochka.create_payment_with_receipt.assert_awaited_once()
    order = await db_session.get(Order, uuid.UUID(body["order_id"]))
    assert order is not None
    assert order.status == "pending"
    assert order.tochka_operation_id == "op-test-123"


@pytest.mark.asyncio
async def test_webhook_invalid_signature_ignored(client, mock_tochka):
    mock_tochka.verify_and_decode_webhook = AsyncMock(side_effect=ValueError("bad sig"))
    resp = await client.post("/api/payments/webhook", content=b"garbage")
    assert resp.status_code == 200
    assert resp.json()["reason"] == "invalid signature"


@pytest.mark.asyncio
async def test_webhook_order_not_found_ignored(client, mock_tochka):
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": "op-nonexistent", "status": "APPROVED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["reason"] == "order not found"


@pytest.mark.asyncio
async def test_webhook_approved_marks_order_paid(client, db_session, test_user, mock_tochka):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="pending")
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": order.tochka_operation_id, "status": "APPROVED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    await db_session.refresh(order)
    assert order.status == "paid"
    assert order.paid_at is not None


@pytest.mark.asyncio
async def test_webhook_idempotent_when_already_paid(client, db_session, test_user, mock_tochka):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="paid")
    mock_tochka.verify_and_decode_webhook = AsyncMock(
        return_value={"operationId": order.tochka_operation_id, "status": "APPROVED"}
    )
    resp = await client.post("/api/payments/webhook", content=b"jwt")
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_processed"


@pytest.mark.asyncio
async def test_status_returns_order_status(auth_client, db_session, test_user):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="paid")
    resp = await auth_client.get(f"/api/payments/{order.id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_status_only_owner(auth_client, db_session, test_admin):
    assessment = await _make_assessment(db_session, test_admin)
    order = await _make_order(db_session, test_admin, assessment, status="paid")
    resp = await auth_client.get(f"/api/payments/{order.id}/status")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_refund_requires_admin(auth_client, db_session, test_user):
    assessment = await _make_assessment(db_session, test_user)
    order = await _make_order(db_session, test_user, assessment, status="paid")
    resp = await auth_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_refund_non_paid_returns_400(admin_client, db_session, test_admin, mock_tochka):
    assessment = await _make_assessment(db_session, test_admin)
    order = await _make_order(db_session, test_admin, assessment, status="pending")
    resp = await admin_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_refund_success_resets_assessment(admin_client, db_session, test_admin, mock_tochka):
    assessment = await _make_assessment(db_session, test_admin, status="completed")
    order = await _make_order(db_session, test_admin, assessment, status="paid")
    resp = await admin_client.post(f"/api/payments/{order.id}/refund")
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"
    mock_tochka.refund_payment.assert_awaited_once()
    await db_session.refresh(order)
    await db_session.refresh(assessment)
    assert order.status == "refunded"
    assert assessment.status == "draft"


@pytest.mark.asyncio
async def test_credits_reflects_paid_orders(auth_client, db_session, test_user):
    assessment = await _make_assessment(db_session, test_user, status="draft")
    await _make_order(db_session, test_user, assessment, status="paid")
    resp = await auth_client.get("/api/payments/credits")
    assert resp.status_code == 200
    assert resp.json()["credits"] == payments_router.REPORTS_PER_ORDER

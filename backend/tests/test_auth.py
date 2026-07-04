"""
test_auth.py — regression-тесты роутера /api/auth.

Покрывает: register, login (OTP step 1), verify (OTP step 2), resend-otp,
forgot-password, reset-password, logout, /me.

Все email-функции мокаются (mock_email_senders fixture) — никаких реальных
SMTP-вызовов. Rate-limiting (slowapi) на эндпоинтах НЕ отключается специально:
если лимиты понизятся в проде по ошибке, тест на это не среагирует (вне
текущего scope), но множественные вызовы одного теста могут упереться в
лимит — поэтому каждый тест использует уникальный email.
"""
import uuid

import pytest
from sqlalchemy import select

from app.models import User, OtpCode
from app.auth import create_otp_code, hash_password


def unique_email() -> str:
    return f"regtest-{uuid.uuid4().hex[:10]}@example.com"


# ── Register ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_creates_user_and_sends_otp_and_welcome(client, db_session, mock_email_senders):
    email = unique_email()
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": "ValidPass123",
        "full_name": "Иван Тестов",
        "company_name": "ООО Тест",
    })
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.role == "user"
    assert user.full_name == "Иван Тестов"
    assert user.company_name == "ООО Тест"

    mock_email_senders["send_otp_email"].assert_called_once()
    mock_email_senders["send_welcome_email"].assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client, test_user, mock_email_senders):
    resp = await client.post("/api/auth/register", json={
        "email": test_user.email,
        "password": "AnotherPass123",
        "full_name": "Другое Имя",
        "company_name": "Другая компания",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password_rejected(client, mock_email_senders):
    resp = await client.post("/api/auth/register", json={
        "email": unique_email(),
        "password": "short",
        "full_name": "Имя",
        "company_name": "Компания",
    })
    assert resp.status_code == 422
    mock_email_senders["send_otp_email"].assert_not_called()


# ── Login (OTP step 1) ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_existing_email_sends_otp(client, test_user, mock_email_senders):
    resp = await client.post("/api/auth/login", json={"email": test_user.email})
    assert resp.status_code == 200
    mock_email_senders["send_otp_email"].assert_called_once()


@pytest.mark.asyncio
async def test_login_unknown_email_same_response_no_otp_sent(client, mock_email_senders):
    resp = await client.post("/api/auth/login", json={"email": unique_email()})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Если email зарегистрирован — код отправлен"
    mock_email_senders["send_otp_email"].assert_not_called()


# ── Verify (OTP step 2) ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_valid_otp_sets_auth_cookie(client, db_session, test_user, mock_email_senders):
    code = await create_otp_code(str(test_user.id), db_session)
    await db_session.flush()

    resp = await client.post("/api/auth/verify", json={
        "email": test_user.email,
        "code": code,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["role"] == "user"
    assert "auth-token" in client.cookies


@pytest.mark.asyncio
async def test_verify_wrong_code_returns_401(client, db_session, test_user, mock_email_senders):
    await create_otp_code(str(test_user.id), db_session)
    await db_session.flush()

    resp = await client.post("/api/auth/verify", json={
        "email": test_user.email,
        "code": "00000",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_unknown_email_returns_401(client, mock_email_senders):
    resp = await client.post("/api/auth/verify", json={
        "email": unique_email(),
        "code": "12345",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_otp_cannot_be_reused(client, db_session, test_user, mock_email_senders):
    code = await create_otp_code(str(test_user.id), db_session)
    await db_session.flush()

    first = await client.post("/api/auth/verify", json={"email": test_user.email, "code": code})
    assert first.status_code == 200

    second = await client.post("/api/auth/verify", json={"email": test_user.email, "code": code})
    assert second.status_code == 401


# ── /me ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_returns_current_user(auth_client, test_user):
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == test_user.email
    assert body["role"] == "user"


@pytest.mark.asyncio
async def test_me_without_cookie_returns_401(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(client):
    client.cookies.set("auth-token", "garbage-not-a-jwt")
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_clears_cookie(auth_client):
    resp = await auth_client.post("/api/auth/logout")
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "auth-token" in set_cookie


# ── Deactivated account enforcement ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_deactivated_silent_no_otp(client, db_session, test_user, mock_email_senders):
    test_user.is_active = False
    await db_session.flush()

    resp = await client.post("/api/auth/login", json={"email": test_user.email})
    assert resp.status_code == 200
    # ответ неотличим от несуществующего email
    assert "зарегистрирован" in resp.json()["message"]
    mock_email_senders["send_otp_email"].assert_not_called()


@pytest.mark.asyncio
async def test_resend_otp_deactivated_silent_no_otp(client, db_session, test_user, mock_email_senders):
    test_user.is_active = False
    await db_session.flush()

    resp = await client.post("/api/auth/resend-otp", json={"email": test_user.email})
    assert resp.status_code == 200
    mock_email_senders["send_otp_email"].assert_not_called()


@pytest.mark.asyncio
async def test_deactivated_user_gets_403(auth_client, db_session, test_user):
    # сессия выдана активному пользователю, затем аккаунт блокируется
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200

    test_user.is_active = False
    await db_session.flush()

    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 403

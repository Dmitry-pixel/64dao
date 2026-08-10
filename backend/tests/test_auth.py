"""
test_auth.py — regression-тесты роутера /api/auth.

Покрывает: register, login (OTP step 1), verify (OTP step 2), resend-otp,
logout, logout-all (отзыв сессий), /me.

Паролей в системе нет: forgot-password и reset-password удалены вместе с
users.password_hash в миграции 033.

Все email-функции мокаются (mock_email_senders fixture) — никаких реальных
SMTP-вызовов. Rate-limiting (slowapi) на эндпоинтах НЕ отключается специально:
если лимиты понизятся в проде по ошибке, тест на это не среагирует (вне
текущего scope), но множественные вызовы одного теста могут упереться в
лимит — поэтому каждый тест использует уникальный email.
"""
import uuid

import pytest
from sqlalchemy import func, select

from app.models import User, OtpCode
from app.auth import create_otp_code


def unique_email() -> str:
    return f"regtest-{uuid.uuid4().hex[:10]}@example.com"


# ── Register ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_creates_user_and_sends_otp_and_welcome(client, db_session, mock_email_senders):
    email = unique_email()
    resp = await client.post("/api/auth/register", json={
        "email": email,
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
        "full_name": "Другое Имя",
        "company_name": "Другая компания",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_ignores_password_field(client, db_session, mock_email_senders):
    """Пароль в теле запроса не принимается и никуда не сохраняется.

    Схема RegisterRequest его не объявляет, а extra-поля pydantic по
    умолчанию игнорирует. Тест фиксирует это: если поле однажды вернут,
    оно не должно молча начать что-то делать.
    """
    email = unique_email()
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": "ValidPass123",
        "full_name": "Имя",
        "company_name": "Компания",
    })
    assert resp.status_code == 200
    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert not hasattr(user, "password_hash")


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


# ── Logout all (отзыв сессий) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_all_invalidates_existing_session(auth_client, test_user):
    """Отзыв сессий убивает уже выданный токен.

    Вход беспарольный, поэтому кука на 7 дней — единственный ключ от
    аккаунта. До появления sessions_revoked_at отозвать её было нечем.
    """
    token = auth_client.cookies.get("auth-token")
    assert token

    before = await auth_client.get("/api/auth/me")
    assert before.status_code == 200

    resp = await auth_client.post("/api/auth/logout-all")
    assert resp.status_code == 200, resp.text

    # Ответ снимает куку. Возвращаем тот же токен вручную: проверяем, что
    # отвергается именно он, а не пустой запрос без куки.
    auth_client.cookies.set("auth-token", token)
    after = await auth_client.get("/api/auth/me")
    assert after.status_code == 401, after.text


@pytest.mark.asyncio
async def test_logout_all_burns_unused_otp(auth_client, db_session, test_user):
    """Неотработанный код входа гаснет вместе с отзывом сессий.

    Иначе код, отправленный до отзыва, остался бы действующим пропуском
    и обесценил бы саму кнопку.
    """
    await create_otp_code(str(test_user.id), db_session)
    unused_before = await db_session.scalar(
        select(func.count(OtpCode.id)).where(
            OtpCode.user_id == test_user.id, OtpCode.used.is_(False)))
    assert unused_before == 1

    resp = await auth_client.post("/api/auth/logout-all")
    assert resp.status_code == 200, resp.text

    unused_after = await db_session.scalar(
        select(func.count(OtpCode.id)).where(
            OtpCode.user_id == test_user.id, OtpCode.used.is_(False)))
    assert unused_after == 0


@pytest.mark.asyncio
async def test_logout_all_requires_auth(client):
    resp = await client.post("/api/auth/logout-all")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_revoke_user_sessions(admin_client, db_session, test_user):
    """Админ отзывает сессии пользователя, который сам этого сделать не может.

    Сценарий: потеряно устройство с открытой сессией, человек пишет в
    поддержку. Блокировка аккаунта тут не годится — она закрывает доступ
    целиком, а не одну сессию.
    """
    assert test_user.sessions_revoked_at is None

    resp = await admin_client.post(f"/api/admin/users/{test_user.id}/revoke-sessions")
    assert resp.status_code == 200, resp.text

    assert test_user.sessions_revoked_at is not None


@pytest.mark.asyncio
async def test_admin_revoke_sessions_unknown_user_404(admin_client):
    import uuid as _uuid
    resp = await admin_client.post(f"/api/admin/users/{_uuid.uuid4()}/revoke-sessions")
    assert resp.status_code == 404


# ── Профиль ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_profile_changes_name_and_company(auth_client, test_user):
    """PUT /api/auth/profile сохраняет имя и компанию.

    Эндпоинта не существовало: форма в кабинете слала сюда PUT и получала
    404, показывая «Ошибка сохранения».
    """
    resp = await auth_client.put("/api/auth/profile", json={
        "full_name": "  Новое Имя  ", "company_name": "ООО Новая"})
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["full_name"] == "Новое Имя"      # пробелы по краям срезаются
    assert body["company_name"] == "ООО Новая"
    assert test_user.full_name == "Новое Имя"


@pytest.mark.asyncio
async def test_update_profile_allows_empty_company(auth_client, test_user):
    """Компанию можно очистить: в кабинете поле не обязательное."""
    resp = await auth_client.put("/api/auth/profile", json={
        "full_name": "Имя", "company_name": ""})
    assert resp.status_code == 200, resp.text
    assert resp.json()["company_name"] is None


@pytest.mark.asyncio
async def test_update_profile_requires_auth(client):
    resp = await client.put("/api/auth/profile", json={
        "full_name": "Имя", "company_name": "Компания"})
    assert resp.status_code == 401

import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, Response
from jwt import PyJWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import OtpCode, User

settings = get_settings()

# Паролей в системе нет: вход — только по одноразовому коду на почту.
# Раньше пароль запрашивался при регистрации и хранился в users.password_hash,
# но verify_password не вызывался ни из одного роутера. То есть поле создавало
# у пользователя впечатление защиты, ничего не защищая, и при этом хранило
# чужие пароли — которые люди переиспользуют — без единой причины.
# Вместе с паролями ушли passlib и bcrypt из зависимостей.


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.jwt_expire_days)
    payload = {
        "sub":   user_id,
        "email": email,
        "role":  role,
        # iat нужен, чтобы отзыв сессий мог аннулировать ранее выданные
        # токены: без времени выпуска отличить старую сессию от новой нечем.
        # Дробные секунды намеренно не отбрасываются — см. token_revoked().
        "iat":   now.timestamp(),
        "exp":   expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="auth-token",
        value=token,
        httponly=True,
        secure=True,                        # только HTTPS
        samesite="lax",
        path="/",
        max_age=settings.jwt_expire_days * 86400,
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key="auth-token", path="/")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None


# backward-compat alias
_decode_token = decode_token


def create_impersonation_token(
    target_user_id: str,
    target_email: str,
    target_role: str,
    admin_id: str,
) -> str:
    """JWT от лица target_user, с полем impersonated_by=admin_id. TTL — 4 ч."""
    now = datetime.now(UTC)
    expire = now + timedelta(hours=4)
    payload = {
        "sub":             target_user_id,
        "email":           target_email,
        "role":            target_role,
        "impersonated_by": admin_id,
        "iat":             now.timestamp(),
        "exp":             expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def token_revoked(payload: dict, user: User) -> bool:
    """Токен выпущен до того, как пользователь отозвал свои сессии?

    Вход в систему беспарольный, поэтому семидневная кука — единственный
    ключ от аккаунта. Отозвать её иначе нечем: сменить «пароль» нельзя, а
    ждать истечения — неделя. Отметка sessions_revoked_at и есть этот рычаг:
    всё, что выпущено раньше неё, перестаёт действовать.

    Сравнение с дробными секундами. Округление iat до целых давало окно
    в секунду: токен, выпущенный в ту же секунду, что и отзыв, проходил бы
    проверку. Для человека неразличимо, для скрипта — нет.

    Токен без iat выпущен до появления этого поля. Пока отзыва не было, он
    остаётся рабочим; после отзыва доказать его свежесть нечем, поэтому он
    считается устаревшим — иначе отзыв не закрывал бы именно те сессии,
    ради которых его и нажимают.
    """
    revoked_at = getattr(user, "sessions_revoked_at", None)
    if revoked_at is None:
        return False
    iat = payload.get("iat")
    if iat is None:
        return True
    if revoked_at.tzinfo is None:
        revoked_at = revoked_at.replace(tzinfo=UTC)
    return float(iat) < revoked_at.timestamp()


# ── Dependencies ──────────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — возвращает текущего пользователя из JWT-куки."""
    token = request.cookies.get("auth-token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = _decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    if token_revoked(payload, user):
        raise HTTPException(status_code=401, detail="Сессия завершена")

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency — только для администраторов."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 5) -> str:
    """Криптографически безопасный цифровой OTP."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


async def create_otp_code(user_id: str, db: AsyncSession) -> str:
    """Инвалидирует старые коды и создаёт новый."""
    # Помечаем все активные коды как использованные
    await db.execute(
        update(OtpCode)
        .where(OtpCode.user_id == user_id, OtpCode.used.is_(False))
        .values(used=True)
    )

    code = generate_otp()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.otp_expire_minutes)

    otp = OtpCode(user_id=user_id, code=code, expires_at=expires_at, used=False)
    db.add(otp)
    await db.flush()  # получаем id без коммита (commit в get_db)

    return code


OTP_OK = "ok"
OTP_INVALID = "invalid"
OTP_EXHAUSTED = "exhausted"


async def verify_otp_code(user_id: str, code: str, db: AsyncSession) -> str:
    """Проверяет OTP: OTP_OK, OTP_INVALID или OTP_EXHAUSTED.

    Берётся последний действующий код пользователя (create_otp_code гасит
    прежние, так что он один), а не код, совпавший с введённым: иначе
    неверный ввод нечему засчитать. Строка блокируется FOR UPDATE, чтобы
    параллельные попытки не прочитали один и тот же счётчик.

    Счётчик меняется в сессии, но коммит — забота вызывающего: get_db
    откатывает транзакцию на исключении, а роутер отвечает 401 именно
    исключением. Без явного commit перед ним попытка не засчиталась бы.
    """
    now = datetime.now(UTC)
    otp = await db.scalar(
        select(OtpCode)
        .where(
            OtpCode.user_id == user_id,
            OtpCode.used    == False,       # noqa: E712
            OtpCode.expires_at > now,
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if not otp:
        return OTP_INVALID

    if secrets.compare_digest(otp.code, code):
        otp.used = True
        return OTP_OK

    otp.attempts += 1
    if otp.attempts >= settings.otp_max_attempts:
        otp.used = True
        return OTP_EXHAUSTED
    return OTP_INVALID

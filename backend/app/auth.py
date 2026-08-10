import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response, HTTPException, Depends
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import User, OtpCode

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(user_id: str, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt_expire_days)
    payload = {
        "sub":   user_id,
        "email": email,
        "role":  role,
        # iat нужен, чтобы смена пароля могла аннулировать ранее выданные
        # токены: без времени выпуска отличить старую сессию от новой нечем.
        # Дробные секунды намеренно не отбрасываются — см. комментарий в
        # token_predates_password_change().
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
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# backward-compat alias
_decode_token = decode_token


def create_impersonation_token(
    target_user_id: str,
    target_email: str,
    target_role: str,
    admin_id: str,
) -> str:
    """JWT от лица target_user, с полем impersonated_by=admin_id. TTL — 4 ч."""
    now = datetime.now(timezone.utc)
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


def token_predates_password_change(payload: dict, user: User) -> bool:
    """Токен выпущен до последней смены пароля этого пользователя?

    Сравнение с дробными секундами. Округление iat до целых ломало главный
    сценарий: ссылка сброса, использованная дважды в пределах одной секунды,
    во второй раз давала iat == password_changed_at и проходила проверку.
    Для человека это неотличимо от одноразовости, для скрипта — нет.

    Токен без iat выпущен до появления этого поля. Пока пароль не менялся,
    он остаётся рабочим; после смены доказать его свежесть нечем, поэтому
    он считается устаревшим — иначе смена пароля не закрывала бы именно те
    сессии, ради которых она чаще всего и делается.
    """
    changed_at = getattr(user, "password_changed_at", None)
    if changed_at is None:
        return False
    iat = payload.get("iat")
    if iat is None:
        return True
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    return float(iat) < changed_at.timestamp()


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

    # Смена пароля закрывает все ранее выданные сессии. Раньше выданная
    # кука жила до истечения (7 дней) независимо от смены пароля, то есть
    # смена пароля не выгоняла того, кто уже вошёл.
    if token_predates_password_change(payload, user):
        raise HTTPException(status_code=401,
                            detail="Сессия завершена: пароль был изменён")

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency — только для администраторов."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Password reset token ─────────────────────────────────────────────────────

def create_reset_token(user_id: str, email: str) -> str:
    """JWT на 1 час для сброса пароля. Одноразовость — через iat, см.
    token_predates_password_change()."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=1)
    payload = {"sub": user_id, "email": email, "type": "password_reset",
               "iat": now.timestamp(), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_reset_token(token: str) -> dict:
    """Декодирует и проверяет токен сброса. Возвращает payload или бросает 400."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except PyJWTError:
        raise HTTPException(status_code=400, detail="Ссылка недействительна или истекла")
    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Неверный тип токена")
    return payload


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
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)

    otp = OtpCode(user_id=user_id, code=code, expires_at=expires_at, used=False)
    db.add(otp)
    await db.flush()  # получаем id без коммита (commit в get_db)

    return code


async def verify_otp_code(user_id: str, code: str, db: AsyncSession) -> bool:
    """Проверяет OTP. При успехе помечает как использованный."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.user_id == user_id,
            OtpCode.code    == code,
            OtpCode.used    == False,       # noqa: E712
            OtpCode.expires_at > now,
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    otp = result.scalar_one_or_none()

    if not otp:
        return False

    otp.used = True
    return True

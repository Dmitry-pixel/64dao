import asyncio
import logging
import random
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    clear_auth_cookie,
    create_otp_code,
    create_token,
    get_current_user,
    set_auth_cookie,
    verify_otp_code,
)
from app.db import get_db
from app.email import send_otp_email, send_welcome_email
from app.limiter import limiter
from app.models import OtpCode, User
from app.schemas import (
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    ResendOTPRequest,
    SuccessResponse,
    UserOut,
    VerifyOTPRequest,
)
from app.site_mode import get_site_mode

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=SuccessResponse)
@limiter.limit("5/minute")
async def register(
    request: Request,   # ← slowapi требует Request первым аргументом
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Регистрация: email + пароль + имя + компания → OTP на почту."""
    if get_site_mode().enabled:
        raise HTTPException(
            status_code=403,
            detail="Регистрация временно недоступна. Сайт находится на техническом обслуживании.",
        )
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email уже зарегистрирован")

    user = User(
        email=body.email,
        full_name=body.full_name,
        company_name=body.company_name,
        role="user",
    )
    db.add(user)
    await db.flush()

    code = await create_otp_code(str(user.id), db)
    await asyncio.gather(
        send_otp_email(user.email, code, user.full_name),
        send_welcome_email(user.email, user.full_name or ""),
    )

    return SuccessResponse(message="Аккаунт создан. Проверьте email.")


# ── Login (шаг 1 OTP-flow) ────────────────────────────────────────────────────

@router.post("/login", response_model=SuccessResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Чистый OTP-flow: принимает ТОЛЬКО email.
    Одинаковый ответ и время ответа для существующих и несуществующих email.
    """
    user = await db.scalar(select(User).where(User.email == body.email))

    if user and not user.is_active:
        logger.info("OTP request for deactivated account: %s", body.email)
        user = None  # ответ неотличим от несуществующего email

    if user:
        code = await create_otp_code(str(user.id), db)
        try:
            await send_otp_email(user.email, code, user.full_name)
        except Exception as exc:
            logger.error("Failed to send OTP to %s: %s", user.email, exc)
            raise HTTPException(status_code=500, detail="Не удалось отправить код. Попробуйте позже.") from exc
    else:
        logger.info("OTP request for unknown email: %s", body.email)
        # ── Защита от Timing Attack ───────────────────────────────────────────
        # Без этой задержки запрос для несуществующего email завершается быстрее
        # (нет обращения к БД для OTP и SMTP-вызова), что позволяет по времени
        # ответа определить, зарегистрирован ли email (user enumeration).
        # Случайный диапазон [0.15, 0.35] имитирует время create_otp + send_email.
        await asyncio.sleep(random.uniform(0.15, 0.35))

    return SuccessResponse(message="Если email зарегистрирован — код отправлен")


# ── Verify (шаг 2 OTP-flow) ───────────────────────────────────────────────────

@router.post("/verify")
@limiter.limit("10/minute")
async def verify(
    request: Request,
    body: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Проверяет OTP по email + code.
    user_id НЕ принимается с фронта — ищем пользователя по email.
    При успехе ставит httpOnly-куку auth-token.
    """
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user:
        # Одинаковая ошибка — не раскрываем что email не существует
        raise HTTPException(status_code=401, detail="Неверный или просроченный код")

    # verify_otp_code возвращает bool — обрабатываем явно
    valid: bool = await verify_otp_code(str(user.id), body.code, db)
    if not valid:
        raise HTTPException(status_code=401, detail="Неверный или просроченный код")

    token = create_token(str(user.id), user.email, user.role)
    set_auth_cookie(response, token)

    return {"success": True, "role": user.role}


# ── Resend OTP ────────────────────────────────────────────────────────────────

@router.post("/resend-otp", response_model=SuccessResponse)
@limiter.limit("3/minute")
async def resend_otp(
    request: Request,
    body: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await db.scalar(select(User).where(User.email == body.email))
    if user and not user.is_active:
        logger.info("OTP request for deactivated account: %s", body.email)
        user = None  # ответ неотличим от несуществующего email

    if user:
        code = await create_otp_code(str(user.id), db)
        try:
            await send_otp_email(user.email, code, user.full_name)
        except Exception as exc:
            logger.error("Failed to resend OTP to %s: %s", user.email, exc)
            raise HTTPException(status_code=500, detail="Не удалось отправить код") from exc
    else:
        # Timing protection для resend тоже
        await asyncio.sleep(random.uniform(0.15, 0.35))

    return SuccessResponse(message="Если email зарегистрирован — код отправлен")


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=SuccessResponse)
async def logout(response: Response):
    clear_auth_cookie(response)
    return SuccessResponse(message="Выход выполнен")


@router.post("/logout-all", response_model=SuccessResponse)
async def logout_all(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Завершить сессии на всех устройствах.

    Вход беспарольный, поэтому кука на 7 дней — единственный ключ от
    аккаунта, и до появления этой отметки отозвать её было нечем: украли
    ноутбук с открытой сессией — оставалось ждать неделю.

    Текущая сессия тоже завершается: её токен выпущен раньше отметки.
    Кука снимается сразу, чтобы браузер не бился в 401 до перезагрузки.
    """
    user.sessions_revoked_at = datetime.now(UTC)

    # Неотработанные коды входа гасим заодно: код, отправленный до отзыва,
    # остался бы действующим пропуском и обесценил бы саму кнопку.
    await db.execute(
        update(OtpCode)
        .where(OtpCode.user_id == user.id, OtpCode.used.is_(False))
        .values(used=True)
    )

    clear_auth_cookie(response)
    return SuccessResponse(message="Сессии на всех устройствах завершены")


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.put("/profile", response_model=UserOut)
async def update_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Имя и название компании из кабинета.

    Эндпоинта не существовало вовсе: форма в профиле слала сюда PUT и всегда
    получала 404, а пользователь видел «Ошибка сохранения». Изменить эти поля
    через интерфейс было нельзя с самого начала.
    """
    user.full_name = body.full_name.strip()
    user.company_name = body.company_name.strip() or None
    await db.flush()
    return user

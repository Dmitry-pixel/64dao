from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin, get_current_user, hash_password, create_impersonation_token, create_token, decode_token, set_auth_cookie
from app.config import get_settings
from app.db import get_db
from app.models import User, Assessment, Report, Strategy
from app.schemas import (
    AdminSetupRequest, AdminStats,
    StrategyCreate, StrategyUpdate, StrategyOut, StrategyListItem,
    UserOut, AssessmentOut, ImpersonateStatus, SuccessResponse,
)

settings = get_settings()
router = APIRouter(prefix="/api/admin", tags=["admin"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


# ── Setup (создание первого администратора) ───────────────────────────────────
@router.post("/setup", response_model=SuccessResponse)
async def admin_setup(body: AdminSetupRequest, db: AsyncSession = Depends(get_db)):
    if not settings.admin_setup_key or body.setup_key != settings.admin_setup_key:
        raise HTTPException(status_code=401, detail="Неверный ключ")

    # Отключаем страницу после создания первого администратора
    existing_admin = await db.scalar(
        select(User).where(User.role == "admin").limit(1)
    )
    if existing_admin:
        raise HTTPException(status_code=403, detail="Администратор уже создан")

    existing_user = await db.scalar(select(User).where(User.email == body.email))
    if existing_user:
        raise HTTPException(status_code=409, detail="Email уже занят")

    admin = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
    )
    db.add(admin)
    return SuccessResponse(message="Администратор создан. Войдите через /login.")


# ── Stats ─────────────────────────────────────────────────────────────────────
@router.get("/stats", response_model=AdminStats)
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users        = await db.scalar(select(func.count(User.id))) or 0
    total_assessments  = await db.scalar(select(func.count(Assessment.id))) or 0
    total_reports      = await db.scalar(select(func.count(Report.id))) or 0
    published_strategies = await db.scalar(
        select(func.count(Strategy.id)).where(Strategy.is_published == True)
    ) or 0

    recent_users_res = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(5)
    )
    recent_users = recent_users_res.scalars().all()

    recent_assessments_res = await db.execute(
        select(Assessment)
        .options(selectinload(Assessment.reports))
        .order_by(Assessment.created_at.desc())
        .limit(5)
    )
    recent_assessments = recent_assessments_res.scalars().all()

    return AdminStats(
        total_users=total_users,
        total_assessments=total_assessments,
        total_reports=total_reports,
        published_strategies=published_strategies,
        recent_users=recent_users,
        recent_assessments=recent_assessments,
    )


# ── Users ─────────────────────────────────────────────────────────────────────
@router.get("/users", response_model=list[UserOut])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


# ── Strategies ────────────────────────────────────────────────────────────────
@router.get("/strategies", response_model=list[StrategyListItem])
async def list_strategies(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Strategy).order_by(Strategy.combination))
    return result.scalars().all()


@router.get("/strategies/{strategy_id}", response_model=StrategyOut)
async def get_strategy(
    strategy_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    strategy = await db.scalar(select(Strategy).where(Strategy.id == strategy_id))
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")
    return strategy


@router.post("/strategies", response_model=StrategyOut, status_code=201)
async def create_strategy(
    body: StrategyCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(
        select(Strategy).where(Strategy.combination == body.combination)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Комбинация уже существует")

    strategy = Strategy(**body.model_dump())
    db.add(strategy)
    await db.flush()
    await db.refresh(strategy)
    return strategy


@router.put("/strategies/{strategy_id}", response_model=StrategyOut)
async def update_strategy(
    strategy_id: str,
    body: StrategyUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    strategy = await db.scalar(select(Strategy).where(Strategy.id == strategy_id))
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(strategy, field, value)

    await db.flush()
    await db.refresh(strategy)
    return strategy


@router.delete("/strategies/{strategy_id}", response_model=SuccessResponse)
async def delete_strategy(
    strategy_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    strategy = await db.scalar(select(Strategy).where(Strategy.id == strategy_id))
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")
    await db.delete(strategy)
    return SuccessResponse(message="Удалено")


@router.post("/strategies/{strategy_id}/image", response_model=SuccessResponse)
async def upload_strategy_image(
    strategy_id: str,
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Разрешены только JPG, PNG, WebP")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 5 МБ)")

    strategy = await db.scalar(select(Strategy).where(Strategy.id == strategy_id))
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")

    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    filename = f"{strategy_id}.{ext}"
    images_dir = Path(settings.uploads_dir).parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    img_path = images_dir / filename
    with open(img_path, "wb") as f:
        f.write(contents)

    # URL относительно /uploads/images/
    strategy.image_url = f"/uploads/images/{filename}"
    await db.flush()

    return SuccessResponse(message="Изображение загружено")


# ── User role management ──────────────────────────────────────────────────────

class SetRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")
        return v


@router.patch("/users/{user_id}/role", response_model=SuccessResponse)
async def set_user_role(
    user_id: str,
    body: SetRoleRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if str(admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Нельзя изменить свою роль")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.role = body.role
    await db.flush()
    return SuccessResponse(message=f"Роль изменена на {body.role}")


# ── Reports list ──────────────────────────────────────────────────────────────
@router.get("/reports", response_model=list[AssessmentOut])
async def list_all_assessments(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assessment)
        .options(selectinload(Assessment.reports))
        .order_by(Assessment.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()


# ── Impersonation ─────────────────────────────────────────────────────────────

@router.post("/impersonate/{user_id}", response_model=SuccessResponse)
async def start_impersonation(
    user_id: str,
    response: Response,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Админ входит в систему от лица указанного пользователя."""
    target = await db.scalar(select(User).where(User.id == user_id))
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if target.role == "admin":
        raise HTTPException(status_code=400, detail="Нельзя имперсонировать администратора")

    token = create_impersonation_token(
        str(target.id), target.email, target.role, str(admin.id)
    )
    set_auth_cookie(response, token)
    return SuccessResponse(message=f"Вы вошли как {target.email}")


@router.post("/impersonate/stop", response_model=SuccessResponse)
async def stop_impersonation(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Возврат из режима имперсонации обратно в аккаунт администратора."""
    token = request.cookies.get("auth-token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    admin_id = payload.get("impersonated_by")
    if not admin_id:
        raise HTTPException(status_code=400, detail="Нет активной имперсонации")

    admin = await db.scalar(select(User).where(User.id == admin_id))
    if not admin or admin.role != "admin":
        raise HTTPException(status_code=404, detail="Администратор не найден")

    new_token = create_token(str(admin.id), admin.email, admin.role)
    set_auth_cookie(response, new_token)
    return SuccessResponse(message="Вернулись в аккаунт администратора")


@router.get("/impersonate/status", response_model=ImpersonateStatus)
async def impersonation_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Статус текущей сессии: активна ли имперсонация и от чьего лица."""
    token = request.cookies.get("auth-token")
    if not token:
        return ImpersonateStatus(active=False)

    try:
        payload = decode_token(token)
    except Exception:
        return ImpersonateStatus(active=False)

    admin_id = payload.get("impersonated_by")
    if not admin_id:
        return ImpersonateStatus(active=False)

    target = await db.scalar(select(User).where(User.id == payload.get("sub")))
    return ImpersonateStatus(
        active=True,
        target_user=target,
        admin_id=admin_id,
    )

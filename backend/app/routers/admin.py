from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin, get_current_user, hash_password, create_impersonation_token, create_token, decode_token, set_auth_cookie
from app.config import get_settings
from app.db import get_db
from app.models import User, Assessment, AssessmentContour, Report, Strategy, Order, LifecycleStage, AccessGrant
from app.schemas import (
    AdminSetupRequest, AdminStats, LogEntry,
    StrategyCreate, StrategyUpdate, StrategyOut, StrategyListItem,
    UserOut, AssessmentOut, ImpersonateStatus, SuccessResponse, ContourBrief,
    AccessGrantCreate, AccessGrantOut,
)

settings = get_settings()
router = APIRouter(prefix="/api/admin", tags=["admin"])



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
    total_reports      = await db.scalar(
        select(func.count(Assessment.id)).where(Assessment.status.in_(["completed", "paid"]))
    ) or 0
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

    # Статистика покупок за последние 30 дней
    since = datetime.now(timezone.utc) - timedelta(days=29)
    orders_res = await db.execute(
        select(
            cast(Order.created_at, Date).label("day"),
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(Order.amount), 0).label("amount"),
        )
        .where(Order.created_at >= since)
        .group_by(cast(Order.created_at, Date))
        .order_by(cast(Order.created_at, Date))
    )
    orders_by_day_raw = orders_res.all()

    # Заполняем все 30 дней (включая дни без заказов)
    all_days: dict[str, dict] = {}
    for i in range(30):
        d = (since + timedelta(days=i)).strftime("%Y-%m-%d")
        all_days[d] = {"date": d, "count": 0, "amount": 0}
    for row in orders_by_day_raw:
        key = str(row.day)
        if key in all_days:
            all_days[key] = {"date": key, "count": int(row.count), "amount": float(row.amount)}
    orders_by_day = list(all_days.values())

    total_orders = await db.scalar(select(func.count(Order.id))) or 0
    total_revenue = float(await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(Order.status == "paid")
    ) or 0)

    return AdminStats(
        total_users=total_users,
        total_assessments=total_assessments,
        total_reports=total_reports,
        published_strategies=published_strategies,
        recent_users=recent_users,
        recent_assessments=recent_assessments,
        orders_by_day=orders_by_day,
        total_orders=total_orders,
        total_revenue=total_revenue,
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


@router.get("/strategies/combo/{combination}", response_model=StrategyOut)
async def get_strategy_by_combo(
    combination: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    strategy = await db.scalar(
        select(Strategy).where(Strategy.combination == combination)
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Стратегия не найдена")
    return strategy


@router.put("/strategies/combo/{combination}", response_model=StrategyOut)
async def upsert_strategy_by_combo(
    combination: str,
    body: StrategyUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    strategy = await db.scalar(
        select(Strategy).where(Strategy.combination == combination)
    )
    if strategy:
        # Обновляем существующую
        for field, value in body.model_dump(exclude_unset=True).items():
            if value is not None or field in ('lifecycle_description',):
                setattr(strategy, field, value)
    else:
        # Создаём новую
        data = body.model_dump(exclude_unset=True)
        data['combination'] = combination
        strategy = Strategy(**data)
        db.add(strategy)

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


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if str(admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await db.delete(user)
    await db.flush()
    return SuccessResponse(message="Пользователь удалён")


# ── Activity log ──────────────────────────────────────────────────────────────

class SetStatusRequest(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}/status", response_model=SuccessResponse)
async def set_user_status(
    user_id: str,
    body: SetStatusRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.email import send_account_status_email

    if str(admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Нельзя изменить свой статус")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Нельзя блокировать администратора")
    if user.is_active == body.is_active:
        return SuccessResponse(message="Статус не изменён")

    user.is_active = body.is_active
    await db.flush()

    try:
        await send_account_status_email(user.email, user.full_name, body.is_active)
    except Exception as exc:
        import logging; logging.getLogger(__name__).error("Status email failed for %s: %s", user.email, exc)

    status = "активирован" if body.is_active else "заблокирован"
    return SuccessResponse(message=f"Пользователь {status}")


@router.get("/logs", response_model=list[LogEntry])
async def get_activity_log(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Объединённая лента событий: регистрации, диагностики, PDF — последние 100."""
    LIMIT = 200  # берём по 200 из каждой таблицы, потом обрежем до 100

    events: list[dict] = []

    # Регистрации пользователей
    users_res = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(LIMIT)
    )
    for u in users_res.scalars():
        events.append({
            "type":       "user",
            "timestamp":  u.created_at.isoformat(),
            "user_email": u.email,
            "user_name":  u.full_name,
            "detail":     "Регистрация",
            "sub":        None,
        })

    # Диагностики с данными пользователя
    assessments_res = await db.execute(
        select(Assessment, User.email, User.full_name)
        .join(User, Assessment.user_id == User.id)
        .order_by(Assessment.created_at.desc())
        .limit(LIMIT)
    )
    for row in assessments_res:
        a, email, name = row
        if a.method1_combination:
            detail = "Диагностика Метод 1"
            sub = a.method1_combination
        else:
            detail = "Диагностика Метод 2"
            sub = a.company_name or "—"
        events.append({
            "type":       "assessment",
            "timestamp":  a.created_at.isoformat(),
            "user_email": email,
            "user_name":  name,
            "detail":     detail,
            "sub":        sub,
        })

    # PDF-отчёты с данными пользователя
    reports_res = await db.execute(
        select(Report, User.email, User.full_name)
        .join(User, Report.user_id == User.id)
        .order_by(Report.created_at.desc())
        .limit(LIMIT)
    )
    for row in reports_res:
        r, email, name = row
        events.append({
            "type":       "report",
            "timestamp":  (r.generated_at or r.created_at).isoformat(),
            "user_email": email,
            "user_name":  name,
            "detail":     "PDF сформирован",
            "sub":        r.pdf_filename,
        })

    # Сортируем по убыванию даты и берём первые 100
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events[:100]


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
    assessments = result.scalars().all()

    # Пройденные контуры — одним запросом на всю выдачу (как в списке диагностик
    # пользователя), чтобы админка показывала, что можно сбросить.
    contours_map: dict = {}
    if assessments:
        rows = (await db.execute(
            select(AssessmentContour).where(
                AssessmentContour.assessment_id.in_([a.id for a in assessments])
            )
        )).scalars().all()
        for r in rows:
            contours_map.setdefault(r.assessment_id, []).append(r)

    out = []
    for a in assessments:
        item = AssessmentOut.model_validate(a)
        item.passed_contours = [
            ContourBrief.model_validate(r) for r in contours_map.get(a.id, [])
        ]
        out.append(item)
    return out


# ── Impersonation ─────────────────────────────────────────────────────────────
# ВАЖНО: статический маршрут /impersonate/stop должен быть ВЫШЕ динамического
# /impersonate/{user_id}, иначе FastAPI трактует "stop" как user_id.

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


import json


# ── Тариф и цена ──────────────────────────────────────────────────────────────
# Раньше здесь были собственные DEFAULT_PRICING/PRICING_FILE/_read_pricing/
# _write_pricing — продублированные с routers/pricing.py. Теперь оба места
# (и payments.py) читают/пишут через общий app/pricing_store.py.
from app.pricing_store import read_pricing, write_pricing


@router.get("/pricing")
async def get_pricing(_: User = Depends(require_admin)):
    return read_pricing()


@router.put("/pricing")
async def update_pricing(body: dict, _: User = Depends(require_admin)):
    write_pricing(body)
    return {"ok": True}


# ── Точка Банк: JWT-токен и Client ID (редактируются без пересборки) ─────────
from app.tochka_settings import masked_view as _tochka_masked_view, write_tochka_settings


@router.get("/tochka-settings")
async def get_tochka_settings_view(_: User = Depends(require_admin)):
    return _tochka_masked_view()


@router.put("/tochka-settings")
async def update_tochka_settings_view(body: dict, _: User = Depends(require_admin)):
    write_tochka_settings(body)
    return _tochka_masked_view()


# ── Email templates ───────────────────────────────────────────────────────────

# Шаблоны писем: единственный источник дефолтов и путь к хранилищу —
# app/email_templates_store. Здесь остаётся только HTTP-обвязка.
from app.email_templates_store import (  # noqa: F401,E402
    DEFAULT_TEMPLATES,
    TEMPLATES_FILE,
    read_templates as _read_templates,
    write_templates as _write_templates,
)


@router.get("/email-senders")
async def get_email_senders(_: User = Depends(require_admin)):
    from app import email_templates_store as _ets
    return {
        "allowed": _ets.allowed_senders(),
        "default": _ets.default_sender(),
    }


@router.get("/email-templates")
async def get_email_templates(_: User = Depends(require_admin)):
    return _read_templates()


@router.put("/email-templates")
async def update_email_templates(body: dict, _: User = Depends(require_admin)):
    _write_templates(body)
    return {"ok": True}


# ── Настройки email-напоминаний ─────────────────────────────────────────────
# Расписание живёт в host cron, здесь только «что и когда рассылать».
from app import reminders_settings as _reminders  # noqa: E402


@router.get("/reminders-settings")
async def get_reminders_settings(_: User = Depends(require_admin)):
    return _reminders.read()


@router.put("/reminders-settings")
async def update_reminders_settings(body: dict,
                                    _: User = Depends(require_admin)):
    # Возвращаем нормализованное значение: админка сразу видит,
    # что порог мог быть подрезан до допустимых границ.
    return _reminders.write(body)


# ── Documents (юридические документы) ───────────────────────────────────────

DOCS_DIR = Path("/var/www/64dao/uploads/docs")

ALLOWED_DOC_SLUGS = {
    "user-agreement":       "Пользовательское соглашение",
    "privacy-policy":       "Политика обработки персональных данных",
    "personal-data-consent":"Согласие на обработку персональных данных",
    "about":                "О нас",
}


def _read_doc(slug: str) -> dict:
    path = DOCS_DIR / f"{slug}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "slug":       slug,
            "title":      ALLOWED_DOC_SLUGS.get(slug, slug),
            "content":    "",
            "published":  False,
            "updated_at": None,
        }


def _write_doc(slug: str, data: dict) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_DIR / f"{slug}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/documents/{slug}")
async def get_document(slug: str, _: User = Depends(require_admin)):
    if slug not in ALLOWED_DOC_SLUGS:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return _read_doc(slug)


@router.put("/documents/{slug}")
async def save_document(slug: str, body: dict, _: User = Depends(require_admin)):
    if slug not in ALLOWED_DOC_SLUGS:
        raise HTTPException(status_code=404, detail="Документ не найден")
    from datetime import datetime, timezone
    body["slug"] = slug
    body["title"] = ALLOWED_DOC_SLUGS[slug]
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_doc(slug, body)
    return {"ok": True}


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


# ── Социальные сети ───────────────────────────────────────────────────────────

SOCIAL_LINKS_FILE = Path("/var/www/64dao/uploads/social_links.json")

DEFAULT_SOCIAL_LINKS = {
    "telegram": "",
    "vk": "",
    "max": "",
}


def _read_social_links() -> dict:
    try:
        return json.loads(SOCIAL_LINKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_SOCIAL_LINKS.copy()


def _write_social_links(data: dict) -> None:
    SOCIAL_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOCIAL_LINKS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/social-links")
async def get_social_links(_: User = Depends(require_admin)):
    return _read_social_links()


@router.put("/social-links")
async def update_social_links(body: dict, _: User = Depends(require_admin)):
    _write_social_links(body)
    return {"ok": True}


# ── Пример отчёта (PDF) ───────────────────────────────────────────────────────

SAMPLE_REPORT_FILE = Path("/var/www/64dao/uploads/sample_report.pdf")


@router.get("/sample-report/status")
async def get_sample_report_status(_: User = Depends(require_admin)):
    exists = SAMPLE_REPORT_FILE.exists()
    return {
        "uploaded": exists,
        "size_bytes": SAMPLE_REPORT_FILE.stat().st_size if exists else None,
    }


@router.post("/sample-report")
async def upload_sample_report(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Допускаются только PDF-файлы")

    contents = await file.read()
    SAMPLE_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE_REPORT_FILE.write_bytes(contents)
    return {"ok": True, "size_bytes": len(contents)}


@router.delete("/sample-report")
async def delete_sample_report(_: User = Depends(require_admin)):
    if not SAMPLE_REPORT_FILE.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    SAMPLE_REPORT_FILE.unlink()
    return {"ok": True}


class LifecycleStagePatch(BaseModel):
    sort_order: int
    description: str | None = None


@router.get("/lifecycle-stages")
async def admin_get_lifecycle_stages(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(LifecycleStage).order_by(LifecycleStage.sort_order))
    return [
        {"sort_order": s.sort_order, "name": s.name, "description": s.description}
        for s in rows.scalars().all()
    ]


@router.put("/lifecycle-stages")
async def admin_update_lifecycle_stages(
    body: list[LifecycleStagePatch],
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(LifecycleStage))
    by_order = {s.sort_order: s for s in rows.scalars().all()}
    for item in body:
        stage = by_order.get(item.sort_order)
        if stage is None:
            raise HTTPException(status_code=404, detail="Stage not found")
        stage.description = item.description
    await db.flush()
    return {"ok": True}


# ── Контуры диагностики Метода 1 ─────────────────────────────────────────────

class ContourFlagUpdate(BaseModel):
    enabled: bool


@router.get("/contours")
async def admin_list_contours(admin: User = Depends(require_admin)):
    """Состояние per-contour флагов. Хранятся в runtime-конфиге (Поправка П2)."""
    from app.contours import CONTOURS, CONTOUR_ORDER
    from app.contour_settings import get_contour_settings
    flags = get_contour_settings()
    return {"contours": [
        {"contour": k, "title": CONTOURS[k].title, "enabled": bool(flags.get(k, False))}
        for k in CONTOUR_ORDER
    ]}


@router.put("/contours/{contour}")
async def admin_set_contour(
    contour: str,
    body: ContourFlagUpdate,
    admin: User = Depends(require_admin),
):
    """Включение и выключение контура без пересборки образа."""
    from app.contour_settings import set_contour_enabled
    try:
        return {"contours": set_contour_enabled(contour, body.enabled)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/assessments/{assessment_id}/contours/{contour}", status_code=204)
async def admin_reset_contour(
    assessment_id: str,
    contour: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сброс ошибочно пройденного контура (Поправка П10): пользователь сможет
    пройти его заново. Отчёт пересобирается при следующем скачивании."""
    if contour == "finance":
        raise HTTPException(
            status_code=400,
            detail="Финансовый контур — часть обязательной анкеты Метода 1, сбросить его отдельно нельзя.",
        )
    row = await db.scalar(
        select(AssessmentContour).where(
            AssessmentContour.assessment_id == assessment_id,
            AssessmentContour.contour == contour,
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Контур не пройден")
    await db.delete(row)


# ── Тестовый доступ: гранты на бесплатные диагностики ──────────────────────────
# Квота + срок; расход считается по assessments.grant_id (app.access_grants).
# Сбой SMTP не откатывает выдачу: доступ уже выдан, письмо переотправляется
# кнопкой (POST /access-grants/{id}/notify), факт отправки — в email_sent_at.

def _grant_out(grant: AccessGrant, state: dict, user: User | None = None) -> AccessGrantOut:
    return AccessGrantOut(
        id=grant.id,
        user_id=grant.user_id,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        quota=grant.quota,
        used=state["used"],
        remaining=state["remaining"],
        status=state["status"],
        starts_at=grant.starts_at,
        expires_at=grant.expires_at,
        reason=grant.reason,
        created_at=grant.created_at,
        revoked_at=grant.revoked_at,
        email_sent_at=grant.email_sent_at,
    )


def _normalize_expires(value: datetime) -> datetime:
    """Дата из формы приходит без таймзоны: считаем её UTC, иначе сравнение
    с datetime.now(timezone.utc) упадёт на naive/aware."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("/access-grants", response_model=list[AccessGrantOut])
async def list_access_grants(
    status: str | None = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Все выданные доступы, свежие сверху. ?status=active — только действующие."""
    from app.access_grants import states as grant_states

    rows = (await db.execute(
        select(AccessGrant, User)
        .join(User, User.id == AccessGrant.user_id)
        .order_by(AccessGrant.created_at.desc())
    )).all()
    st = await grant_states(db, [g for g, _ in rows])
    out = []
    for grant, user in rows:
        state = st[grant.id]
        if status and state["status"] != status:
            continue
        out.append(_grant_out(grant, state, user))
    return out


@router.get("/users/{user_id}/access-grants", response_model=list[AccessGrantOut])
async def list_user_access_grants(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.access_grants import states as grant_states

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    grants = (await db.execute(
        select(AccessGrant)
        .where(AccessGrant.user_id == user.id)
        .order_by(AccessGrant.created_at.desc())
    )).scalars().all()
    st = await grant_states(db, list(grants))
    return [_grant_out(g, st[g.id], user) for g in grants]


@router.post("/users/{user_id}/access-grants", response_model=AccessGrantOut, status_code=201)
async def create_access_grant(
    user_id: str,
    body: AccessGrantCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Выдать временный бесплатный доступ и уведомить партнёра письмом."""
    from app.access_grants import grant_state
    from app.email import send_access_grant_email

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Пользователь заблокирован — сначала разблокируйте доступ")
    expires_at = _normalize_expires(body.expires_at)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Дата окончания должна быть в будущем")

    grant = AccessGrant(
        user_id=user.id,
        quota=body.quota,
        expires_at=expires_at,
        reason=body.reason,
        created_by=admin.id,
    )
    db.add(grant)
    await db.flush()

    if body.notify:
        try:
            await send_access_grant_email(user.email, user.full_name, grant.quota, expires_at)
            grant.email_sent_at = datetime.now(timezone.utc)
            await db.flush()
        except Exception as exc:
            import logging; logging.getLogger(__name__).error(
                "Access grant email failed for %s: %s", user.email, exc)

    return _grant_out(grant, await grant_state(db, grant), user)


@router.post("/access-grants/{grant_id}/revoke", response_model=AccessGrantOut)
async def revoke_access_grant(
    grant_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Отзыв доступа. Уже сформированные отчёты остаются у пользователя:
    отзывается право проходить новые диагностики, а не выданные результаты."""
    from app.access_grants import grant_state

    grant = await db.scalar(select(AccessGrant).where(AccessGrant.id == grant_id))
    if not grant:
        raise HTTPException(status_code=404, detail="Грант не найден")
    if grant.revoked_at:
        raise HTTPException(status_code=409, detail="Грант уже отозван")
    grant.revoked_at = datetime.now(timezone.utc)
    grant.revoked_by = admin.id
    await db.flush()
    user = await db.scalar(select(User).where(User.id == grant.user_id))
    return _grant_out(grant, await grant_state(db, grant), user)


@router.post("/access-grants/{grant_id}/notify", response_model=AccessGrantOut)
async def notify_access_grant(
    grant_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Переотправка письма о доступе: после сбоя SMTP или по просьбе партнёра."""
    from app.access_grants import grant_state
    from app.email import send_access_grant_email

    grant = await db.scalar(select(AccessGrant).where(AccessGrant.id == grant_id))
    if not grant:
        raise HTTPException(status_code=404, detail="Грант не найден")
    if grant.revoked_at:
        raise HTTPException(status_code=400, detail="Грант отозван — письмо не отправляется")
    if grant.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Срок доступа истёк — письмо не отправляется")
    user = await db.scalar(select(User).where(User.id == grant.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    try:
        await send_access_grant_email(user.email, user.full_name, grant.quota, grant.expires_at)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Не удалось отправить письмо: %s" % exc)
    grant.email_sent_at = datetime.now(timezone.utc)
    await db.flush()
    return _grant_out(grant, await grant_state(db, grant), user)

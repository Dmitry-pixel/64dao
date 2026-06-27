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
from app.models import User, Assessment, Report, Strategy, Order
from app.schemas import (
    AdminSetupRequest, AdminStats, LogEntry,
    StrategyCreate, StrategyUpdate, StrategyOut, StrategyListItem,
    UserOut, AssessmentOut, ImpersonateStatus, SuccessResponse,
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
    return result.scalars().all()


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

PRICING_FILE = Path("/var/www/64dao/uploads/pricing.json")

DEFAULT_PRICING = {
    "title": "Полный отчёт 64 ДАО",
    "price": 14900,
    "currency": "₽",
    "description": "разовая оплата · НДС не облагается",
    "features": [
        {"label": "Диагностика", "value": "Метод 1 + Метод 2"},
        {"label": "PDF-отчёт", "value": "Включён"},
        {"label": "Онлайн-просмотр", "value": "Без ограничений"},
        {"label": "Срок готовности", "value": "До 30 минут"},
    ],
    "payment_enabled": False,
    "payment_note": "Платёжный шлюз (ЮKassa / Тинькофф) подключим после тестирования сайта. Пока что отчёты доступны в демо-режиме без оплаты.",
}


def _read_pricing() -> dict:
    try:
        return json.loads(PRICING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_PRICING.copy()


def _write_pricing(data: dict) -> None:
    PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRICING_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/pricing")
async def get_pricing(_: User = Depends(require_admin)):
    return _read_pricing()


@router.put("/pricing")
async def update_pricing(body: dict, _: User = Depends(require_admin)):
    _write_pricing(body)
    return {"ok": True}


# ── Email templates ───────────────────────────────────────────────────────────

TEMPLATES_FILE = Path("/var/www/64dao/uploads/email_templates.json")

DEFAULT_TEMPLATES = {
    "otp": {
        "subject": "{code} — код входа в 64DAO",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Ваш код для входа в систему <b>64DAO</b>:</p>"
            "<p style=\"font-size:28px;font-weight:700;letter-spacing:6px;color:#1a2540;\">{code}</p>"
            "<p>Код действует <b>10 минут</b>. Не передавайте его никому.</p>"
            "<p style=\"color:#999;font-size:12px;\">Если вы не запрашивали код — просто проигнорируйте это письмо.</p>"
        ),
        "description": "Отправляется при входе и регистрации. Доступные переменные: {name} — имя, {code} — код OTP.",
    },
    "welcome": {
        "subject": "Добро пожаловать в 64DAO",
        "body_html": (
            "<p>Добро пожаловать{name_part}!</p>"
            "<p>Вы успешно зарегистрировались в системе стратегической диагностики <b>64DAO</b>.</p>"
            "<p>Вы можете войти в свой кабинет и начать первую диагностику.</p>"
            "<p style=\"color:#999;font-size:12px;\">Команда 64DAO</p>"
        ),
        "description": "Отправляется один раз при регистрации. Доступные переменные: {name} — имя пользователя.",
    },
    "forgot_password": {
        "subject": "Сброс пароля 64DAO",
        "body_html": (
            "<p>Здравствуйте{name_part}!</p>"
            "<p>Мы получили запрос на сброс пароля для вашей учётной записи.</p>"
            "<p style=\"margin:24px 0;\">"
            "<a href=\"{reset_link}\" style=\"background:#1a2540;color:#fff;padding:12px 24px;"
            "border-radius:6px;text-decoration:none;font-weight:600;\">Сбросить пароль</a>"
            "</p>"
            "<p>Или скопируйте ссылку в браузер:<br>"
            "<span style=\"color:#1e3a8a;font-size:13px;\">{reset_link}</span></p>"
            "<p>Ссылка действует <b>1 час</b>.</p>"
            "<p style=\"color:#999;font-size:12px;\">Если вы не запрашивали сброс пароля — просто проигнорируйте это письмо.</p>"
        ),
        "description": "Отправляется при запросе сброса пароля. Доступные переменные: {name}, {name_part}, {reset_link} — ссылка на форму сброса.",
    },
}


def _read_templates() -> dict:
    defaults = {k: dict(v) for k, v in DEFAULT_TEMPLATES.items()}
    try:
        saved = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
        # Merge: saved templates take priority, but new default templates are added automatically
        result = dict(defaults)
        result.update(saved)
        return result
    except Exception:
        return defaults


def _write_templates(data: dict) -> None:
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/email-templates")
async def get_email_templates(_: User = Depends(require_admin)):
    return _read_templates()


@router.put("/email-templates")
async def update_email_templates(body: dict, _: User = Depends(require_admin)):
    _write_templates(body)
    return {"ok": True}


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

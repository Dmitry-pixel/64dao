import uuid
import re
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code:  str = Field(min_length=5, max_length=5, pattern=r"^\d{5}$")


class ResendOTPRequest(BaseModel):
    email: EmailStr


class ProfileUpdateRequest(BaseModel):
    # company_name допускает пустую строку: в кабинете поле можно очистить,
    # а min_length=1 превратил бы это в 422 и «Ошибка сохранения» без причины.
    full_name:    str = Field(min_length=1, max_length=255)
    company_name: str = Field(default="", max_length=255)


class RegisterRequest(BaseModel):
    # Пароля нет: вход по одноразовому коду на почту, см. app/auth.py.
    email:        EmailStr
    full_name:    str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id:           uuid.UUID
    email:        str
    full_name:    str | None
    company_name: str | None
    role:         str
    is_active:    bool = True
    created_at:   datetime


# ── Assessments ───────────────────────────────────────────────────────────────

class Method2Block(BaseModel):
    score: int = Field(ge=0, le=5)
    text:  str = Field(default="", max_length=5000)


class AssessmentCreate(BaseModel):
    method1_answers:     dict[str, str] | None = None
    method1_combination: str | None = None
    method2_data:        dict[str, Method2Block] | None = None
    finance_answers:     dict[str, int | None] | None = None
    company_name:        str | None = None
    company_id:          uuid.UUID | None = None
    status:              str = Field(default="completed")

    @field_validator("method1_combination")
    @classmethod
    def validate_combination(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"[AB]{6}", v):
            raise ValueError("Combination must be exactly 6 chars A or B")
        return v

    @field_validator("method1_answers")
    @classmethod
    def validate_answers(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        for key, val in v.items():
            if val not in ("A", "B"):
                raise ValueError(f"Answer for key {key} must be 'A' or 'B'")
        return v

    @field_validator("finance_answers")
    @classmethod
    def validate_finance_answers(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        for key, val in v.items():
            if val is not None and val not in (1, 2, 3, 4):
                raise ValueError(f"finance answer {key} must be 1..4 or null")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("draft", "completed"):
            raise ValueError("Status must be 'draft' or 'completed'")
        return v


class ContourSubmit(BaseModel):
    """Сабмит анкеты контура: 24 ответа, значения 1..4 или null («не знаю»).
    Полнота набора и лимит пропусков проверяются скорингом на сервере."""
    answers: dict[str, int | None]

    @field_validator("answers")
    @classmethod
    def validate_contour_answers(cls, v: dict) -> dict:
        for key, val in v.items():
            if val is not None and val not in (1, 2, 3, 4):
                raise ValueError(f"ответ {key} должен быть 1..4 или null")
        return v


class ReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id:           uuid.UUID
    pdf_filename: str | None
    generated_at: datetime | None
    created_at:   datetime


class ContourBrief(BaseModel):
    model_config = {"from_attributes": True}

    contour:     str
    combination: str
    created_at:  datetime


class AssessmentOut(BaseModel):
    model_config = {"from_attributes": True}

    id:                  uuid.UUID
    user_id:             uuid.UUID
    method1_combination: str | None
    method2_data:        dict[str, Any] | None
    method:              str = "method1"
    company_name:        str | None
    status:              str
    created_at:          datetime
    reports:             list[ReportOut] = []
    strategy_image_url:  str | None = None
    # Имя отличается от relationship Assessment.contours намеренно: иначе Pydantic
    # полез бы читать связь с ORM-объекта и уронил бы ленивую подгрузку в async.
    passed_contours:     list[ContourBrief] = []
    finance_combination: str | None = None
    finance_result:      dict[str, Any] | None = None
    # Повторная диагностика: счётчик права живёт на первичной, связь идёт
    # через parent_assessment_id. Кабинету это нужно, чтобы показать бейдж
    # и сгруппировать повторный отчёт с основным.
    company_id:           uuid.UUID | None = None
    parent_assessment_id: uuid.UUID | None = None
    is_followup:          bool = False
    followup_allowed:     int = 0
    followup_used:        int = 0


# ── Strategies ────────────────────────────────────────────────────────────────

class StrategyCreate(BaseModel):
    combination:                str = Field(min_length=6, max_length=6)
    title:                      str | None = None
    current_state:              dict[str, str] | None = None
    stratagema_title:           str | None = None
    lifecycle_stage:            str | None = None
    lifecycle_stage_index:      int | None = None
    lifecycle_description:      str | None = None
    lc_profit:                  str | None = None
    lc_strategy:                str | None = None
    lc_decisions:               str | None = None
    lc_consumer:                str | None = None
    lc_market:                  str | None = None
    lc_value:                   str | None = None
    scenario:                   dict[str, str] | None = None
    scenario_text:              str | None = None
    marketing_text:             str | None = None
    management_text:            str | None = None
    transition_title:           str | None = None
    transition_lifecycle_stage: str | None = None
    transition_description:     str | None = None
    hexagram_number:            int | None = None
    target_combination:         str | None = None
    assm_planning:              str | None = None
    assm_growth:                str | None = None
    assm_advertising:           str | None = None
    assm_feedback:              str | None = None
    assm_risk:                  str | None = None
    assm_product:               str | None = None
    assm_service:               str | None = None
    assm_startup:               str | None = None
    assm_investment:            str | None = None
    assm_contracts:             str | None = None
    assm_sync:                  str | None = None
    assm_creative:              str | None = None
    assm_interaction:           str | None = None
    assm_resources:             str | None = None
    assm_research:              str | None = None
    assm_trade:                 str | None = None
    assm_failures:              str | None = None
    assm_success:               str | None = None
    fin_pattern_essence:        str | None = None
    fin_pattern_mistake:        str | None = None
    is_published:               bool = False

    @field_validator("combination")
    @classmethod
    def validate_combination(cls, v: str) -> str:
        if not re.fullmatch(r"[AB]{6}", v):
            raise ValueError("Combination must be exactly 6 A/B chars")
        return v


class StrategyUpdate(StrategyCreate):
    combination: str | None = None  # type: ignore[assignment]


class StrategyOut(BaseModel):
    model_config = {"from_attributes": True}

    id:                         uuid.UUID
    combination:                str
    title:                      str | None
    current_state:              dict | None
    stratagema_title:           str | None
    lifecycle_stage:            str | None
    lifecycle_stage_index:      int | None
    lifecycle_description:      str | None
    lc_profit:                  str | None
    lc_strategy:                str | None
    lc_decisions:               str | None
    lc_consumer:                str | None
    lc_market:                  str | None
    lc_value:                   str | None
    scenario:                   dict | None
    scenario_text:              str | None
    marketing_text:             str | None
    management_text:            str | None
    transition_title:           str | None
    transition_lifecycle_stage: str | None
    transition_description:     str | None
    image_url:                  str | None
    hexagram_number:            int | None = None
    target_combination:         str | None = None
    # Целевая гексаграмма: производные поля, заполняет роутер из БД
    target_number:              int | None = None
    target_name:                str | None = None
    target_symbol:              str | None = None
    assm_planning:              str | None
    assm_growth:                str | None
    assm_advertising:           str | None
    assm_feedback:              str | None
    assm_risk:                  str | None
    assm_product:               str | None
    assm_service:               str | None
    assm_startup:               str | None
    assm_investment:            str | None
    assm_contracts:             str | None
    assm_sync:                  str | None
    assm_creative:              str | None
    assm_interaction:           str | None
    assm_resources:             str | None
    assm_research:              str | None
    assm_trade:                 str | None
    assm_failures:              str | None
    assm_success:               str | None
    fin_pattern_essence:        str | None = None
    fin_pattern_mistake:        str | None = None
    is_published:               bool
    updated_at:                 datetime


class StrategyListItem(BaseModel):
    model_config = {"from_attributes": True}

    id:           uuid.UUID
    combination:  str
    title:        str | None
    lifecycle_stage: str | None = None
    is_published: bool
    updated_at:   datetime


# ── Admin ─────────────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    type:       str
    timestamp:  str
    user_email: str
    user_name:  str | None
    detail:     str
    sub:        str | None = None


class AdminSetupRequest(BaseModel):
    setup_key: str
    email:     EmailStr
    full_name: str = Field(min_length=1)


class AdminStats(BaseModel):
    total_users:          int
    total_assessments:    int
    total_reports:        int
    published_strategies: int
    recent_users:         list[UserOut]
    recent_assessments:   list[AssessmentOut]
    orders_by_day:        list[dict] = []
    total_orders:         int = 0
    total_revenue:        float = 0


# ── Impersonation ─────────────────────────────────────────────────────────────

class ImpersonateStatus(BaseModel):
    active:        bool
    target_user:   UserOut | None = None
    admin_id:      uuid.UUID | None = None


# ── Generic ───────────────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    success: bool = True
    message: str  = ""


# ── FinContent (контент интерпретации финансовой функции) ─────────────────────

class FinContentOut(BaseModel):
    model_config = {"from_attributes": True}

    id:        uuid.UUID
    kind:      str
    key:       str
    contour:   str
    payload:   dict[str, Any]
    sort:      int
    is_active: bool


class FinContentUpsert(BaseModel):
    payload:   dict[str, Any]
    sort:      int = 0
    is_active: bool = True


class CompanyOut(BaseModel):
    id:               uuid.UUID
    name:             str
    assessment_count: int = 0
    latest_at:        datetime | None = None


class LifecycleStageOut(BaseModel):
    model_config = {"from_attributes": True}

    sort_order:  int
    name:        str
    description: str | None


# ── Access grants (временный бесплатный доступ) ────────────────────────────────

class AccessGrantCreate(BaseModel):
    """Выдача доступа: квота и срок обязательны (решение D1/D2)."""

    # Продукт гранта. Дефолт m12 — совместимость с формой админки до её
    # обновления; гранта «на всё» нет, для обоих продуктов выдаются два.
    product:    Literal["m12", "m3"] = "m12"
    quota:      int = Field(ge=1, le=50)
    expires_at: datetime
    reason:     str | None = Field(default=None, max_length=500)
    notify:     bool = True


class AccessGrantOut(BaseModel):
    """used/remaining/status считаются в app.access_grants, в БД их нет."""

    model_config = {"from_attributes": True}

    id:            uuid.UUID
    user_id:       uuid.UUID
    user_email:    str | None = None
    user_name:     str | None = None
    product:       str = "m12"
    quota:         int
    used:          int = 0
    remaining:     int = 0
    status:        str = "active"
    starts_at:     datetime
    expires_at:    datetime
    reason:        str | None = None
    created_at:    datetime
    revoked_at:    datetime | None = None
    email_sent_at: datetime | None = None

import uuid
import re
from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Шаг 1 OTP-flow: только email. Пароль не нужен."""
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    """Шаг 2 OTP-flow: email + 5-значный код. user_id НЕ передаём с фронта."""
    email: EmailStr
    code:  str = Field(min_length=5, max_length=5, pattern=r"^\d{5}$")


class ResendOTPRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    """Регистрация с паролем — используется при первичной регистрации."""
    email:        EmailStr
    password:     str = Field(min_length=8, max_length=128)
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
    created_at:   datetime


# ── Assessments ───────────────────────────────────────────────────────────────

class Method2Block(BaseModel):
    score: int = Field(ge=1, le=5)
    text:  str = Field(default="", max_length=5000)


class AssessmentCreate(BaseModel):
    method1_answers:     dict[str, str]
    method1_combination: str = Field(min_length=6, max_length=6)
    method2_data:        dict[str, Method2Block] | None = None
    status:              str = Field(default="completed")

    @field_validator("method1_combination")
    @classmethod
    def validate_combination(cls, v: str) -> str:
        if not re.fullmatch(r"[AB]{6}", v):
            raise ValueError("Combination must be exactly 6 chars A or B")
        return v

    @field_validator("method1_answers")
    @classmethod
    def validate_answers(cls, v: dict) -> dict:
        for key, val in v.items():
            if val not in ("A", "B"):
                raise ValueError(f"Answer for key {key} must be 'A' or 'B'")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("draft", "completed"):
            raise ValueError("Status must be 'draft' or 'completed'")
        return v


class ReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id:           uuid.UUID
    pdf_filename: str | None
    generated_at: datetime | None
    created_at:   datetime


class AssessmentOut(BaseModel):
    model_config = {"from_attributes": True}

    id:                  uuid.UUID
    user_id:             uuid.UUID
    method1_combination: str | None
    method2_data:        dict[str, Any] | None
    status:              str
    created_at:          datetime
    reports:             list[ReportOut] = []


# ── Strategies ────────────────────────────────────────────────────────────────

class StrategyCreate(BaseModel):
    combination:                str = Field(min_length=6, max_length=6)
    title:                      str | None = None
    current_state:              dict[str, str] | None = None
    stratagema_title:           str | None = None
    lifecycle_stage:            str | None = None
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
    # Предположения для связи с будущим
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
    # Предположения для связи с будущим
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
    is_published:               bool
    updated_at:                 datetime


class StrategyListItem(BaseModel):
    model_config = {"from_attributes": True}

    id:           uuid.UUID
    combination:  str
    title:        str | None
    is_published: bool
    updated_at:   datetime


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminSetupRequest(BaseModel):
    setup_key: str
    email:     EmailStr
    password:  str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class AdminStats(BaseModel):
    total_users:          int
    total_assessments:    int
    total_reports:        int
    published_strategies: int
    recent_users:         list[UserOut]
    recent_assessments:   list[AssessmentOut]


# ── Impersonation ─────────────────────────────────────────────────────────────

class ImpersonateStatus(BaseModel):
    active:        bool
    target_user:   UserOut | None = None
    admin_id:      uuid.UUID | None = None


# ── Generic ───────────────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    success: bool = True
    message: str  = ""

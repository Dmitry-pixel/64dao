import uuid
from datetime import datetime
from sqlalchemy import (
    String, Boolean, Text, Numeric, DateTime, Integer,
    ForeignKey, CheckConstraint, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from app.db import Base


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email:        Mapped[str]       = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash:Mapped[str | None]= mapped_column(Text, nullable=True)
    full_name:    Mapped[str | None]= mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None]= mapped_column(String(255), nullable=True)
    role:         Mapped[str]       = mapped_column(String(20), nullable=False, default="user")
    is_active:    Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="chk_user_role"),
    )

    otp_codes:   Mapped[list["OtpCode"]]   = relationship(back_populates="user", cascade="all, delete-orphan")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports:     Mapped[list["Report"]]     = relationship(back_populates="user", cascade="all, delete-orphan")
    orders:      Mapped[list["Order"]]      = relationship(back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ── OTP codes ─────────────────────────────────────────────────────────────────
class OtpCode(Base):
    __tablename__ = "otp_codes"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code:       Mapped[str]       = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    used:       Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="otp_codes")


# ── Strategies (64 combinations) ─────────────────────────────────────────────
LIFECYCLE_STAGE_ORDER = {
    "зарождение": 1,
    "расцвет":    2,
    "зрелость":   3,
    "упадок":     4,
    "обновление": 5,
}


class Strategy(Base):
    __tablename__ = "strategies"

    id:                         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    combination:                Mapped[str]       = mapped_column(String(6), unique=True, nullable=False, index=True)
    title:                      Mapped[str | None]= mapped_column(Text)
    current_state:              Mapped[dict | None]= mapped_column(JSONB)
    stratagema_title:           Mapped[str | None]= mapped_column(Text)
    lifecycle_stage:            Mapped[str | None]= mapped_column(String(100))
    lifecycle_description:      Mapped[str | None]= mapped_column(Text)
    lifecycle_stage_index:      Mapped[int | None]= mapped_column(Integer)
    # 6 блоков жизненного цикла (по одному на каждый вопрос диагностики)
    lc_profit:                  Mapped[str | None]= mapped_column(Text)  # Формирование прибыли
    lc_strategy:                Mapped[str | None]= mapped_column(Text)  # Рыночная стратегия
    lc_decisions:               Mapped[str | None]= mapped_column(Text)  # Принятие решений
    lc_consumer:                Mapped[str | None]= mapped_column(Text)  # Тип потребителя
    lc_market:                  Mapped[str | None]= mapped_column(Text)  # Статус рынка
    lc_value:                   Mapped[str | None]= mapped_column(Text)  # Тип ценности
    scenario:                   Mapped[dict | None]= mapped_column(JSONB)
    scenario_text:              Mapped[str | None]= mapped_column(Text)
    marketing_text:             Mapped[str | None]= mapped_column(Text)
    management_text:            Mapped[str | None]= mapped_column(Text)
    transition_title:           Mapped[str | None]= mapped_column(Text)
    transition_lifecycle_stage: Mapped[str | None]= mapped_column(String(100))
    transition_description:     Mapped[str | None]= mapped_column(Text)
    image_url:                  Mapped[str | None]= mapped_column(Text)
    # Слой C — паттерны финансовых гексаграмм (для текущей и результирующей)
    fin_pattern_essence:        Mapped[str | None]= mapped_column(Text)  # суть ситуации (1–2 предложения)
    fin_pattern_mistake:        Mapped[str | None]= mapped_column(Text)  # типичная ошибка (1 предложение)
    # Предположения для связи с будущим (13 тематических блоков)
    assm_planning:              Mapped[str | None]= mapped_column(Text)
    assm_growth:                Mapped[str | None]= mapped_column(Text)
    assm_advertising:           Mapped[str | None]= mapped_column(Text)
    assm_feedback:              Mapped[str | None]= mapped_column(Text)
    assm_risk:                  Mapped[str | None]= mapped_column(Text)
    assm_product:               Mapped[str | None]= mapped_column(Text)
    assm_service:               Mapped[str | None]= mapped_column(Text)
    assm_startup:               Mapped[str | None]= mapped_column(Text)
    assm_investment:            Mapped[str | None]= mapped_column(Text)
    assm_contracts:             Mapped[str | None]= mapped_column(Text)
    assm_sync:                  Mapped[str | None]= mapped_column(Text)
    assm_creative:              Mapped[str | None]= mapped_column(Text)
    assm_interaction:           Mapped[str | None]= mapped_column(Text)
    assm_resources:             Mapped[str | None]= mapped_column(Text)
    assm_research:              Mapped[str | None]= mapped_column(Text)
    assm_trade:                 Mapped[str | None]= mapped_column(Text)
    assm_failures:              Mapped[str | None]= mapped_column(Text)
    assm_success:               Mapped[str | None]= mapped_column(Text)

    @validates("lifecycle_stage")
    def _sync_lifecycle_index(self, key, value):
        self.lifecycle_stage_index = (
            LIFECYCLE_STAGE_ORDER.get(value.strip().lower()) if value else None
        )
        return value
    is_published:               Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    created_at:                 Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:                 Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(r"combination ~ '^[AB]{6}$'", name="chk_strategy_combination"),
    )


# ── FinContent (контент интерпретации фин. функции: слои A, B, D, E) ──────────
class FinContent(Base):
    __tablename__ = "fin_content"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    kind:       Mapped[str]       = mapped_column(String(20), nullable=False, index=True)
    key:        Mapped[str]       = mapped_column(String(40), nullable=False)
    contour:    Mapped[str]       = mapped_column(String(20), nullable=False, server_default="common")
    payload:    Mapped[dict]      = mapped_column(JSONB, nullable=False)
    sort:       Mapped[int]       = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active:  Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("kind", "key", "contour", name="uq_fin_content_kind_key_contour"),
        CheckConstraint(
            "contour IN ('common','finance','product','market','process')",
            name="chk_fin_content_contour",
        ),
        CheckConstraint(
            "kind IN ('tonality','quadrant','trigram','tension_rule','action_package')",
            name="chk_fin_content_kind",
        ),
    )


# ── Assessments ───────────────────────────────────────────────────────────────
class Assessment(Base):
    __tablename__ = "assessments"

    id:                  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    method1_answers:     Mapped[dict | None]= mapped_column(JSONB)
    method1_combination: Mapped[str | None]= mapped_column(String(6))
    method2_data:        Mapped[dict | None]= mapped_column(JSONB)
    method:              Mapped[str]       = mapped_column(String(10), nullable=False, server_default="method1")
    company_name:        Mapped[str | None]= mapped_column(String(255), nullable=True)
    status:              Mapped[str]       = mapped_column(String(20), nullable=False, default="draft")
    created_at:          Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:          Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('draft','completed','paid')", name="chk_assessment_status"),
        CheckConstraint("method IN ('method1','method2')", name="assessments_method_check"),
        CheckConstraint(r"method1_combination IS NULL OR method1_combination ~ '^[AB]{6}$'", name="chk_assessment_combination"),
    )

    user:    Mapped["User"]          = relationship(back_populates="assessments")
    reports: Mapped[list["Report"]]  = relationship(back_populates="assessment", cascade="all, delete-orphan")
    contours: Mapped[list["AssessmentContour"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")
    orders:  Mapped[list["Order"]]   = relationship(back_populates="assessment", cascade="all, delete-orphan")


# ── Assessment contours (мультиконтурная диагностика Метода 1) ───────────────
class AssessmentContour(Base):
    __tablename__ = "assessment_contours"

    id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    contour:       Mapped[str]       = mapped_column(String(20), nullable=False)
    answers:       Mapped[dict]      = mapped_column(JSONB, nullable=False)
    result:        Mapped[dict]      = mapped_column(JSONB, nullable=False)
    combination:   Mapped[str]       = mapped_column(String(6), nullable=False)
    created_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("assessment_id", "contour", name="uq_contour_per_assessment"),
        CheckConstraint("contour IN ('finance','product','market','process')", name="chk_contour_name"),
        CheckConstraint(r"combination ~ '^[AB]{6}$'", name="chk_contour_combination"),
        CheckConstraint("jsonb_typeof(answers) = 'object'", name="chk_contour_answers_obj"),
        CheckConstraint("jsonb_typeof(result) = 'object'", name="chk_contour_result_obj"),
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="contours")


# ── Reports ───────────────────────────────────────────────────────────────────
class Report(Base):
    __tablename__ = "reports"

    id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    user_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pdf_path:      Mapped[str | None]= mapped_column(Text)           # локальный путь
    pdf_filename:  Mapped[str | None]= mapped_column(String(255))    # имя файла для скачивания
    generated_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    assessment: Mapped["Assessment"] = relationship(back_populates="reports")
    user:       Mapped["User"]       = relationship(back_populates="reports")


# ── Orders (платёжный модуль — на будущее) ────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    id:            Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:       Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    amount:        Mapped[float]       = mapped_column(Numeric(10, 2), nullable=False, default=5500.00)
    currency:      Mapped[str]         = mapped_column(String(3), nullable=False, default="RUB")
    status:        Mapped[str]         = mapped_column(String(20), nullable=False, default="pending")
    payment_id:    Mapped[str | None]  = mapped_column(String(255))
    tochka_operation_id: Mapped[str | None] = mapped_column(String(255))
    tochka_payment_link: Mapped[str | None] = mapped_column(String(500))
    merchant_id:         Mapped[str | None] = mapped_column(String(255))
    webhook_payload:     Mapped[dict | None] = mapped_column(JSONB)
    paid_at:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at:    Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('pending','paid','failed','refunded')", name="chk_order_status"),
    )

    user:       Mapped["User"]       = relationship(back_populates="orders")
    assessment: Mapped["Assessment"] = relationship(back_populates="orders")


# ── Sample-report leads (заявки на пример отчёта) ─────────────────────────────
class SampleLead(Base):
    __tablename__ = "sample_leads"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name:       Mapped[str]       = mapped_column(String(200), nullable=False)
    channel:    Mapped[str]       = mapped_column(String(20), nullable=False)   # email | telegram | max
    address:    Mapped[str]       = mapped_column(String(320), nullable=False)
    consent:    Mapped[bool]      = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    ip:         Mapped[str | None]= mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("channel IN ('email','telegram','max')", name="chk_sample_lead_channel"),
    )



# ── Lifecycle stages (справочник стадий жизненного цикла) ────────────────────
class LifecycleStage(Base):
    __tablename__ = "lifecycle_stages"

    id:          Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    sort_order:  Mapped[int]        = mapped_column(Integer, nullable=False, unique=True)
    name:        Mapped[str]        = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


# ── Subscriptions (доступ к разделу «Динамика», роадмап 3.1) ──────────────────
class Subscription(Base):
    __tablename__ = "subscriptions"

    id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:    Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # NULL = выдана вручную админом (без заказа); при оплате — ссылка на orders.id
    order_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    starts_at:  Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at:    Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False)
    status:     Mapped[str]              = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('active','expired','revoked')", name="chk_subscription_status"),
    )

    user: Mapped["User"] = relationship(back_populates="subscriptions")

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Boolean, Text, Numeric, DateTime,
    ForeignKey, CheckConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    created_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="chk_user_role"),
    )

    otp_codes:   Mapped[list["OtpCode"]]   = relationship(back_populates="user", cascade="all, delete-orphan")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports:     Mapped[list["Report"]]     = relationship(back_populates="user", cascade="all, delete-orphan")
    orders:      Mapped[list["Order"]]      = relationship(back_populates="user", cascade="all, delete-orphan")


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
class Strategy(Base):
    __tablename__ = "strategies"

    id:                         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    combination:                Mapped[str]       = mapped_column(String(6), unique=True, nullable=False, index=True)
    title:                      Mapped[str | None]= mapped_column(String(255))
    current_state:              Mapped[dict | None]= mapped_column(JSONB)
    stratagema_title:           Mapped[str | None]= mapped_column(String(255))
    lifecycle_stage:            Mapped[str | None]= mapped_column(String(100))
    lifecycle_description:      Mapped[str | None]= mapped_column(Text)
    scenario:                   Mapped[dict | None]= mapped_column(JSONB)
    scenario_text:              Mapped[str | None]= mapped_column(Text)
    marketing_text:             Mapped[str | None]= mapped_column(Text)
    management_text:            Mapped[str | None]= mapped_column(Text)
    transition_title:           Mapped[str | None]= mapped_column(String(255))
    transition_lifecycle_stage: Mapped[str | None]= mapped_column(String(100))
    transition_description:     Mapped[str | None]= mapped_column(Text)
    image_url:                  Mapped[str | None]= mapped_column(Text)
    is_published:               Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    created_at:                 Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:                 Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(r"combination ~ '^[AB]{6}$'", name="chk_strategy_combination"),
    )


# ── Assessments ───────────────────────────────────────────────────────────────
class Assessment(Base):
    __tablename__ = "assessments"

    id:                  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    method1_answers:     Mapped[dict | None]= mapped_column(JSONB)
    method1_combination: Mapped[str | None]= mapped_column(String(6))
    method2_data:        Mapped[dict | None]= mapped_column(JSONB)
    status:              Mapped[str]       = mapped_column(String(20), nullable=False, default="draft")
    created_at:          Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:          Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('draft','completed','paid')", name="chk_assessment_status"),
        CheckConstraint(r"method1_combination IS NULL OR method1_combination ~ '^[AB]{6}$'", name="chk_assessment_combination"),
    )

    user:    Mapped["User"]          = relationship(back_populates="assessments")
    reports: Mapped[list["Report"]]  = relationship(back_populates="assessment", cascade="all, delete-orphan")
    orders:  Mapped[list["Order"]]   = relationship(back_populates="assessment", cascade="all, delete-orphan")


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
    paid_at:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at:    Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('pending','paid','failed','refunded')", name="chk_order_status"),
    )

    user:       Mapped["User"]       = relationship(back_populates="orders")
    assessment: Mapped["Assessment"] = relationship(back_populates="orders")

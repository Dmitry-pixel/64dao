# -*- coding: utf-8 -*-
"""Журнал решений (Decision Log).

После отчёта клиент записывает, какой сценарий выбрал, что делает и какого
результата ждёт. К повторной диагностике он отмечает, что произошло.
Это цепочка «состояние → решение → новое состояние»: без записанного
решения повтор показывает только сдвиг, но не то, совпал ли он с замыслом.

source_id без внешнего ключа намеренно: запись ссылается на один из трёх
источников (assessments, m3_portfolios, m4_runs), и вид источника задаёт
method. Принадлежность источника пользователю проверяет API.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

METHODS = ("m1", "m3", "m4")
OUTCOMES = ("done", "partial", "not_done")


class Decision(Base):
    __tablename__ = "decisions"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                                  nullable=False, index=True)
    method:     Mapped[str]       = mapped_column(String(4), nullable=False)
    source_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario:   Mapped[str]       = mapped_column(Text, nullable=False)
    actions:    Mapped[str | None] = mapped_column(Text)
    expected:   Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                  onupdate=func.now(), nullable=False)
    # Заполняется к повторной диагностике.
    outcome:      Mapped[str | None] = mapped_column(String(10))
    outcome_note: Mapped[str | None] = mapped_column(Text)
    outcome_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("method IN ('m1','m3','m4')", name="chk_decision_method"),
        CheckConstraint("outcome IS NULL OR outcome IN ('done','partial','not_done')",
                        name="chk_decision_outcome"),
        Index("ix_decisions_source", "method", "source_id"),
    )

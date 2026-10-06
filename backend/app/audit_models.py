# -*- coding: utf-8 -*-
"""Журнал событий: действия администратора и смены статуса заказов.

Одна таблица на оба вида событий: смотреть их приходится вместе («кто
вернул деньги и что после этого стало с заказом»), а схема у них одна.

actor_id — без внешнего ключа намеренно. Журнал пишет middleware в
отдельной транзакции, и запись не должна зависеть от того, жива ли строка
пользователя; актёр к тому же сохраняется снимком email (actor_email).
Журнал только дописывается: ни один код его не правит и не удаляет.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at:  Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # 'admin' — действие администратора через API, 'order' — смена статуса заказа.
    kind:        Mapped[str]       = mapped_column(String(20), nullable=False)
    # Для admin: "PUT /api/admin/pricing". Для order: "order.status".
    action:      Mapped[str]       = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id:   Mapped[str | None] = mapped_column(String(100))
    actor_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_email: Mapped[str | None] = mapped_column(String(255))
    # Имперсонация: админ действовал от лица пользователя actor_*.
    impersonated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status_code: Mapped[int | None] = mapped_column(Integer)
    before:      Mapped[dict | None] = mapped_column(JSONB)
    after:       Mapped[dict | None] = mapped_column(JSONB)
    # Источник смены статуса заказа (webhook, status_poll, reconcile_job, ...).
    note:        Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
    )

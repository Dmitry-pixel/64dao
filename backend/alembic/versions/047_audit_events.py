# -*- coding: utf-8 -*-
"""047 Журнал действий администратора и истории статусов заказов

audit_events — одна таблица на два вида событий (kind = admin | order).
Пишут её middleware app.audit.AdminAuditMiddleware (каждый изменяющий
запрос администратора) и слушатель смены Order.status. Журнал только
дописывается (аудит 2026-10-06, R015, R006).

Revision ID: 047
Revises: 046
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("entity_type", sa.String(50)),
        sa.Column("entity_id", sa.String(100)),
        sa.Column("actor_id", UUID),
        sa.Column("actor_email", sa.String(255)),
        sa.Column("impersonated_by", UUID),
        sa.Column("status_code", sa.Integer),
        sa.Column("before", JSONB),
        sa.Column("after", JSONB),
        sa.Column("note", sa.Text),
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_table("audit_events")

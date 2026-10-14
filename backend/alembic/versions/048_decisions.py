# -*- coding: utf-8 -*-
"""048 Журнал решений клиента по отчётам (Decision Log)

decisions — что клиент решил по итогам отчёта (Методы 1, 3, 4) и что из
этого вышло к повторной диагностике. source_id без внешнего ключа: вид
источника задаёт method, принадлежность проверяет API.

Revision ID: 048
Revises: 047
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method", sa.String(4), nullable=False),
        sa.Column("source_id", UUID, nullable=False),
        sa.Column("scenario", sa.Text, nullable=False),
        sa.Column("actions", sa.Text),
        sa.Column("expected", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("outcome", sa.String(10)),
        sa.Column("outcome_note", sa.Text),
        sa.Column("outcome_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("method IN ('m1','m3','m4')", name="chk_decision_method"),
        sa.CheckConstraint("outcome IS NULL OR outcome IN ('done','partial','not_done')",
                           name="chk_decision_outcome"),
    )
    op.create_index("ix_decisions_user_id", "decisions", ["user_id"])
    op.create_index("ix_decisions_source", "decisions", ["method", "source_id"])


def downgrade() -> None:
    op.drop_index("ix_decisions_source", table_name="decisions")
    op.drop_index("ix_decisions_user_id", table_name="decisions")
    op.drop_table("decisions")

# -*- coding: utf-8 -*-
"""043 Метод 4: недостающие поля снимка результата

Расчёт (app/m4_engine.py) выдаёт больше, чем помещалось в снимок 042:
  top_gaps          — три главных разрыва (экспресс показывает именно их);
  cause_effect      — сопоставление причин (модули 1–9) и следствия (модуль 10);
  constraint_detail — сила ограничения и модули, которые оно блокирует;
  metrics           — названные клиентом числа (доля клиента, DSO и т. п.).

Отдельными колонками, а не одним JSON «прочее»: отчёт и динамика будут
выбирать их по имени, и неявная структура разошлась бы между рендерами.
Таблица новая и пустая, поэтому NOT NULL у top_gaps ставится сразу.

Revision ID: 043
Revises: 042
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB


def upgrade() -> None:
    op.add_column("m4_snapshots", sa.Column("top_gaps", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("m4_snapshots", sa.Column("cause_effect", JSONB, nullable=True))
    op.add_column("m4_snapshots", sa.Column("constraint_detail", JSONB, nullable=True))
    op.add_column("m4_snapshots", sa.Column("metrics", JSONB, nullable=True))


def downgrade() -> None:
    for col in ("metrics", "constraint_detail", "cause_effect", "top_gaps"):
        op.drop_column("m4_snapshots", col)

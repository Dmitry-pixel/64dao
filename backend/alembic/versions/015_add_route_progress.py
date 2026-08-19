"""add route_progress (feature F: чек-листы шагов маршрута)

Прогресс выполнения шагов маршрута перехода. Наличие строки = шаг выполнен.
Маршрут детерминирован (contour_route.build_route) и пересчитывается — в БД
храним только отметки, ключ шага (assessment_id, contour, line).

Revision ID: 015
Revises: 014
Create Date: 2026-07-23
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "route_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", UUID(as_uuid=True),
                  sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contour", sa.String(20), nullable=False),
        sa.Column("line", sa.Integer, nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("assessment_id", "contour", "line",
                            name="uq_route_progress_step"),
        sa.CheckConstraint("contour IN ('finance','product','market','process')",
                           name="chk_route_progress_contour"),
    )
    op.create_index("ix_route_progress_assessment_id", "route_progress",
                    ["assessment_id"])


def downgrade() -> None:
    op.drop_index("ix_route_progress_assessment_id", table_name="route_progress")
    op.drop_table("route_progress")

"""followup counters on assessments

Право на одну бесплатную повторную диагностику. Счётчик живёт на первичной
диагностике: он куплен вместе с конкретным отчётом, а не выдан пользователю
и не привязан к компании. При включении платежей каждая новая оплаченная
первичная диагностика принесёт собственное право, и лимит не заблокирует
того, кто заплатил второй раз.

Revision ID: 017
Revises: 016
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column(
        "parent_assessment_id", UUID(as_uuid=True),
        sa.ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True))
    op.add_column("assessments", sa.Column(
        "is_followup", sa.Boolean(), nullable=False,
        server_default=sa.text("false")))
    op.add_column("assessments", sa.Column(
        "followup_allowed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assessments", sa.Column(
        "followup_used", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_assessments_parent_assessment_id", "assessments",
                    ["parent_assessment_id"])
    op.create_check_constraint(
        "chk_assessment_followup_used", "assessments",
        "followup_used >= 0 AND followup_used <= followup_allowed")
    # Бэкфил: каждая завершённая диагностика получает право на один повтор.
    # Клиентов нет, данные тестовые, поэтому право выдаётся без разбора истории.
    op.execute("UPDATE assessments SET followup_allowed = 1 "
               "WHERE status IN ('completed','paid')")


def downgrade() -> None:
    op.drop_constraint("chk_assessment_followup_used", "assessments",
                       type_="check")
    op.drop_index("ix_assessments_parent_assessment_id",
                  table_name="assessments")
    op.drop_column("assessments", "followup_used")
    op.drop_column("assessments", "followup_allowed")
    op.drop_column("assessments", "is_followup")
    op.drop_column("assessments", "parent_assessment_id")

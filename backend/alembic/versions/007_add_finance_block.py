"""add finance block: strategies fin_pattern_*, fin_content table, assessments finance_*

Revision ID: 007
Revises: 006
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Слой C — паттерны гексаграмм на strategies
    op.add_column("strategies", sa.Column("fin_pattern_essence", sa.Text(), nullable=True))
    op.add_column("strategies", sa.Column("fin_pattern_mistake", sa.Text(), nullable=True))

    # 2) Универсальная таблица контента интерпретации (слои A, B, D, E)
    op.create_table(
        "fin_content",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("kind", "key", name="uq_fin_content_kind_key"),
        sa.CheckConstraint(
            "kind IN ('tonality','quadrant','trigram','tension_rule','action_package')",
            name="chk_fin_content_kind",
        ),
    )
    op.create_index("ix_fin_content_kind", "fin_content", ["kind"])

    # 3) Финансовые поля на assessments
    op.add_column("assessments", sa.Column("finance_answers", JSONB(), nullable=True))
    op.add_column("assessments", sa.Column("finance_result", JSONB(), nullable=True))
    op.add_column("assessments", sa.Column("finance_combination", sa.String(6), nullable=True))
    op.create_check_constraint(
        "chk_assessment_finance_combination",
        "assessments",
        r"finance_combination IS NULL OR finance_combination ~ '^[AB]{6}$'",
    )


def downgrade() -> None:
    op.drop_constraint("chk_assessment_finance_combination", "assessments", type_="check")
    op.drop_column("assessments", "finance_combination")
    op.drop_column("assessments", "finance_result")
    op.drop_column("assessments", "finance_answers")

    op.drop_index("ix_fin_content_kind", table_name="fin_content")
    op.drop_table("fin_content")

    op.drop_column("strategies", "fin_pattern_mistake")
    op.drop_column("strategies", "fin_pattern_essence")

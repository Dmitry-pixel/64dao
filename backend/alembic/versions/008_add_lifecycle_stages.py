"""add lifecycle_stages reference table and strategies.lifecycle_stage_index

Revision ID: 008
Revises: 007
"""
import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

STAGES = [
    (1, "Зарождение", "Модель ещё проверяется, структура подвижна, ресурс уходит на поиск повторяемого спроса."),
    (2, "Расцвет", "Спрос подтверждён, рост опережает возможности структуры. Узкое место в управляемости, а не в рынке."),
    (3, "Зрелость", "Рост замедлился, структура выручки стабильна. Основной риск — переход в упадок без обновления продукта."),
    (4, "Упадок", "Прежняя модель теряет отдачу, издержки растут быстрее выручки, решения смещаются к сокращению."),
    (5, "Обновление", "Формируется новая опора роста на базе сохранённого ресурса. Ключевой вопрос — что демонтировать."),
]


def upgrade() -> None:
    op.create_table(
        "lifecycle_stages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("sort_order", name="uq_lifecycle_stages_sort_order"),
    )
    tbl = sa.table(
        "lifecycle_stages",
        sa.column("sort_order", sa.Integer),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(tbl, [
        {"sort_order": s, "name": n, "description": d} for s, n, d in STAGES
    ])
    op.add_column(
        "strategies",
        sa.Column("lifecycle_stage_index", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("strategies", "lifecycle_stage_index")
    op.drop_table("lifecycle_stages")

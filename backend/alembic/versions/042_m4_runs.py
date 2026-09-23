# -*- coding: utf-8 -*-
"""042 Метод 4: прогоны, ответы, снимок результата

m4_runs — один проход анкеты по одной компании: экспресс (бесплатно,
20 вопросов) или полная диагностика из пакета «Метод 3 + Метод 4». Оплата —
привязкой к заказу продукта m3, как у m3_portfolios. Право на повтор хранится
в самом прогоне, как у assessments: свой счётчик у Метода 4, общего на пакет
нет.

m4_answers — ответы; «Не знаю» хранится значением 'unknown', перенесённый в
повторе ответ — строкой с source='carried_over'.

m4_snapshots — рассчитанный результат, единственный источник для веба и PDF.

Существующие таблицы не меняются. Откат удаляет только таблицы Метода 4.

Revision ID: 042
Revises: 041
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "m4_runs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("m3_portfolio_id", UUID, nullable=True),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="draft"),
        sa.Column("order_id", UUID, nullable=True),
        sa.Column("grant_id", UUID, nullable=True),
        sa.Column("is_followup", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("parent_run_id", UUID, nullable=True),
        sa.Column("followup_allowed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("followup_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reduced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("profile_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("item_versions", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["m3_portfolio_id"], ["m3_portfolios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["grant_id"], ["access_grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_run_id"], ["m4_runs.id"], ondelete="SET NULL"),
        sa.CheckConstraint("mode IN ('express','full')", name="chk_m4_run_mode"),
        sa.CheckConstraint("status IN ('draft','filled','calculated')", name="chk_m4_run_status"),
        sa.CheckConstraint("followup_used >= 0 AND followup_used <= followup_allowed",
                           name="chk_m4_run_followup_used"),
        sa.CheckConstraint("mode = 'full' OR (order_id IS NULL AND grant_id IS NULL)",
                           name="chk_m4_run_express_unpaid"),
        sa.CheckConstraint("NOT is_followup OR parent_run_id IS NOT NULL", name="chk_m4_run_followup_parent"),
    )
    for col in ("user_id", "company_id", "m3_portfolio_id", "order_id", "grant_id", "parent_run_id"):
        op.create_index(f"ix_m4_runs_{col}", "m4_runs", [col])

    op.create_table(
        "m4_answers",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID, nullable=False),
        sa.Column("question_code", sa.String(8), nullable=False),
        sa.Column("value", sa.String(32), nullable=True),
        sa.Column("numeric_value", sa.Numeric(16, 2), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="direct"),
        sa.Column("item_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["m4_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_code"], ["m4_questions.code"], ondelete="RESTRICT"),
        sa.UniqueConstraint("run_id", "question_code", name="uq_m4_answer"),
        sa.CheckConstraint("value IS NOT NULL OR numeric_value IS NOT NULL", name="chk_m4_answer_present"),
        sa.CheckConstraint("source IN ('direct','carried_over','reused')", name="chk_m4_answer_source"),
    )
    op.create_index("ix_m4_answers_run_id", "m4_answers", ["run_id"])

    op.create_table(
        "m4_snapshots",
        sa.Column("run_id", UUID, primary_key=True),
        sa.Column("calc_version", sa.String(16), nullable=False),
        sa.Column("module_scores", postgresql.JSONB(), nullable=False),
        sa.Column("constraint_module", sa.SmallInteger(), nullable=True),
        sa.Column("fired_rules", postgresql.JSONB(), nullable=False),
        sa.Column("unverified_rules", postgresql.JSONB(), nullable=False),
        sa.Column("confidence_index", sa.SmallInteger(), nullable=False),
        sa.Column("confidence_components", postgresql.JSONB(), nullable=False),
        sa.Column("resistance_factor", sa.Numeric(3, 2), nullable=False),
        sa.Column("priority_queue", postgresql.JSONB(), nullable=False),
        sa.Column("cross_check", postgresql.JSONB(), nullable=True),
        sa.Column("reduced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["m4_runs.id"], ondelete="CASCADE"),
        sa.CheckConstraint("constraint_module IS NULL OR (constraint_module >= 1 AND constraint_module <= 9)",
                           name="chk_m4_snapshot_constraint_module"),
        sa.CheckConstraint("confidence_index >= 0 AND confidence_index <= 100",
                           name="chk_m4_snapshot_confidence"),
        sa.CheckConstraint("resistance_factor >= 1.0 AND resistance_factor <= 2.0",
                           name="chk_m4_snapshot_resistance"),
    )


def downgrade() -> None:
    op.drop_table("m4_snapshots")
    op.drop_index("ix_m4_answers_run_id", table_name="m4_answers")
    op.drop_table("m4_answers")
    for col in ("user_id", "company_id", "m3_portfolio_id", "order_id", "grant_id", "parent_run_id"):
        op.drop_index(f"ix_m4_runs_{col}", table_name="m4_runs")
    op.drop_table("m4_runs")

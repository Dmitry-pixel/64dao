# -*- coding: utf-8 -*-
"""038 Метод 4: модули, банк вопросов, варианты ответов

Первая миграция Метода 4. Только хранение контента: расчёт, прогоны и
снимки — отдельными миграциями, чтобы каждую можно было откатить по одной.

Почему три таблицы, а не один jsonb: вопросы правятся в админке поштучно,
на коды вопросов ссылаются правила противоречий, а на значения вариантов —
сохранённые ответы. В jsonb ни первое, ни второе не проверяется базой.

Варианта «Не знаю» в m4_question_options нет намеренно — его подставляет код
по полям unknown_* вопроса. Ограничение chk_m4_option_not_unknown не даёт
завести его руками: иначе он разойдётся между вопросами.

Revision ID: 038
Revises: 037
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "m4_modules",
        sa.Column("code", sa.SmallInteger(), primary_key=True),
        sa.Column("slug", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("client_question", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("is_effect", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("code >= 1 AND code <= 10", name="chk_m4_module_code"),
    )

    op.create_table(
        "m4_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(8), nullable=False, unique=True),
        sa.Column("module_code", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("weight", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("is_fact", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tier", sa.String(2), nullable=False),
        sa.Column("reverse", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score_neutral", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score_excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("affects", sa.String(24), nullable=True),
        sa.Column("unknown_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("unknown_score", sa.SmallInteger(), nullable=True),
        sa.Column("unknown_confidence_penalty", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("metric_code", sa.String(48), nullable=True),
        sa.Column("threshold_based", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("control_pair", sa.String(8), nullable=True),
        sa.Column("applies_when", postgresql.JSONB(), nullable=True),
        sa.Column("construct_code", sa.String(48), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("item_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["module_code"], ["m4_modules.code"], ondelete="RESTRICT"),
        sa.CheckConstraint("type IN ('bool','scale3','choice','number','money')",
                           name="chk_m4_question_type"),
        sa.CheckConstraint("tier IN ('u0','u1')", name="chk_m4_question_tier"),
        sa.CheckConstraint("weight >= 1 AND weight <= 3", name="chk_m4_question_weight"),
        sa.CheckConstraint("unknown_score IS NULL OR (unknown_score >= 0 AND unknown_score <= 100)",
                           name="chk_m4_question_unknown_score"),
        sa.CheckConstraint("unknown_allowed OR unknown_score IS NULL",
                           name="chk_m4_question_unknown_consistency"),
        sa.CheckConstraint("affects IS NULL OR score_excluded", name="chk_m4_question_affects"),
    )
    op.create_index("ix_m4_questions_module_code", "m4_questions", ["module_code"])
    op.create_index("ix_m4_questions_construct_code", "m4_questions", ["construct_code"])

    op.create_table(
        "m4_question_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value", sa.String(32), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("sort", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["question_id"], ["m4_questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("question_id", "value", name="uq_m4_option_value"),
        sa.CheckConstraint("value <> 'unknown'", name="chk_m4_option_not_unknown"),
        sa.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)",
                           name="chk_m4_option_score"),
    )
    op.create_index("ix_m4_question_options_question_id", "m4_question_options", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_m4_question_options_question_id", table_name="m4_question_options")
    op.drop_table("m4_question_options")
    op.drop_index("ix_m4_questions_construct_code", table_name="m4_questions")
    op.drop_index("ix_m4_questions_module_code", table_name="m4_questions")
    op.drop_table("m4_questions")
    op.drop_table("m4_modules")

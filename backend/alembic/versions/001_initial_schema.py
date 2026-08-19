"""Initial schema with seed data (AAABAA strategy)

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email",         sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text,        nullable=True),
        sa.Column("full_name",     sa.String(255), nullable=True),
        sa.Column("company_name",  sa.String(255), nullable=True),
        sa.Column("role",          sa.String(20),  nullable=False, server_default="user"),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('user','admin')", name="chk_user_role"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── otp_codes ──────────────────────────────────────────────────────────────
    op.create_table(
        "otp_codes",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code",       sa.String(10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used",       sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_otp_user_id",  "otp_codes", ["user_id"])
    op.create_index("ix_otp_expires",  "otp_codes", ["expires_at"])

    # ── strategies ─────────────────────────────────────────────────────────────
    op.create_table(
        "strategies",
        sa.Column("id",                         postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("combination",                sa.String(6),  nullable=False),
        sa.Column("title",                      sa.String(255), nullable=True),
        sa.Column("current_state",              postgresql.JSONB, nullable=True),
        sa.Column("stratagema_title",           sa.String(255), nullable=True),
        sa.Column("lifecycle_stage",            sa.String(100), nullable=True),
        sa.Column("lifecycle_description",      sa.Text, nullable=True),
        sa.Column("scenario",                   postgresql.JSONB, nullable=True),
        sa.Column("scenario_text",              sa.Text, nullable=True),
        sa.Column("marketing_text",             sa.Text, nullable=True),
        sa.Column("management_text",            sa.Text, nullable=True),
        sa.Column("transition_title",           sa.String(255), nullable=True),
        sa.Column("transition_lifecycle_stage", sa.String(100), nullable=True),
        sa.Column("transition_description",     sa.Text, nullable=True),
        sa.Column("image_url",                  sa.Text, nullable=True),
        sa.Column("is_published",               sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at",                 sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",                 sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("combination", name="uq_strategy_combination"),
        sa.CheckConstraint(r"combination ~ '^[AB]{6}$'", name="chk_strategy_combination"),
    )
    op.create_index("ix_strategies_combination", "strategies", ["combination"])

    # ── assessments ────────────────────────────────────────────────────────────
    op.create_table(
        "assessments",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",             postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method1_answers",     postgresql.JSONB, nullable=True),
        sa.Column("method1_combination", sa.String(6), nullable=True),
        sa.Column("method2_data",        postgresql.JSONB, nullable=True),
        sa.Column("status",              sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",          sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('draft','completed','paid')", name="chk_assessment_status"),
        sa.CheckConstraint(r"method1_combination IS NULL OR method1_combination ~ '^[AB]{6}$'", name="chk_assessment_combination"),
    )
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"])

    # ── reports ────────────────────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pdf_path",      sa.Text, nullable=True),
        sa.Column("pdf_filename",  sa.String(255), nullable=True),
        sa.Column("generated_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"],       ["users.id"],       ondelete="CASCADE"),
    )
    op.create_index("ix_reports_user_id",       "reports", ["user_id"])
    op.create_index("ix_reports_assessment_id", "reports", ["assessment_id"])

    # ── orders ─────────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount",        sa.Numeric(10, 2), nullable=False, server_default="5500.00"),
        sa.Column("currency",      sa.String(3),  nullable=False, server_default="RUB"),
        sa.Column("status",        sa.String(20), nullable=False, server_default="pending"),
        sa.Column("payment_id",    sa.String(255), nullable=True),
        sa.Column("paid_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"],       ["users.id"],       ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('pending','paid','failed','refunded')", name="chk_order_status"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])

    # ── Seed: стратегия AAABAA ─────────────────────────────────────────────────
    op.execute("""
        INSERT INTO strategies (
            combination, title,
            current_state,
            stratagema_title, lifecycle_stage, lifecycle_description,
            scenario, scenario_text, marketing_text, management_text,
            transition_title, transition_lifecycle_stage, transition_description,
            is_published
        ) VALUES (
            'AAABAA', 'Развитие',
            '{"value_type":"Прорывной","market_status":"Хорошо развитый","consumer_type":"Потребительский (B2C)","organization":"Иерархическое управление","strategy":"Быстрый последователь","goal":"Увеличить прибыль за счет увеличения выручки"}',
            'РАЗВИТИЕ', 'РОСТ',
            'Это время для уточнения, а не революции. Гексаграмма РАЗВИТИЕ благоприятствует небольшим движениям, микро-корректировкам и тонкому планированию. Не спешите взбираться на масштаб. Улучшите системы, упростите своё предложение, пересмотрите детали.',
            '{"innovation_strategy":"Мониторинг потребностей клиентов","innovation_type":"Инновационная бизнес-модель","value_discipline":"Операционное совершенство","leadership_principles":"Максимизация прибыли","growth_strategy":"Расширение","focus":"Эмоции"}',
            'Фирмы с данной стратагемой могут применять операционные технологии для снижения издержек, а также для увеличения доходов.',
            'Неблагоприятный. Будьте осмотрительны со всеми ресурсами. Следует избегать расходов без гарантированной отдачи.',
            'Философия Кайдзен: непрерывное совершенствование через небольшие улучшения.',
            'ГАРМОНИЯ И ДОВЕРИЕ', 'СОТРУДНИЧЕСТВО',
            'Целевое стратегическое состояние: переход к модели, основанной на доверии партнёров.',
            true
        )
    """)


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("reports")
    op.drop_table("assessments")
    op.drop_table("strategies")
    op.drop_table("otp_codes")
    op.drop_table("users")

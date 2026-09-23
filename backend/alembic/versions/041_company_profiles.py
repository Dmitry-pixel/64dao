# -*- coding: utf-8 -*-
"""041 Профиль диагностируемой компании

Один к одному с companies. Привязка к компании, а не к пользователю: у
консультанта несколько компаний под одним аккаунтом, и профиль одного клиента
не должен попасть в отчёт другого.

Обязательно одно поле — revenue_model: оно управляет показом части вопросов
Метода 4. Отрасль, диапазон выручки, численность и число клиентов —
необязательные: ни на один вопрос, правило или балл сегодня не влияют.

Таблица новая, companies не меняется: откат не задевает ни одну существующую
компанию.

Revision ID: 041
Revises: 040
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("revenue_model", sa.String(16), nullable=False),
        sa.Column("industry_id", sa.Integer(), nullable=True),
        sa.Column("revenue_range", sa.String(12), nullable=True),
        sa.Column("headcount", sa.Integer(), nullable=True),
        sa.Column("active_clients", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.CheckConstraint("revenue_model IN ('one_off','repeat','subscription')",
                           name="chk_company_profile_revenue_model"),
        sa.CheckConstraint(
            "revenue_range IS NULL OR revenue_range IN ('lt_10m','10_50m','50_300m','gt_300m')",
            name="chk_company_profile_revenue_range"),
        sa.CheckConstraint("headcount IS NULL OR headcount >= 0", name="chk_company_profile_headcount"),
        sa.CheckConstraint("active_clients IS NULL OR active_clients >= 0",
                           name="chk_company_profile_active_clients"),
    )


def downgrade() -> None:
    op.drop_table("company_profiles")

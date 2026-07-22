"""add companies + assessments.company_id + backfill (роадмап 3.1)

Best-effort группировка legacy-диагностик по (user_id, company_name). Пустое
имя → «Без названия» (одна компания на пользователя). Опечатки/разные написания
объединяются вручную позже (UI «объединить компании», §10 плана).

Revision ID: 013
Revises: 012
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

_NAME = "COALESCE(NULLIF(TRIM(company_name), ''), 'Без названия')"


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "name", name="uq_company_user_name"),
    )
    op.create_index("ix_companies_user_id", "companies", ["user_id"])

    op.add_column("assessments",
                  sa.Column("company_id", UUID(as_uuid=True),
                            sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_assessments_company_id", "assessments", ["company_id"])

    # Backfill: компания на каждую уникальную пару (user_id, нормализованное имя)
    op.execute(f"""
        INSERT INTO companies (id, user_id, name, created_at)
        SELECT gen_random_uuid(), user_id, {_NAME} AS cname, MIN(created_at)
        FROM assessments
        GROUP BY user_id, {_NAME}
    """)
    op.execute(f"""
        UPDATE assessments a SET company_id = c.id
        FROM companies c
        WHERE c.user_id = a.user_id AND c.name = {_NAME}
    """)


def downgrade() -> None:
    op.drop_index("ix_assessments_company_id", table_name="assessments")
    op.drop_column("assessments", "company_id")
    op.drop_index("ix_companies_user_id", table_name="companies")
    op.drop_table("companies")

"""add reminder idempotency columns (PR6)

Идемпотентность email-напоминаний:
- subscriptions.expiry_reminder_sent_at — «за 14 дней до конца подписки»
  (одноразово на подписку; новая подписка = новая строка = NULL).
- companies.repeat_reminder_sent_at — «пора повторить»; авто-перевзвод, т.к.
  сравнивается с датой последней диагностики компании.

Revision ID: 014
Revises: 013
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("expiry_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("repeat_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "repeat_reminder_sent_at")
    op.drop_column("subscriptions", "expiry_reminder_sent_at")

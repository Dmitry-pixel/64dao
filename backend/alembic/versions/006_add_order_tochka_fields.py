"""add tochka fields to orders

Устраняет дрейф схемы: колонки Order.tochka_operation_id / tochka_payment_link /
merchant_id / webhook_payload есть в models.py, но не были заведены ни одной
миграцией (001-005). На проде они были добавлены вручную SQL, поэтому здесь
используется ADD COLUMN IF NOT EXISTS - миграция идемпотентна.

Revision ID: 006
Revises: 005
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tochka_operation_id VARCHAR(255)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tochka_payment_link VARCHAR(500)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS merchant_id         VARCHAR(255)")
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS webhook_payload     JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS webhook_payload")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS merchant_id")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS tochka_payment_link")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS tochka_operation_id")

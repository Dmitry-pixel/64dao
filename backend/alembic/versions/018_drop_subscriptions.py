"""drop subscriptions table

Подписка как продукт отменена: повторная диагностика и раздел «Динамика»
входят в стоимость основной диагностики. Код подписки удалён ранее, таблица
держалась ради возможности отката. На момент удаления она пуста.

downgrade воссоздаёт структуру, но не данные: строк не было, восстанавливать
нечего.

Revision ID: 018
Revises: 017
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")


def downgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", UUID(as_uuid=True),
                  sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("expiry_reminder_sent_at", sa.DateTime(timezone=True),
                  nullable=True),
        sa.CheckConstraint("status IN ('active','expired','revoked')",
                           name="chk_subscription_status"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

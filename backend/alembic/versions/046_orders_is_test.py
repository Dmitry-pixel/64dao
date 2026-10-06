# -*- coding: utf-8 -*-
"""046 Признак тестового заказа

Тестовый платёж на 1 ₽ из админки раньше был неотличим от настоящего:
давал кредиты и входил в выручку и статистику. Теперь у заказа есть
is_test, и эти запросы его исключают (аудит 2026-10-06, R009).

Задним числом помечаются заказы на 1 ₽: реальная цена такой не бывает.
На 2026-10-06 это три заказа администратора, все возвращены.

Revision ID: 046
Revises: 045
"""
import sqlalchemy as sa

from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("is_test", sa.Boolean, nullable=False,
                                      server_default=sa.text("false")))
    op.execute("UPDATE orders SET is_test = true WHERE amount = 1.00")


def downgrade() -> None:
    op.drop_column("orders", "is_test")

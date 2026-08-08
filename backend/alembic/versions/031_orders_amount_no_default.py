"""Сумма заказа перестаёт иметь дефолт

В схеме с самого начала стоял server_default="5500.00" — цена, от которой
давно отказались. В models.py к нему прилагался python-дефолт с тем же
числом. Оба недостижимы: и create_payment, и test-create передают сумму
явно. Но это мина: место, где сумму забудут передать, молча создаст заказ
на 5500 ₽ вместо падения.

Ровно от этого в том же классе защищён product — «дефолта нет намеренно:
пропущенный аргумент должен падать, а не молча создавать заказ не того
продукта». К сумме то же правило не применили.

Существующие строки не трогаются: снятие дефолта на них не влияет.

Revision ID: 031
Revises: 030
"""
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("orders", "amount", server_default=None)


def downgrade() -> None:
    op.alter_column("orders", "amount", server_default="5500.00")

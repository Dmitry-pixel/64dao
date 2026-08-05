"""m3_portfolios.order_id / grant_id — чем оплачен расчёт портфеля

Симметрично assessments.order_id (ревизия 022) и assessments.grant_id
(ревизия 021): чем оплачено, то и списано. Расход кредита Метода 3 считается
по этим колонкам, а не счётчиком, — как и в платном контуре Методов 1 и 2.

Следствия ровно те же: возврат заказа возвращает квоту автоматически,
счётчик не может разойтись с фактом, отзыв доступа при рефанде находит
именно те портфели, которые были оплачены возвращённым заказом.

ondelete='SET NULL', а не CASCADE: удаление заказа не должно уносить
результат диагностики. Портфель при этом станет «ничем не оплачен» и снова
попадёт под проверку кредитов, что и требуется.

Revision ID: 027
Revises: 026
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("m3_portfolios", sa.Column(
        "order_id", UUID(as_uuid=True),
        sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True))
    op.add_column("m3_portfolios", sa.Column(
        "grant_id", UUID(as_uuid=True),
        sa.ForeignKey("access_grants.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_m3_portfolios_order_id", "m3_portfolios", ["order_id"])
    op.create_index("ix_m3_portfolios_grant_id", "m3_portfolios", ["grant_id"])


def downgrade() -> None:
    op.drop_index("ix_m3_portfolios_grant_id", table_name="m3_portfolios")
    op.drop_index("ix_m3_portfolios_order_id", table_name="m3_portfolios")
    op.drop_column("m3_portfolios", "grant_id")
    op.drop_column("m3_portfolios", "order_id")

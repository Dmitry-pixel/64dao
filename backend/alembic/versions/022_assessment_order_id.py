"""assessments.order_id — привязка диагностики к оплаченному заказу

Расход платного кредита считался глобально: paid_orders * REPORTS_PER_ORDER
минус все завершённые диагностики пользователя. Поэтому диагностика
возвращённого заказа продолжала вычитаться из кредитов будущих покупок, а
отзыв доступа при возврате приходилось вести по компании — точной связи
диагностики с заказом в схеме не было.

Колонка симметрична grant_id: чем оплачено, то и списано.

Бэкфил раскладывает существующие завершённые диагностики по оплаченным
заказам того же пользователя в порядке создания, по REPORTS_PER_ORDER на
заказ. Что не поместилось — остаётся NULL: это записи бесплатного периода,
и они не должны съедать оплаченные кредиты.

Revision ID: 022
Revises: 021
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None

# Дублирует payments.REPORTS_PER_ORDER намеренно: миграция не должна
# зависеть от кода приложения, который изменится после её применения.
REPORTS_PER_ORDER = 2


def upgrade() -> None:
    op.add_column("assessments", sa.Column(
        "order_id", UUID(as_uuid=True),
        sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_assessments_order_id", "assessments", ["order_id"])

    op.execute(f"""
        WITH paid AS (
            SELECT id, user_id,
                   row_number() OVER (PARTITION BY user_id
                       ORDER BY COALESCE(paid_at, created_at), id) AS rn
            FROM orders WHERE status = 'paid'
        ), cand AS (
            SELECT id, user_id,
                   row_number() OVER (PARTITION BY user_id
                       ORDER BY created_at, id) AS rn
            FROM assessments
            WHERE status IN ('completed', 'paid')
              AND grant_id IS NULL
              AND is_followup = false
        )
        UPDATE assessments a
        SET order_id = p.id
        FROM cand c
        JOIN paid p ON p.user_id = c.user_id
                   AND p.rn = ((c.rn - 1) / {REPORTS_PER_ORDER}) + 1
        WHERE a.id = c.id
    """)


def downgrade() -> None:
    op.drop_index("ix_assessments_order_id", table_name="assessments")
    op.drop_column("assessments", "order_id")

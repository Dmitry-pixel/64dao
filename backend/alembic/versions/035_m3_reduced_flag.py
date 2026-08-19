"""m3_portfolio_results.reduced — признак сокращённого режима

Портфельный слой считается от порога portfolio_min. Порог лежит в правимом
конфиге, поэтому вычислять признак при сборке отчёта нельзя: правка порога
задним числом переписала бы уже выданные отчёты. Снимок должен быть
самодостаточен, значит признак хранится вместе с ним.

Revision ID: 035
Revises: 034
"""
import sqlalchemy as sa

from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "m3_portfolio_results",
        sa.Column("reduced", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("m3_portfolio_results", "reduced")

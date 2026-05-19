"""add lc_ lifecycle fields to strategies

Revision ID: 003
Revises: 002
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategies', sa.Column('lc_profit',    sa.Text(), nullable=True))
    op.add_column('strategies', sa.Column('lc_strategy',  sa.Text(), nullable=True))
    op.add_column('strategies', sa.Column('lc_decisions', sa.Text(), nullable=True))
    op.add_column('strategies', sa.Column('lc_consumer',  sa.Text(), nullable=True))
    op.add_column('strategies', sa.Column('lc_market',    sa.Text(), nullable=True))
    op.add_column('strategies', sa.Column('lc_value',     sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('strategies', 'lc_value')
    op.drop_column('strategies', 'lc_market')
    op.drop_column('strategies', 'lc_consumer')
    op.drop_column('strategies', 'lc_decisions')
    op.drop_column('strategies', 'lc_strategy')
    op.drop_column('strategies', 'lc_profit')

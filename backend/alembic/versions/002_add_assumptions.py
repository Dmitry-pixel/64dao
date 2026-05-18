"""add assumption fields to strategies

Revision ID: 002
Revises: 001
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

COLUMNS = [
    'assm_planning',
    'assm_growth',
    'assm_advertising',
    'assm_feedback',
    'assm_risk',
    'assm_product',
    'assm_service',
    'assm_startup',
    'assm_investment',
    'assm_contracts',
    'assm_sync',
    'assm_creative',
    'assm_interaction',
]


def upgrade() -> None:
    for col in COLUMNS:
        op.add_column('strategies', sa.Column(col, sa.Text(), nullable=True))


def downgrade() -> None:
    for col in reversed(COLUMNS):
        op.drop_column('strategies', col)

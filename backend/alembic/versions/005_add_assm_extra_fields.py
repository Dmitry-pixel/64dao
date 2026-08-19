"""add assm extra fields: resources, research, trade, failures, success

Revision ID: 005
Revises: 004
Create Date: 2026-05-21
"""
import sqlalchemy as sa

from alembic import op

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

COLUMNS = [
    'assm_resources',
    'assm_research',
    'assm_trade',
    'assm_failures',
    'assm_success',
]


def upgrade() -> None:
    for col in COLUMNS:
        op.add_column('strategies', sa.Column(col, sa.Text(), nullable=True))


def downgrade() -> None:
    for col in reversed(COLUMNS):
        op.drop_column('strategies', col)

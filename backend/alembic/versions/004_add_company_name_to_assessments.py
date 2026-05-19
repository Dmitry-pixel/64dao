"""add company_name to assessments

Revision ID: 004
Revises: 003
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('assessments', sa.Column('company_name', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('assessments', 'company_name')

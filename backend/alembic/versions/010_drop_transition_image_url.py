"""drop orphan column strategies.transition_image_url (F4)

Осиротевшая колонка: была добавлена в БД вне alembic, отсутствует в models.py,
не читается и не пишется кодом; аудит F4 (2026-07-22) показал все 64 значения
NULL. Удаляем, чтобы схема БД совпадала с моделью.

Revision ID: 010
Revises: 009
Create Date: 2026-07-22
"""
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE strategies DROP COLUMN IF EXISTS transition_image_url")


def downgrade() -> None:
    op.execute("ALTER TABLE strategies ADD COLUMN IF NOT EXISTS transition_image_url TEXT")

# -*- coding: utf-8 -*-
"""045 Счётчик неверных попыток ввода OTP

Ограничение частоты на /api/auth/verify ключуется по IP: подбор пятизначного
кода с пула адресов оно не останавливает. Счётчик на самом коде останавливает:
после settings.otp_max_attempts неверных вводов код гасится (used = true),
и подобрать его уже нельзя (аудит 2026-10-06, R003).

Существующие коды получают 0 — они живут 10 минут, переходного периода нет.

Revision ID: 045
Revises: 044
"""
import sqlalchemy as sa

from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("otp_codes", sa.Column("attempts", sa.Integer, nullable=False,
                                         server_default=sa.text("0")))


def downgrade() -> None:
    op.drop_column("otp_codes", "attempts")

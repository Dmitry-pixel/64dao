"""Снимок расчёта Метода 3 хранит отраслевые веса

Уровень ячейки считается по сумме весов линий-Ян (раздел 10.1 передачи),
и карточка направления обязана этот вывод показать: «Ян на Л2 (45) +
Л3 (30) = 75 из 100 → высокая». Отчёт собирается из m3_results, а весов
там не было — печатать было не из чего.

Пересчитывать веса на лету по industry_id нельзя. Пресеты правятся
в админке через m3_weights, и старые отчёты начали бы меняться задним
числом. Ровно от этого защищает item_versions; здесь та же логика.

Колонка nullable и без бэкфилла намеренно: у снимков, снятых до этой
ревизии, весов не было, и достраивать их сейчас значит выдумать данные.
Такие отчёты просто не печатают строку вывода ячейки.

Revision ID: 030
Revises: 029
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("m3_results",
                  sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()),
                            nullable=True))


def downgrade() -> None:
    op.drop_column("m3_results", "weights")

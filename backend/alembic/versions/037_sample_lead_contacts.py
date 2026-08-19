# -*- coding: utf-8 -*-
"""037 sample_leads: контакты формы скачивания

Форма перед скачиванием перестала быть «один канал на выбор»: теперь она
собирает имя, e-mail и телефон обязательно, Max и Telegram — по желанию.

channel/address не трогаем и не делаем nullable: на них завязаны строки,
собранные старой формой, отправка письма и выгрузка CSV. Новая форма пишет
в них channel='email' и address=email, поэтому старые и новые строки
остаются сравнимыми, а откат миграции не теряет ни одного контакта из тех,
что были до неё.

source отвечает на вопрос «какая кнопка привела лида»: одна форма теперь
обслуживает методику и два примера отчёта, и без этой колонки сегменты
пришлось бы восстанавливать по времени и догадкам.

Revision ID: 037
Revises: 036
"""
import sqlalchemy as sa

from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None

TABLE = "sample_leads"

COLUMNS = [
    ("email", sa.String(320)),
    ("phone", sa.String(64)),
    ("max_address", sa.String(320)),
    ("telegram_address", sa.String(320)),
    ("source", sa.String(32)),
]


def upgrade() -> None:
    for name, type_ in COLUMNS:
        op.add_column(TABLE, sa.Column(name, type_, nullable=True))

    # Строки старой формы: канал уже известен, разложим его по новым колонкам,
    # чтобы админка и выгрузка не показывали по ним пустоту.
    op.execute("UPDATE sample_leads SET email = address WHERE channel = 'email'")
    op.execute("UPDATE sample_leads SET telegram_address = address WHERE channel = 'telegram'")
    op.execute("UPDATE sample_leads SET max_address = address WHERE channel = 'max'")
    op.execute("UPDATE sample_leads SET source = 'sample_m12' WHERE source IS NULL")


def downgrade() -> None:
    for name, _ in reversed(COLUMNS):
        op.drop_column(TABLE, name)

"""Удаление паролей: вход только по одноразовому коду

users.password_hash заполнялся при регистрации, админ-setup и сбросе, но
verify_password не вызывался ни из одного роутера — вход всегда шёл только
через OTP на почту. Поле создавало у пользователя впечатление защиты, ничего
не защищая, и при этом хранило чужие пароли: люди их переиспользуют, поэтому
утечка базы била бы по их почте и банку без всякой выгоды для нас.

Вместе с колонкой уходят /api/auth/forgot-password, /api/auth/reset-password,
шаблон письма forgot_password и зависимости passlib + bcrypt.

password_changed_at (миграция 032) переименована в sessions_revoked_at.
Смысл сместился, механизм тот же: токен с iat раньше отметки отклоняется.
Раньше отметку ставила смена пароля, теперь — кнопка «выйти со всех
устройств». Для беспарольного входа это нужнее: кука на 7 дней остаётся
единственным ключом от аккаунта, и отозвать её больше нечем.

Переименование, а не пара drop/add: значения сохраняются, а у тех, кто успел
сменить пароль между 032 и 033, отметка остаётся действующей.

ВНИМАНИЕ: DROP COLUMN необратим. downgrade вернёт пустую колонку — хеши
паролей не восстановятся. Перед накатом снимите дамп: deploy/scripts/backup.sh

Revision ID: 033
Revises: 032
"""
import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password_changed_at",
                    new_column_name="sessions_revoked_at")
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.alter_column("users", "sessions_revoked_at",
                    new_column_name="password_changed_at")

"""Удаление отчёта скрывает запись, а не стирает её

Расход кредита считается по факту: сколько завершённых диагностик и
рассчитанных портфелей привязано к оплаченным заказам. Пока удаление
стирало строку, оно возвращало кредит — и при включённой обязательной
оплате позволяло проходить диагностику заново сколько угодно раз.

Пометка вместо стирания закрывает это, не ломая главного свойства учёта:
счётчика по-прежнему нет, расход остаётся производным от фактов, и
разойтись они не могут. Возврат денег кредит возвращает как и раньше —
там меняется статус, а не факт существования записи.

Пользователь при удалении теряет запись из кабинета и файл PDF: строка
остаётся только для учёта.

Revision ID: 029
Revises: 028
"""
import sqlalchemy as sa

from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments",
                  sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("m3_portfolios",
                  sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Откат теряет пометки: записи снова станут видимыми в кабинете.
    # Данные при этом не пропадают — они и не удалялись.
    op.drop_column("m3_portfolios", "deleted_at")
    op.drop_column("assessments", "deleted_at")

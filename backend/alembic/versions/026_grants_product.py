"""access_grants.product — грант выдаётся на конкретный продукт

Партнёрский бесплатный доступ к Методу 3 назначает администратор (решение
владельца). Без поля продукта грант «на диагностику» покрывал бы и Метод 1
с Методом 2, и Метод 3 — то есть возвращал бы ту же дыру, ради закрытия
которой разделены платные кредиты: дешёвая квота тратится на дорогой продукт.

Гранта «на всё» нет намеренно. Партнёру, которому нужны оба продукта,
выдаются два гранта: их видно в списке по отдельности и отзывать их можно
по отдельности. Один универсальный грант такой возможности не даёт.

Бэкфил в 'm12': до этой ревизии Метод 3 не продавался вовсе, поэтому все
существующие гранты относятся к Методам 1 и 2. Догадки здесь нет.

Revision ID: 026
Revises: 025
"""
import sqlalchemy as sa

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("access_grants", sa.Column(
        "product", sa.String(10), nullable=False, server_default="m12"))
    # Дефолт снимаем: выдача гранта — действие администратора, продукт он
    # выбирает явно. Молчаливый m12 при опечатке в форме — хуже ошибки.
    op.alter_column("access_grants", "product", server_default=None)
    op.create_check_constraint(
        "chk_grant_product", "access_grants", "product IN ('m12','m3')")


def downgrade() -> None:
    op.drop_constraint("chk_grant_product", "access_grants", type_="check")
    op.drop_column("access_grants", "product")

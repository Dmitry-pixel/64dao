"""revoke followup right from method2 assessments

Бэкфил миграции 017 выдал право на бесплатную повторную диагностику всем
завершённым диагностикам без разбора метода. Это ошибка: повторная
диагностика и раздел «Динамика» работают только с Методом 1. Метод 2 это
оценка бизнес-модели по шкале, сравнивать там нечего, и бейдж «доступна
повторная» появлялся на отчётах, где повтор не предусмотрен.

Условие followup_used = 0 защищает ограничение followup_used <=
followup_allowed на случай, если право где-то уже было израсходовано.

Revision ID: 019
Revises: 018
"""
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE assessments SET followup_allowed = 0 "
        "WHERE method = 'method2' AND followup_used = 0"
    )


def downgrade() -> None:
    # Обратная операция вернула бы заведомо неверное состояние: право на
    # повтор у Метода 2 не имеет смысла. Оставлено пустым намеренно.
    pass

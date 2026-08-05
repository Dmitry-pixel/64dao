"""orders.product — заказ становится покупкой кредита на продукт

До этой ревизии заказ обязан был ссылаться на конкретную диагностику:
orders.assessment_id объявлен NOT NULL. Из этого следовали две вещи, обе
мешающие Методу 3.

Первое: Метод 3 живёт в m3_portfolios и ассессментом не является — продать
его было физически нечем. Обходной путь (служебный пустой ассессмент, как в
/api/payments/test-create) множит записи, которые потом приходится прятать
из списка отчётов.

Второе: купить диагностику заранее было невозможно — покупать нечего, пока
пользователь её не прошёл. А кабинету нужна обратная последовательность:
сначала оплата, потом прохождение.

Поэтому заказ теперь описывает ПРОДУКТ, а связь с конкретной диагностикой
проставляется в момент списания. Природа учёта не меняется: остаток
по-прежнему считается по факту использования, а не счётчиком, — рефанд
возвращает квоту автоматически, и счётчик не может разойтись с фактом.

CHECK-констрейнт держит инвариант «заказ ссылается только на свой продукт»:
заказ m3 не может быть привязан к ассессменту. Без него ошибка в коде
списания молча свяжет заказ не с тем объектом, и разойдутся оба баланса.

Обратной ссылки orders -> m3_portfolios здесь нет намеренно: вместе с
уже существующей m3_portfolios.order_id она образовала бы цикл внешних
ключей, на котором SQLAlchemy не может отсортировать таблицы (create_all
и drop_all падают с CircularDependencyError). Расход Метода 3 считается
по m3_portfolios.order_id — так же, как расход Методов 1 и 2 по
assessments.order_id.

ВНИМАНИЕ ПРИ ОТКАТЕ. downgrade возвращает assessment_id в NOT NULL и падает,
если к этому моменту существуют заказы product='m3' (у них assessment_id
всегда NULL). Это не дефект миграции: восстановить несуществующую привязку
неоткуда. Такие заказы нужно решить отдельно — вернуть деньги или перенести.
Дамп базы перед прогоном обязателен.

Revision ID: 025
Revises: 024
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default нужен на время бэкфила: колонка объявляется NOT NULL,
    # а у существующих строк значения нет. Снимаем его сразу после — новый
    # код обязан указывать продукт явно, иначе пропущенный аргумент тихо
    # создаст заказ m12 вместо m3.
    op.add_column("orders", sa.Column(
        "product", sa.String(10), nullable=False, server_default="m12"))
    op.alter_column("orders", "product", server_default=None)

    op.alter_column("orders", "assessment_id",
                    existing_type=UUID(as_uuid=True), nullable=True)

    op.create_check_constraint(
        "chk_order_product", "orders", "product IN ('m12','m3')")
    op.create_check_constraint(
        "chk_order_target", "orders",
        "product <> 'm3' OR assessment_id IS NULL")


def downgrade() -> None:
    op.drop_constraint("chk_order_target", "orders", type_="check")
    op.drop_constraint("chk_order_product", "orders", type_="check")

    # Падаем с внятной причиной раньше, чем это сделает Postgres на
    # ALTER COLUMN SET NOT NULL: сообщение БД не называет, откуда взялись
    # строки с NULL.
    orphans = op.get_bind().execute(sa.text(
        "SELECT count(*) FROM orders WHERE assessment_id IS NULL")).scalar()
    if orphans:
        raise RuntimeError(
            f"Откат невозможен: {orphans} заказ(ов) без assessment_id "
            "(заказы Метода 3). Решите их судьбу до отката ревизии 025.")

    op.alter_column("orders", "assessment_id",
                    existing_type=UUID(as_uuid=True), nullable=False)
    op.drop_column("orders", "product")

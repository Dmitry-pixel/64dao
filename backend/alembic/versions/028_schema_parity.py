"""Достроить то, что появилось на проде мимо alembic

Цепочка миграций не собирала базу с нуля. Причин было четыре, и все одного
рода: схема боевой базы правилась вручную, а миграции этого не знали.

  1. assessments.method и CHECK assessments_method_check — ревизия 009
     обращалась к колонке, которой на чистой базе нет. Исправлено в 009.
  2. Каталог из 64 стратегий заполняется через админку, а ревизия 020
     вешает внешний ключ strategies.target_combination -> combination.
     На неполном каталоге ключ не создавался. Исправлено в 020.
  3. users.is_active — колонку не создаёт ни одна миграция.
  4. Таблица sample_leads — не создаётся ни одной миграцией.
  5. Названия стратегий на проде давно text, в моделях Text, а миграция 001
     создаёт varchar(255): на базе с нуля длинное название не сохранилось бы.

Пункты 3 и 4 закрываются здесь, а не правкой старых ревизий: в отличие от
пункта 1, они не нужны ни одной миграции по ходу цепочки — их отсутствие
видно только в конце, когда схема сравнивается с моделями. Отдельная
ревизия честнее: она видна в истории и объясняет причину.

Всё идемпотентно. На существующих установках (и на проде) ревизия ничего
не делает: объекты уже есть.

downgrade намеренно пустой. Снести таблицу с заявками на пример отчёта или
колонку блокировки пользователей при откате на одну ревизию — потерять
данные ради симметрии, которая никому не нужна.

Revision ID: 028
Revises: 027
"""
from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Блокировка пользователя (админка: «заблокировать доступ»).
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS "
               "is_active BOOLEAN NOT NULL DEFAULT true")

    # Длинные названия стратегий. varchar(255) -> text: типы бинарно
    # совместимы, поэтому таблица не переписывается, а на базе, где колонки
    # уже text, ALTER ничего не меняет.
    op.execute("ALTER TABLE strategies "
               "ALTER COLUMN title TYPE text, "
               "ALTER COLUMN stratagema_title TYPE text, "
               "ALTER COLUMN transition_title TYPE text")

    # Заявки на пример отчёта (лендинг -> /api/sample-report).
    op.execute("""
        CREATE TABLE IF NOT EXISTS sample_leads (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(200) NOT NULL,
            channel     VARCHAR(20)  NOT NULL,
            address     VARCHAR(320) NOT NULL,
            consent     BOOLEAN      NOT NULL DEFAULT true,
            ip          VARCHAR(64),
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT chk_sample_lead_channel
                CHECK (channel IN ('email','telegram','max'))
        )
    """)


def downgrade() -> None:
    pass

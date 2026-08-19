"""m3_portfolios.company_name — название компании для заголовка отчёта

До этой ревизии колонки не было, и m3_report_api.company_name_for разрешал
название по цепочке portfolio.company_name -> portfolio.title ->
user.company_name, всегда попадая во второе звено: заголовок отчёта
показывал название портфеля вместо названия компании.

Название вводится ПЕРЕД диагностикой, как в Методах 1 и 2, и не берётся из
профиля пользователя (решение владельца). Поэтому колонка на портфеле, а не
чтение из users на лету: профиль может измениться после выдачи отчёта, а
отчёт обязан остаться воспроизводимым.

Бэкфила нет намеренно: у существующих портфелей названия компании никто не
спрашивал, и подстановка title сюда сделала бы догадку неотличимой от факта.
NULL честно означает «не спрашивали», и цепочка в company_name_for на таких
записях отработает как раньше.

Revision ID: 024
Revises: 023
"""
import sqlalchemy as sa

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("m3_portfolios",
                  sa.Column("company_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("m3_portfolios", "company_name")

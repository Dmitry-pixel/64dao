# -*- coding: utf-8 -*-
"""036 m3_content: вид zone_reduced

Расширяет chk_m3_content_kind значением 'zone_reduced'. Данных не трогает.

Зачем отдельный вид, а не колонка-признак у 'zone': переопределение
разрешается с откатом к общему тексту, и семь зон из девяти остаются без
своей версии. Колонка потребовала бы девяти строк-заглушек, вид не требует
ни одной. Тот же приём, что у контурного переопределения в fin_content:
запись существует только там, где она что-то меняет.

Ключ не меняется: zone_reduced/high_low переопределяет zone/high_low.
Уникальность (kind, key, industry_id) уже даёт нужную развязку.

Revision ID: 036
Revises: 035
"""
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None

TABLE = "m3_content"
CONSTRAINT = "chk_m3_content_kind"

KINDS_OLD = "kind IN ('zone','weak_line','strong_line','tension')"
KINDS_NEW = "kind IN ('zone','zone_reduced','weak_line','strong_line','tension')"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE, KINDS_NEW)


def downgrade() -> None:
    # Строки нового вида удаляются до восстановления ограничения: иначе
    # старое ограничение не встанет, и downgrade упадёт на середине.
    # Потеря допустима осознанно: это тексты, а не расчёт, и они
    # восстанавливаются повторным seed_m3_zone_reduced.py.
    op.execute("DELETE FROM " + TABLE + " WHERE kind = 'zone_reduced'")
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE, KINDS_OLD)

"""allow kind='level_state' in fin_content

Раздел «Три уровня» (сань-цай) хранит трактовки как редактируемый контент:
3 уровня x 4 состояния пары = 12 записей. Ключ вида {level}_{code}, например
earth_AB. Расчёт состояния живёт в app/contour_levels и контентом не
управляется: правится текст, а не правило.

Новых колонок не требуется. Контурные переопределения работают сразу:
колонка contour и уникальный ключ (kind, key, contour) существуют с 009,
и action_package ими уже пользуется.

Основание: 64dao_levels_block_plan.md, §3.2.

Revision ID: 034
Revises: 033
"""
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None

OLD = ("kind IN ('tonality','quadrant','trigram','tension_rule',"
       "'action_package','base_question')")
NEW = ("kind IN ('tonality','quadrant','trigram','tension_rule',"
       "'action_package','base_question','level_state')")


def upgrade() -> None:
    op.drop_constraint("chk_fin_content_kind", "fin_content", type_="check")
    op.create_check_constraint("chk_fin_content_kind", "fin_content", NEW)


def downgrade() -> None:
    op.execute("DELETE FROM fin_content WHERE kind = 'level_state'")
    op.drop_constraint("chk_fin_content_kind", "fin_content", type_="check")
    op.create_check_constraint("chk_fin_content_kind", "fin_content", OLD)

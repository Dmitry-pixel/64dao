"""allow kind='base_question' in fin_content

Базовые вопросы Метода 1 становятся редактируемым контентом: тексты переезжают
в fin_content и правятся в админке. Значения по умолчанию остаются в коде
(app/method1_questions) и заливаются скриптом seed_base_questions.py.

Revision ID: 016
Revises: 015
"""
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None

OLD = "kind IN ('tonality','quadrant','trigram','tension_rule','action_package')"
NEW = ("kind IN ('tonality','quadrant','trigram','tension_rule',"
       "'action_package','base_question')")


def upgrade() -> None:
    op.drop_constraint("chk_fin_content_kind", "fin_content", type_="check")
    op.create_check_constraint("chk_fin_content_kind", "fin_content", NEW)


def downgrade() -> None:
    op.execute("DELETE FROM fin_content WHERE kind = 'base_question'")
    op.drop_constraint("chk_fin_content_kind", "fin_content", type_="check")
    op.create_check_constraint("chk_fin_content_kind", "fin_content", OLD)

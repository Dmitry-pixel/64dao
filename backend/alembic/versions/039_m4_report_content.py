# -*- coding: utf-8 -*-
"""039 Метод 4: карточки отчёта, правила противоречий, цепочки симптомов

Контент отчёта отдельно от банка вопросов (038): его можно откатить, не
трогая вопросы.

Правила создаются раньше карточек: рекомендация по противоречию ссылается на
m4_rules.code внешним ключом. Так база сама не даст завести рекомендацию к
несуществующему правилу или удалить правило, у которого есть рекомендация.

Заодно добавляются поля, которых не хватило в 038. У модуля — intro,
вводный абзац перед блоком вопросов. У вопроса — границы числового ответа
(min_value, max_value: проценты не бывают больше 100) и служебная заметка
для администратора (note_internal): почему вопрос не штрафуется и с каким
правилом работает в паре.

Revision ID: 039
Revises: 038
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("m4_modules", sa.Column("intro", sa.Text(), nullable=True))
    op.add_column("m4_questions", sa.Column("min_value", sa.Integer(), nullable=True))
    op.add_column("m4_questions", sa.Column("max_value", sa.Integer(), nullable=True))
    op.add_column("m4_questions", sa.Column("note_internal", sa.Text(), nullable=True))
    op.create_check_constraint(
        "chk_m4_question_min_max", "m4_questions",
        "min_value IS NULL OR max_value IS NULL OR min_value <= max_value")

    op.create_table(
        "m4_rules",
        sa.Column("code", sa.String(8), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("severity", sa.String(8), nullable=False),
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("what_happens", sa.Text(), nullable=False),
        sa.Column("fix_one_of", postgresql.JSONB(), nullable=False),
        sa.Column("cost_of_inaction", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("is_mvp", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rule_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("severity IN ('high','medium','low')", name="chk_m4_rule_severity"),
        sa.CheckConstraint("jsonb_typeof(conditions) = 'object'", name="chk_m4_rule_conditions"),
        sa.CheckConstraint("jsonb_typeof(fix_one_of) = 'array'", name="chk_m4_rule_fix"),
    )

    op.create_table(
        "m4_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("key", sa.String(24), nullable=False),
        sa.Column("module_code", sa.SmallInteger(), nullable=True),
        sa.Column("state", sa.String(4), nullable=True),
        sa.Column("rule_code", sa.String(8), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mistake", sa.Text(), nullable=True),
        sa.Column("steps", postgresql.JSONB(), nullable=True),
        sa.Column("first_step", sa.Text(), nullable=True),
        sa.Column("how_to_check", sa.Text(), nullable=True),
        sa.Column("effect", sa.SmallInteger(), nullable=True),
        sa.Column("speed_weeks", sa.SmallInteger(), nullable=True),
        sa.Column("cost", sa.SmallInteger(), nullable=True),
        sa.Column("item_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["module_code"], ["m4_modules.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rule_code"], ["m4_rules.code"], ondelete="RESTRICT"),
        sa.UniqueConstraint("kind", "key", name="uq_m4_card_kind_key"),
        sa.CheckConstraint(
            "kind IN ('module_state','module_constraint','recommendation','dynamics','confidence')",
            name="chk_m4_card_kind"),
        sa.CheckConstraint("state IS NULL OR state IN ('low','mid','high')", name="chk_m4_card_state"),
        sa.CheckConstraint("effect IS NULL OR (effect >= 1 AND effect <= 3)", name="chk_m4_card_effect"),
        sa.CheckConstraint("cost IS NULL OR (cost >= 1 AND cost <= 3)", name="chk_m4_card_cost"),
        sa.CheckConstraint("speed_weeks IS NULL OR (speed_weeks >= 1 AND speed_weeks <= 104)",
                           name="chk_m4_card_speed"),
        sa.CheckConstraint(
            "kind <> 'recommendation' OR "
            "(effect IS NOT NULL AND speed_weeks IS NOT NULL AND cost IS NOT NULL)",
            name="chk_m4_card_reco_scores"),
        sa.CheckConstraint(
            "kind <> 'recommendation' OR ((module_code IS NULL) <> (rule_code IS NULL))",
            name="chk_m4_card_reco_target"),
        sa.CheckConstraint("steps IS NULL OR jsonb_typeof(steps) = 'array'", name="chk_m4_card_steps"),
    )
    op.create_index("ix_m4_cards_module_code", "m4_cards", ["module_code"])
    op.create_index("ix_m4_cards_rule_code", "m4_cards", ["rule_code"])

    op.create_table(
        "m4_symptom_chains",
        sa.Column("code", sa.String(40), primary_key=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("detected_by", postgresql.JSONB(), nullable=False),
        sa.Column("chain", postgresql.JSONB(), nullable=False),
        sa.Column("root_modules", postgresql.JSONB(), nullable=False),
        sa.Column("check_questions", postgresql.JSONB(), nullable=False),
        sa.Column("first_action", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sort", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "jsonb_typeof(detected_by) = 'array' AND jsonb_typeof(chain) = 'array' "
            "AND jsonb_typeof(root_modules) = 'array' AND jsonb_typeof(check_questions) = 'array'",
            name="chk_m4_chain_arrays"),
    )


def downgrade() -> None:
    op.drop_table("m4_symptom_chains")
    op.drop_index("ix_m4_cards_rule_code", table_name="m4_cards")
    op.drop_index("ix_m4_cards_module_code", table_name="m4_cards")
    op.drop_table("m4_cards")
    op.drop_table("m4_rules")
    op.drop_constraint("chk_m4_question_min_max", "m4_questions", type_="check")
    op.drop_column("m4_questions", "note_internal")
    op.drop_column("m4_questions", "max_value")
    op.drop_column("m4_questions", "min_value")
    op.drop_column("m4_modules", "intro")

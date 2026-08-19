"""Метод 3 «Матрица силы» — таблицы m3_*

Изолированный раздел: ни одна существующая таблица не меняется, внешние
ключи ведут только на users. Откат удаляет всё созданное и возвращает схему
в состояние ревизии 022.

Ограничение «3–8 направлений» намеренно НЕ вынесено в БД: направления
добавляются по одному, и констрейнт запрещал бы промежуточное состояние
формы, где их пока два. Проверка живёт в сервисе (m3_service.calculate)
и в схеме запроса.

Revision ID: 023
Revises: 022
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "m3_portfolios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("industry_id", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("owner_ranks", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('draft','filled','calculated')",
                           name="chk_m3_portfolio_status"),
    )
    op.create_index("ix_m3_portfolios_user_id", "m3_portfolios", ["user_id"])

    op.create_table(
        "m3_objects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("portfolio_id", UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("revenue", sa.Numeric(16, 2), nullable=True),
        sa.Column("revenue_dynamics", sa.Numeric(6, 2), nullable=True),
        sa.Column("revenue_share", sa.Numeric(5, 2), nullable=True),
        sa.Column("profitability", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("industry_id", sa.SmallInteger(), nullable=True),
        sa.Column("screening_price", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("screening_market", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_new_venture", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["m3_portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "position", name="uq_m3_object_position"),
        sa.CheckConstraint(
            "profitability IN ('profitable','marginal','unprofitable','unknown')",
            name="chk_m3_object_profitability"),
        sa.CheckConstraint("position >= 1 AND position <= 8",
                           name="chk_m3_object_position_range"),
        sa.CheckConstraint(
            "revenue_share IS NULL OR (revenue_share >= 0 AND revenue_share <= 100)",
            name="chk_m3_object_share"),
    )
    op.create_index("ix_m3_objects_portfolio_id", "m3_objects", ["portfolio_id"])

    op.create_table(
        "m3_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("block", sa.String(1), nullable=False),
        sa.Column("number", sa.SmallInteger(), nullable=False),
        sa.Column("code", sa.String(4), nullable=False),
        sa.Column("line", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_reverse", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("industry_id", sa.SmallInteger(), nullable=True),
        sa.Column("item_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("code", "industry_id", "item_version",
                            name="uq_m3_item_version"),
        sa.CheckConstraint("block IN ('Р','Н','А')", name="chk_m3_item_block"),
        sa.CheckConstraint("line >= 1 AND line <= 6", name="chk_m3_item_line"),
    )

    op.create_table(
        "m3_hints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("industry_id", sa.SmallInteger(), nullable=False),
        sa.Column("item_code", sa.String(4), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("industry_id", "item_code", name="uq_m3_hint"),
    )
    op.create_index("ix_m3_hints_industry_id", "m3_hints", ["industry_id"])

    op.create_table(
        "m3_answers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("portfolio_id", UUID(as_uuid=True), nullable=False),
        sa.Column("object_id", UUID(as_uuid=True), nullable=True),
        sa.Column("item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("item_code", sa.String(4), nullable=False),
        sa.Column("value", sa.SmallInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["portfolio_id"], ["m3_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_id"], ["m3_objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["m3_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "object_id", "item_id", name="uq_m3_answer"),
        sa.CheckConstraint("value IS NULL OR (value >= 1 AND value <= 4)",
                           name="chk_m3_answer_value"),
    )
    op.create_index("ix_m3_answers_portfolio_id", "m3_answers", ["portfolio_id"])
    op.create_index("ix_m3_answers_object_id", "m3_answers", ["object_id"])

    op.create_table(
        "m3_weights",
        sa.Column("industry_id", sa.SmallInteger(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("w_l1", sa.SmallInteger(), nullable=False),
        sa.Column("w_l2", sa.SmallInteger(), nullable=False),
        sa.Column("w_l3", sa.SmallInteger(), nullable=False),
        sa.Column("w_l4", sa.SmallInteger(), nullable=False),
        sa.Column("w_l5", sa.SmallInteger(), nullable=False),
        sa.Column("w_l6", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("w_l1 + w_l2 + w_l3 = 100", name="chk_m3_weights_strength"),
        sa.CheckConstraint("w_l4 + w_l5 + w_l6 = 100", name="chk_m3_weights_attract"),
    )

    op.create_table(
        "m3_hexagrams",
        sa.Column("code", sa.String(6), primary_key=True),
        sa.Column("kw_number", sa.SmallInteger(), nullable=False, unique=True),
        sa.Column("name_64dao", sa.String(120), nullable=False),
        sa.CheckConstraint(r"code ~ '^[AB]{6}$'", name="chk_m3_hexagram_code"),
        sa.CheckConstraint("kw_number >= 1 AND kw_number <= 64",
                           name="chk_m3_hexagram_number"),
    )

    op.create_table(
        "m3_content",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("key", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mistake", sa.Text(), nullable=True),
        sa.Column("industry_id", sa.SmallInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("kind", "key", "industry_id", name="uq_m3_content"),
        sa.CheckConstraint("kind IN ('zone','weak_line','strong_line','tension')",
                           name="chk_m3_content_kind"),
    )

    op.create_table(
        "m3_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("portfolio_id", UUID(as_uuid=True), nullable=False),
        sa.Column("object_id", UUID(as_uuid=True), nullable=False),
        *[sa.Column(f"l{i}", sa.Numeric(3, 2), nullable=False) for i in range(1, 7)],
        sa.Column("symbols", sa.String(6), nullable=False),
        sa.Column("mobility", JSONB(), nullable=False, server_default="{}"),
        sa.Column("cell_strength", sa.String(4), nullable=False),
        sa.Column("cell_attract", sa.String(4), nullable=False),
        sa.Column("coord_strength", sa.Numeric(3, 2), nullable=False),
        sa.Column("coord_attract", sa.Numeric(3, 2), nullable=False),
        sa.Column("current_hex", sa.SmallInteger(), nullable=False),
        sa.Column("target_hex", sa.SmallInteger(), nullable=True),
        sa.Column("target_lines", ARRAY(sa.SmallInteger()), nullable=True),
        sa.Column("risk_hex", sa.SmallInteger(), nullable=True),
        sa.Column("risk_lines", ARRAY(sa.SmallInteger()), nullable=True),
        sa.Column("v_index", sa.Numeric(6, 4), nullable=False),
        sa.Column("z_index", sa.Numeric(6, 4), nullable=False),
        sa.Column("v_rank", sa.SmallInteger(), nullable=False),
        sa.Column("z_rank", sa.SmallInteger(), nullable=False),
        sa.Column("weak_line", sa.SmallInteger(), nullable=False),
        sa.Column("strong_line", sa.SmallInteger(), nullable=False),
        sa.Column("tensions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("flags", JSONB(), nullable=False, server_default="[]"),
        # Версии пунктов на момент расчёта. Без них правка формулировки
        # сделает старые отчёты несопоставимыми с новыми.
        sa.Column("item_versions", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["portfolio_id"], ["m3_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_id"], ["m3_objects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "object_id", name="uq_m3_result"),
        sa.CheckConstraint(r"symbols ~ '^[AB]{6}$'", name="chk_m3_result_symbols"),
        sa.CheckConstraint("cell_strength IN ('low','mid','high')", name="chk_m3_result_cell_s"),
        sa.CheckConstraint("cell_attract IN ('low','mid','high')", name="chk_m3_result_cell_a"),
    )
    op.create_index("ix_m3_results_portfolio_id", "m3_results", ["portfolio_id"])
    op.create_index("ix_m3_results_object_id", "m3_results", ["object_id"])

    op.create_table(
        "m3_portfolio_results",
        sa.Column("portfolio_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("sum_positions", sa.SmallInteger(), nullable=False),
        sa.Column("turbulence", sa.SmallInteger(), nullable=False),
        sa.Column("delta", sa.SmallInteger(), nullable=False),
        sa.Column("distinct_cells", sa.SmallInteger(), nullable=False),
        sa.Column("spearman", sa.Numeric(4, 2), nullable=True),
        sa.Column("flags", JSONB(), nullable=False, server_default="[]"),
        sa.Column("verdicts_held", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["portfolio_id"], ["m3_portfolios.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "m3_tradeoff_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("portfolio_id", UUID(as_uuid=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("accepted_option", sa.String(10), nullable=False),
        sa.Column("waves", JSONB(), nullable=False, server_default="{}"),
        sa.Column("cost_accepted", sa.Text(), nullable=True),
        sa.Column("review_triggers", ARRAY(sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["m3_portfolios.id"], ondelete="CASCADE"),
        sa.CheckConstraint("accepted_option IN ('method','custom')",
                           name="chk_m3_tradeoff_option"),
    )
    op.create_index("ix_m3_tradeoff_portfolio_id", "m3_tradeoff_decisions", ["portfolio_id"])

    op.create_table(
        "m3_checklist",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("portfolio_id", UUID(as_uuid=True), nullable=False),
        sa.Column("object_id", UUID(as_uuid=True), nullable=True),
        sa.Column("step_text", sa.Text(), nullable=False),
        sa.Column("line", sa.SmallInteger(), nullable=True),
        sa.Column("step_type", sa.String(10), nullable=False),
        sa.Column("wave", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("needs_budget", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["m3_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_id"], ["m3_objects.id"], ondelete="CASCADE"),
        sa.CheckConstraint("step_type IN ('route','hold','prep','decision')",
                           name="chk_m3_checklist_type"),
    )
    op.create_index("ix_m3_checklist_portfolio_id", "m3_checklist", ["portfolio_id"])
    op.create_index("ix_m3_checklist_object_id", "m3_checklist", ["object_id"])


def downgrade() -> None:
    for table in (
        "m3_checklist", "m3_tradeoff_decisions", "m3_portfolio_results",
        "m3_results", "m3_content", "m3_hexagrams", "m3_weights",
        "m3_answers", "m3_hints", "m3_items", "m3_objects", "m3_portfolios",
    ):
        op.drop_table(table)

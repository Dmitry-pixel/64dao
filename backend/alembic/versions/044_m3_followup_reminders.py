# -*- coding: utf-8 -*-
"""044 Повтор Метода 3 и напоминания о повторе Методов 3 и 4

Решение владельца: один бесплатный повтор у всех методов, кроме Метода 2
(BMC). У Метода 1 и Метода 4 право на повтор уже есть; здесь — Метод 3,
по той же схеме, что assessments и m4_runs:
  followup_allowed / followup_used — у первичного портфеля;
  is_followup / parent_portfolio_id — у повтора.

repeat_reminder_sent_at у m3_portfolios и m4_runs — отметка письма
«пора повторить». Ставится на последнюю диагностику компании: новая
диагностика приходит с пустой отметкой, и напоминание само взводится снова.
У Метода 1 отметка живёт на companies; Метод 3 к компаниям не привязан
(только название), поэтому отметка — на самой диагностике.

Существующие строки получают значения по умолчанию: права на повтор у уже
рассчитанных портфелей нет (followup_allowed = 0) — повтор не обещали
тем, кто покупал до этого решения.

Revision ID: 044
Revises: 043
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("m3_portfolios", sa.Column("is_followup", sa.Boolean, nullable=False,
                                             server_default=sa.text("false")))
    op.add_column("m3_portfolios", sa.Column("parent_portfolio_id", UUID, nullable=True))
    op.add_column("m3_portfolios", sa.Column("followup_allowed", sa.Integer, nullable=False,
                                             server_default="0"))
    op.add_column("m3_portfolios", sa.Column("followup_used", sa.Integer, nullable=False,
                                             server_default="0"))
    op.add_column("m3_portfolios", sa.Column("repeat_reminder_sent_at", sa.DateTime(timezone=True),
                                             nullable=True))
    op.create_foreign_key("fk_m3_portfolio_parent", "m3_portfolios", "m3_portfolios",
                          ["parent_portfolio_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_m3_portfolios_parent_portfolio_id", "m3_portfolios", ["parent_portfolio_id"])
    op.create_check_constraint("chk_m3_portfolio_followup_used", "m3_portfolios",
                               "followup_used >= 0 AND followup_used <= followup_allowed")
    op.create_check_constraint("chk_m3_portfolio_followup_parent", "m3_portfolios",
                               "NOT is_followup OR parent_portfolio_id IS NOT NULL")

    op.add_column("m4_runs", sa.Column("repeat_reminder_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("m4_runs", "repeat_reminder_sent_at")
    op.drop_constraint("chk_m3_portfolio_followup_parent", "m3_portfolios", type_="check")
    op.drop_constraint("chk_m3_portfolio_followup_used", "m3_portfolios", type_="check")
    op.drop_index("ix_m3_portfolios_parent_portfolio_id", table_name="m3_portfolios")
    op.drop_constraint("fk_m3_portfolio_parent", "m3_portfolios", type_="foreignkey")
    for col in ("repeat_reminder_sent_at", "followup_used", "followup_allowed",
                "parent_portfolio_id", "is_followup"):
        op.drop_column("m3_portfolios", col)

"""access_grants — временный бесплатный доступ (партнёрские пилоты)

Квота + срок. Расход не хранится счётчиком, а считается по
assessments.grant_id — так же, как платные кредиты в
payments.calculate_credits. Рефанд возвращает диагностику в draft,
и квота гранта восстанавливается сама.

Статус гранта (active/used_up/expired/revoked) не хранится, а
вычисляется от revoked_at, expires_at и остатка: крон на протухание
не нужен.

Revision ID: 021
Revises: 020
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_grants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("quota", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", UUID(as_uuid=True), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("quota > 0", name="chk_grant_quota_positive"),
        sa.CheckConstraint("expires_at > starts_at", name="chk_grant_period"),
    )
    op.create_index("ix_access_grants_user_id", "access_grants", ["user_id"])

    op.add_column("assessments", sa.Column(
        "grant_id", UUID(as_uuid=True),
        sa.ForeignKey("access_grants.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_assessments_grant_id", "assessments", ["grant_id"])


def downgrade() -> None:
    op.drop_index("ix_assessments_grant_id", table_name="assessments")
    op.drop_column("assessments", "grant_id")
    op.drop_index("ix_access_grants_user_id", table_name="access_grants")
    op.drop_table("access_grants")

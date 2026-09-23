# -*- coding: utf-8 -*-
"""040 Метод 4: реестр конструктов и связи с пунктами других методов

Конструкт — то, что метод пытается узнать, независимо от формулировки. Реестр
нужен, чтобы не спрашивать одно и то же дважды и сверять ответы Метода 3 и
Метода 4 на один вопрос.

Связи с другими методами — отдельной таблицей m4_construct_links, а не полем
construct_code в m3_items: пункты Метода 3 хранятся по строкам на каждую
версию и отрасль, пункты контуров живут в коде. Так таблицы Метода 3 эта
миграция не трогает вовсе, и откат не может задеть Метод 3.

Поле m4_questions.construct_code уже есть (038). Внешний ключ на реестр не
ставится: 28 вопросов залиты раньше реестра. Соответствие кодов проверяет
seed_m4_content.py перед записью.

Revision ID: 040
Revises: 039
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "m4_constructs",
        sa.Column("code", sa.String(48), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(12), nullable=False),
        sa.Column("reusable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cross_check", sa.String(24), nullable=True),
        sa.Column("cross_check_why", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sort", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("unit IN ('company','direction','function')", name="chk_m4_construct_unit"),
        sa.CheckConstraint(
            "cross_check IS NULL OR cross_check IN ('always','single_direction_only','no')",
            name="chk_m4_construct_cross_check"),
    )

    op.create_table(
        "m4_construct_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("construct_code", sa.String(48), nullable=False),
        sa.Column("method", sa.String(24), nullable=False),
        sa.Column("item_code", sa.String(48), nullable=False),
        sa.Column("reverse", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dynamic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("free_text", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["construct_code"], ["m4_constructs.code"], ondelete="CASCADE"),
        sa.UniqueConstraint("construct_code", "method", "item_code", name="uq_m4_construct_link"),
        sa.CheckConstraint(
            "method IN ('m1_base','m3','contour_finance','contour_product','contour_process',"
            "'contour_market','ui_bmc')",
            name="chk_m4_construct_link_method"),
    )
    op.create_index("ix_m4_construct_links_construct_code", "m4_construct_links", ["construct_code"])


def downgrade() -> None:
    op.drop_index("ix_m4_construct_links_construct_code", table_name="m4_construct_links")
    op.drop_table("m4_construct_links")
    op.drop_table("m4_constructs")

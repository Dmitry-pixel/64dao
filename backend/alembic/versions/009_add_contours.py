"""add contours: assessment_contours, assessments.method, fin_content.contour

Revision ID: 009
Revises: 008
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

_CONTOURS = "('finance','product','market','process')"
_SCOPES = "('common','finance','product','market','process')"


def upgrade() -> None:
    # 1) Нормализация JSON-нулей в SQL NULL (SQLAlchemy JSONB пишет None как json null)
    op.execute("UPDATE assessments SET finance_result = NULL "
               "WHERE jsonb_typeof(finance_result) = 'null'")
    op.execute("UPDATE assessments SET finance_answers = NULL "
               "WHERE jsonb_typeof(finance_answers) = 'null'")
    op.execute("UPDATE assessments SET method2_data = NULL "
               "WHERE jsonb_typeof(method2_data) = 'null'")

    # 2) Признак метода (Поправка П3).
    #
    # Колонка method и CHECK assessments_method_check были созданы на боевой
    # базе вне alembic, поэтому здесь их сознательно не создавали — только
    # засыпали значения. На боевой базе это работало, а на чистой цепочка
    # обрывалась ровно тут: UPDATE обращался к колонке, которой нет, и поднять
    # схему с нуля было невозможно — ни при восстановлении из дампа, ни новому
    # разработчику.
    #
    # Создаём идемпотентно: на базе, где колонка уже есть (все существующие
    # установки), ALTER ничего не делает и повторный прогон безвреден.
    # Тип, дефолт и имя CHECK — те же, что в models.py, иначе схема чистой
    # базы разошлась бы с боевой.
    op.execute("ALTER TABLE assessments ADD COLUMN IF NOT EXISTS "
               "method VARCHAR(10) NOT NULL DEFAULT 'method1'")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'assessments_method_check'
            ) THEN
                ALTER TABLE assessments ADD CONSTRAINT assessments_method_check
                    CHECK (method IN ('method1','method2'));
            END IF;
        END $$;
    """)

    op.execute(
        "UPDATE assessments SET method = 'method2' "
        "WHERE (method2_data IS NOT NULL AND method2_data <> '{}'::jsonb) "
        "   OR (method1_answers IS NULL AND method1_combination IS NULL)"
    )

    # 3) Таблица контуров
    op.create_table(
        "assessment_contours",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", UUID(as_uuid=True),
                  sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contour", sa.String(20), nullable=False),
        sa.Column("answers", JSONB(), nullable=False),
        sa.Column("result", JSONB(), nullable=False),
        sa.Column("combination", sa.String(6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("assessment_id", "contour", name="uq_contour_per_assessment"),
        sa.CheckConstraint(f"contour IN {_CONTOURS}", name="chk_contour_name"),
        sa.CheckConstraint(r"combination ~ '^[AB]{6}$'", name="chk_contour_combination"),
        sa.CheckConstraint("jsonb_typeof(answers) = 'object'", name="chk_contour_answers_obj"),
        sa.CheckConstraint("jsonb_typeof(result) = 'object'", name="chk_contour_result_obj"),
    )
    op.create_index("ix_assessment_contours_assessment_id",
                    "assessment_contours", ["assessment_id"])

    # 4) Перенос финблока. Колонки finance_* НЕ удаляем — rollback-окно (миграция 010).
    conn = op.get_bind()
    where = ("jsonb_typeof(finance_result) = 'object' "
             "AND jsonb_typeof(finance_answers) = 'object' "
             "AND COALESCE(finance_combination, finance_result->>'combination_current') "
             "    ~ '^[AB]{6}$'")
    src = conn.execute(sa.text(f"SELECT count(*) FROM assessments WHERE {where}")).scalar_one()
    conn.execute(sa.text(
        "INSERT INTO assessment_contours "
        "(id, assessment_id, contour, answers, result, combination, created_at, updated_at) "
        "SELECT gen_random_uuid(), id, 'finance', finance_answers, finance_result, "
        "       COALESCE(finance_combination, finance_result->>'combination_current'), "
        "       created_at, updated_at "
        f"FROM assessments WHERE {where}"
    ))
    moved = conn.execute(sa.text(
        "SELECT count(*) FROM assessment_contours WHERE contour = 'finance'")).scalar_one()
    if moved != src:
        raise RuntimeError(
            f"[009] перенос финблока: исходных {src}, перенесено {moved} — "
            "миграция остановлена, транзакция откатывается")
    print(f"[009] перенесено финансовых контуров: {moved} из {src}")

    # 5) Контурное переопределение контента (Поправка П1: sentinel 'common', не NULL)
    op.add_column("fin_content",
                  sa.Column("contour", sa.String(20), nullable=False, server_default="common"))
    op.create_check_constraint("chk_fin_content_contour", "fin_content", f"contour IN {_SCOPES}")
    op.drop_constraint("uq_fin_content_kind_key", "fin_content", type_="unique")
    op.create_unique_constraint("uq_fin_content_kind_key_contour", "fin_content",
                                ["kind", "key", "contour"])


def downgrade() -> None:
    conn = op.get_bind()

    # UNIQUE(kind, key) восстановим только при отсутствии контурных переопределений —
    # иначе ограничение не создастся и откат упадёт на полпути.
    overrides = conn.execute(sa.text(
        "SELECT count(*) FROM fin_content WHERE contour <> 'common'")).scalar_one()
    if overrides:
        raise RuntimeError(
            f"[009 downgrade] в fin_content контурных переопределений: {overrides}. "
            "Удалите их или переведите в 'common' перед откатом.")

    # Финансовый контур восстановим из колонок finance_* — они не удалялись.
    # Остальные контуры при откате теряются безвозвратно.
    extra = conn.execute(sa.text(
        "SELECT count(*) FROM assessment_contours WHERE contour <> 'finance'")).scalar_one()
    if extra:
        print(f"[009 downgrade] ВНИМАНИЕ: будет потеряно контуров (кроме finance): {extra}")

    op.drop_constraint("uq_fin_content_kind_key_contour", "fin_content", type_="unique")
    op.create_unique_constraint("uq_fin_content_kind_key", "fin_content", ["kind", "key"])
    op.drop_constraint("chk_fin_content_contour", "fin_content", type_="check")
    op.drop_column("fin_content", "contour")

    op.drop_index("ix_assessment_contours_assessment_id", table_name="assessment_contours")
    op.drop_table("assessment_contours")

    # Колонка method и её CHECK существовали до 009 — не трогаем.

"""drop legacy finance_* columns on assessments (F2)

Финансовый контур Метода 1 хранится в assessment_contours (этап 1). Колонки
assessments.finance_answers/finance_result/finance_combination оставались как
rollback-окно. Аудит 2026-07-22: все завершённые диагностики уже имеют строку
контура 'finance' (completed_missing_row = 0), черновиков только в старых
колонках нет (drafts_answers_only = 0). Перед дропом — защитный бэкфилл на
случай гонки при деплое.

Revision ID: 011
Revises: 010
Create Date: 2026-07-22
"""
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # (а) Защитный перенос: завершённый finance без строки контура → в assessment_contours.
    op.execute("""
        INSERT INTO assessment_contours (id, assessment_id, contour, answers, result, combination, created_at, updated_at)
        SELECT gen_random_uuid(), a.id, 'finance',
               COALESCE(a.finance_answers, '{}'::jsonb), a.finance_result, a.finance_combination,
               a.created_at, a.updated_at
        FROM assessments a
        WHERE a.finance_result IS NOT NULL AND a.finance_combination IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM assessment_contours c
              WHERE c.assessment_id = a.id AND c.contour = 'finance'
          )
    """)
    # (б) Дроп колонок (CHECK chk_assessment_finance_combination снимется вместе с колонкой).
    op.execute("ALTER TABLE assessments DROP COLUMN IF EXISTS finance_answers")
    op.execute("ALTER TABLE assessments DROP COLUMN IF EXISTS finance_result")
    op.execute("ALTER TABLE assessments DROP COLUMN IF EXISTS finance_combination")


def downgrade() -> None:
    op.execute("ALTER TABLE assessments ADD COLUMN IF NOT EXISTS finance_answers JSONB")
    op.execute("ALTER TABLE assessments ADD COLUMN IF NOT EXISTS finance_result JSONB")
    op.execute("ALTER TABLE assessments ADD COLUMN IF NOT EXISTS finance_combination VARCHAR(6)")
    op.execute(
        "ALTER TABLE assessments ADD CONSTRAINT chk_assessment_finance_combination "
        "CHECK (finance_combination IS NULL OR finance_combination ~ '^[AB]{6}$')"
    )
    # Обратный перенос из контура в колонки (для симметрии downgrade).
    op.execute("""
        UPDATE assessments a SET
            finance_result = c.result,
            finance_combination = c.combination,
            finance_answers = c.answers
        FROM assessment_contours c
        WHERE c.assessment_id = a.id AND c.contour = 'finance'
    """)

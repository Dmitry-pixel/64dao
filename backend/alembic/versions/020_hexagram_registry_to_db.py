"""hexagram registry moves to the database

Реестр гексаграмм жил двумя копиями в коде. Названия уже хранились в
strategies.title и правились в админке, номер и целевая гексаграмма были
захардкожены. Миграция переносит недостающее в БД.

Бэкфил взят из backend/app/hexagrams.py; значения сверены с фронтендом и с
методологической таблицей соответствия, расхождений нет.

Колонки nullable намеренно: отчёт не должен падать на записи без цели.

Revision ID: 020
Revises: 019
"""
from alembic import op
import sqlalchemy as sa

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None

# (комбинация, номер гексаграммы, комбинация целевой гексаграммы)
_ROWS = [
    ('AAAAAA', 1, 'AAABAA'),
    ('BBBBBB', 2, 'BBAABB'),
    ('ABBBAB', 3, 'ABAAAB'),
    ('BABBBA', 4, 'BABBBB'),
    ('AAABAB', 5, 'ABABAB'),
    ('BABAAA', 6, 'BABAAA'),
    ('BABBBB', 7, 'BBAABB'),
    ('BBBBAB', 8, 'BBBBBA'),
    ('AAABAA', 9, 'ABABAA'),
    ('AABAAA', 10, 'ABBAAA'),
    ('AAABBB', 11, 'ABABBB'),
    ('BBBAAA', 12, 'AAABAA'),
    ('ABAAAA', 13, 'ABABAA'),
    ('AAAABA', 14, 'AAABBA'),
    ('BBABBB', 15, 'AAABBB'),
    ('BBBABB', 16, 'AABABB'),
    ('ABBAAB', 17, 'ABABAB'),
    ('BAABBA', 18, 'BABABA'),
    ('AABBBB', 19, 'AAAABB'),
    ('BBBBAA', 20, 'BBAAAA'),
    ('ABBABA', 21, 'BABABA'),
    ('ABABBA', 22, 'BAABBA'),
    ('BBBBBA', 23, 'BBAABA'),
    ('ABBBBB', 24, 'AABBBB'),
    ('ABBAAA', 25, 'ABABAA'),
    ('AAABBA', 26, 'ABABBA'),
    ('ABBBBA', 27, 'BABBBA'),
    ('BAAAAB', 28, 'BAAAAA'),
    ('BABBAB', 29, 'ABBBAB'),
    ('ABAABA', 30, 'ABABBA'),
    ('BBAAAB', 31, 'AAAAAB'),
    ('BAAABB', 32, 'BAAAAA'),
    ('BBAAAA', 33, 'AAAAAA'),
    ('AAAABB', 34, 'AAAAAA'),
    ('BBBABA', 35, 'BABABA'),
    ('ABABBB', 36, 'ABABAA'),
    ('ABABAA', 37, 'ABABAB'),
    ('AABABA', 38, 'ABBABA'),
    ('BBABAB', 39, 'AAABAB'),
    ('BABABB', 40, 'BAABBB'),
    ('AABBBA', 41, 'ABBBBA'),
    ('ABBBAA', 42, 'ABBBAB'),
    ('AAAAAB', 43, 'AAABAB'),
    ('BAAAAA', 44, 'BBAAAA'),
    ('BBBAAB', 45, 'AABAAB'),
    ('BAABBB', 46, 'BAABAA'),
    ('BABAAB', 47, 'BAAAAA'),
    ('BAABAB', 48, 'BABAAB'),
    ('ABAAAB', 49, 'ABABAB'),
    ('BAAABA', 50, 'BAABBA'),
    ('ABBABB', 51, 'ABBAAA'),
    ('BBABBA', 52, 'BAABBA'),
    ('BBABAA', 53, 'BBABAB'),
    ('AABABB', 54, 'AAABBB'),
    ('ABAABB', 55, 'ABABBB'),
    ('BBAABA', 56, 'AAAABA'),
    ('BAABAA', 57, 'BAAAAA'),
    ('AABAAB', 58, 'AAABAB'),
    ('BABBAA', 59, 'BAAAAA'),
    ('AABBAB', 60, 'AAAAAB'),
    ('AABBAA', 61, 'ABBBAA'),
    ('BBAABB', 62, 'BBAAAA'),
    ('ABABAB', 63, 'ABBAAB'),
    ('BABABA', 64, 'BABABB'),
]


def upgrade() -> None:
    op.add_column('strategies', sa.Column('hexagram_number', sa.Integer(), nullable=True))
    op.add_column('strategies', sa.Column('target_combination', sa.String(length=6), nullable=True))
    conn = op.get_bind()
    stmt = sa.text('UPDATE strategies SET hexagram_number = :n, target_combination = :tc WHERE combination = :combo')
    conn.execute(stmt, [{'combo': c, 'n': n, 'tc': t} for c, n, t in _ROWS])
    op.create_unique_constraint('uq_strategy_hexagram_number', 'strategies', ['hexagram_number'])
    op.create_check_constraint('ck_strategy_hexagram_number', 'strategies', 'hexagram_number BETWEEN 1 AND 64')
    op.create_foreign_key('fk_strategy_target_combination', 'strategies', 'strategies', ['target_combination'], ['combination'])


def downgrade() -> None:
    op.drop_constraint('fk_strategy_target_combination', 'strategies', type_='foreignkey')
    op.drop_constraint('ck_strategy_hexagram_number', 'strategies', type_='check')
    op.drop_constraint('uq_strategy_hexagram_number', 'strategies', type_='unique')
    op.drop_column('strategies', 'target_combination')
    op.drop_column('strategies', 'hexagram_number')

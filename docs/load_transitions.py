# -*- coding: utf-8 -*-
"""Разбор transition_texts.md в SQL для strategies.transition_description.

Заголовок блока: "### номер | комбинация | подпись", далее текст до
следующего заголовка. Скрипт ничего не пишет в БД сам — только формирует
transition_load.sql с одной транзакцией, чтобы правку можно было прочитать
глазами до применения.
"""
import re
import sys

SRC = 'transition_texts.md'
DST = 'transition_load.sql'

text = open(SRC, encoding='utf-8').read()
blocks = re.split(r'(?m)^### ', text)[1:]

rows = []
for b in blocks:
    head, _, body = b.partition('\n')
    parts = [p.strip() for p in head.split('|')]
    if len(parts) < 2:
        sys.exit('Плохой заголовок: ' + head)
    combo = parts[1]
    if not re.fullmatch(r'[AB]{6}', combo):
        sys.exit('Плохая комбинация: ' + combo)
    value = body.strip()
    if not value:
        sys.exit('Пустой текст у ' + combo)
    rows.append((combo, value))

if len(rows) != 64:
    sys.exit('Найдено %d записей вместо 64' % len(rows))
if len({c for c, _ in rows}) != 64:
    sys.exit('Комбинации повторяются')

with open(DST, 'w', encoding='utf-8') as f:
    f.write('BEGIN;\n')
    for combo, value in rows:
        f.write("UPDATE strategies SET transition_description = '%s' "
                "WHERE combination = '%s';\n"
                % (value.replace("'", "''"), combo))
    f.write('COMMIT;\n')

print('OK: записей', len(rows), '| файл', DST)

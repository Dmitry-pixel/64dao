'use client'

// Строка сдвига в шапке раздела контура повторного отчёта.
// Общий источник фраз о сдвиге контура. Бэкенд-аналог —
// состав фраз держим одинаковым (правило паритета HTML и PDF).
// Формулировки продублированы намеренно: их правка идёт парой.

export const SHIFT_TEXT = {
  maturity: 'зрелость',
  strengthen: 'Инь → Ян (укрепление)',
  weaken: 'Ян → Инь (ослабление)',
  movingClosedLines: 'Закрытые точки роста',
  movingNewLines: 'Новые',
  noLineChanges: 'Без изменений в линиях.',
  reachedTarget: '✓ Достигнута целевая гексаграмма предыдущего прогона',
  maturityUp: 'зрелость выросла',
  maturityDown: 'зрелость снизилась',
  maturitySame: 'зрелость не изменилась',
  linesChanged: 'изменились линии',
  movingNew: 'новые подвижные линии',
  movingClosed: 'закрылись подвижные линии',
  reached: 'достигнута результирующая гексаграмма предыдущего прогона',
}

export function shiftSummary(diff: any): string[] {
  if (!diff) return []
  const out: string[] = []
  const delta = diff.maturity_delta || 0
  out.push(`${SHIFT_TEXT.maturity} ${diff.maturity_from}/6 → ${diff.maturity_to}/6 (${delta > 0 ? '+' + delta : delta})`)
  if (diff.reached_prev_target) out.push(SHIFT_TEXT.reachedTarget)
  const changes = diff.line_changes || []
  changes.forEach((ch: any) => {
    const label = ch.line_title || ch.line_key
    const dir = ch.direction === 'yin_to_yang' ? SHIFT_TEXT.strengthen : SHIFT_TEXT.weaken
    out.push(`Линия ${ch.line} (${label}): ${dir}`)
  })
  const closed = diff.moving_closed || []
  if (closed.length) out.push(`${SHIFT_TEXT.movingClosedLines}: линии ${closed.join(', ')}.`)
  const movingNew = diff.moving_new || []
  if (movingNew.length) out.push(`${SHIFT_TEXT.movingNewLines}: линии ${movingNew.join(', ')}.`)
  if (!changes.length && !closed.length && !movingNew.length) out.push(SHIFT_TEXT.noLineChanges)
  return out
}

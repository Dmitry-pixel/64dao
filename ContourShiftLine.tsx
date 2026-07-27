'use client'

// Строка сдвига в шапке раздела контура повторного отчёта.
// Экранный аналог backend/app/dynamics_block.py::shift_line_html —
// состав фраз держим одинаковым (правило паритета HTML и PDF).
// Формулировки продублированы намеренно: их правка идёт парой.

export const SHIFT_TEXT = {
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
  if (delta > 0) out.push(SHIFT_TEXT.maturityUp + ': ' + diff.maturity_from + ' → ' + diff.maturity_to)
  else if (delta < 0) out.push(SHIFT_TEXT.maturityDown + ': ' + diff.maturity_from + ' → ' + diff.maturity_to)
  else out.push(SHIFT_TEXT.maturitySame)

  const changes = diff.line_changes || []
  if (changes.length) {
    out.push(SHIFT_TEXT.linesChanged + ': ' + changes.map((c: any) => String(c.line_key || c.line)).join(', '))
  }
  const movingNew = diff.moving_new || []
  if (movingNew.length) out.push(SHIFT_TEXT.movingNew + ': ' + movingNew.join(', '))

  const movingClosed = diff.moving_closed || []
  if (movingClosed.length) out.push(SHIFT_TEXT.movingClosed + ': ' + movingClosed.join(', '))

  if (diff.reached_prev_target) out.push(SHIFT_TEXT.reached)
  return out
}

const STYLE = {
  fontSize: 11,
  fontFamily: 'sans-serif',
  color: '#166534',
  background: 'rgba(22,101,52,0.06)',
  border: '1px solid rgba(22,101,52,0.2)',
  borderRadius: 6,
  padding: '8px 12px',
  margin: '0 0 14px',
  lineHeight: 1.6,
}

export default function ContourShiftLine({ diff }: { diff?: any }) {
  const parts = shiftSummary(diff)
  if (parts.length === 0) return null
  return <p style={STYLE}>{parts.join('; ')}</p>
}

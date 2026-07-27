'use client'
import { shiftSummary } from '@/components/ContourShiftLine'

// Раздел 09 «Динамика» в конце повторного отчёта.
// Экранный аналог backend/app/dynamics_block.py::dynamics_section_html —
// состав блоков держим одинаковым (правило паритета HTML и PDF).

const TEXT = {
  title: 'Динамика',
  comparedWith: 'Сравнение с замером от',
  improved: 'Улучшилось',
  degraded: 'Ухудшилось',
  unchanged: 'Без изменений',
  constraintChanged: 'Контур-ограничение сместился',
  constraintSame: 'Контур-ограничение не изменился',
  baseChanged: 'Базовая гексаграмма изменилась',
  baseSame: 'Базовая гексаграмма прежняя',
}

function fmtDate(iso?: string): string {
  if (!iso || iso.length < 10) return ''
  return iso.slice(8, 10) + '.' + iso.slice(5, 7) + '.' + iso.slice(0, 4)
}

export default function DynamicsSection({
  dyn,
  sectionNo = '09',
  titles = {},
  styles: S,
}: {
  dyn?: any
  sectionNo?: string
  titles?: Record<string, string>
  styles: Record<string, any>
}) {
  if (!dyn || dyn.available !== true) return null

  const contours = dyn.contours || {}
  const keys = Object.keys(contours).sort()
  const summary = dyn.summary || {}
  const constraint = dyn.constraint || {}
  const basePair = dyn.base_pair || {}
  const date = fmtDate(dyn.compare_from?.created_at)

  const name = (key?: string) => (key ? titles[key] || key : '—')
  const list = (keysIn?: string[]) =>
    keysIn && keysIn.length ? keysIn.map(name).join(', ') : '—'

  return (
    <div style={S.section} id="s-dynamics">
      <h2 style={S.sectionH2}><span style={S.num}>{sectionNo}</span>{TEXT.title}</h2>

      {date && <p style={S.reportText}>{TEXT.comparedWith} {date}</p>}

      {keys.map((key) => {
        const parts = shiftSummary(contours[key])
        if (parts.length === 0) return null
        return (
          <div key={key} style={{ marginTop: 14 }}>
            <span style={S.labelRed}>{name(key)}</span>
            <div style={{ ...S.reportText, marginTop: 6 }}>{parts.map((x, i) => <div key={i}>{x}</div>)}</div>
          </div>
        )
      })}

      <div style={{ marginTop: 18 }}>
        <span style={S.labelRed}>{TEXT.improved}</span>
        <p style={{ ...S.reportText, marginTop: 6 }}>{list(summary.improved)}</p>
      </div>
      <div style={{ marginTop: 14 }}>
        <span style={S.labelRed}>{TEXT.degraded}</span>
        <p style={{ ...S.reportText, marginTop: 6 }}>{list(summary.degraded)}</p>
      </div>
      <div style={{ marginTop: 14 }}>
        <span style={S.labelRed}>{TEXT.unchanged}</span>
        <p style={{ ...S.reportText, marginTop: 6 }}>{list(summary.unchanged)}</p>
      </div>

      <p style={{ ...S.reportText, marginTop: 18 }}>
        {constraint.changed
          ? TEXT.constraintChanged + ': ' + name(constraint.from) + ' → ' + name(constraint.to)
          : TEXT.constraintSame + ': ' + name(constraint.to)}
      </p>

      {(basePair.combination_from || basePair.combination_to) && (
        <p style={S.reportText}>
          {basePair.changed
            ? TEXT.baseChanged + ': ' + (basePair.combination_from || '—') + ' → ' + (basePair.combination_to || '—')
            : TEXT.baseSame + ': ' + (basePair.combination_to || '—')}
        </p>
      )}
    </div>
  )
}

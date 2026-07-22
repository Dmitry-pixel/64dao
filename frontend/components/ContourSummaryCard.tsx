'use client'

import React from 'react'

export type ContourSummaryCardProps = {
  sectionNo: string
  summary: any
  styles: Record<string, React.CSSProperties>
}

export default function ContourSummaryCard({ sectionNo, summary, styles: S }: ContourSummaryCardProps) {
  if (!summary) return null
  const rows: any[] = summary.rows || []
  const titleOf = (key: string) => rows.find(r => r.contour === key)?.title || key

  const cap = (t: string) => (
    <div style={{ fontSize: 10, color: '#c0392b', letterSpacing: 2, textTransform: 'uppercase' as const, fontFamily: 'sans-serif', fontWeight: 700, marginBottom: 8 }}>{t}</div>
  )

  let verdict: React.ReactNode
  if (summary.constraint) {
    const name = titleOf(summary.constraint)
    verdict = summary.gap_significant ? (
      <><strong>{name}</strong> — наиболее вероятная зона системного ограничения по данным диагностики.
      Отрыв от ближайшего контура — {summary.gap} балла зрелости, поэтому ресурсы рекомендуется
      сфокусировать здесь, а остальные контуры вести в поддерживающем режиме.</>
    ) : (
      <><strong>{name}</strong> — наиболее вероятная зона системного ограничения по данным диагностики.
      Отрыв от остальных контуров невелик, поэтому работать с ними можно параллельно.</>
    )
  } else {
    const tied = (summary.tied || []).map(titleOf).join(', ')
    verdict = (
      <>Контуры сопоставимы по зрелости{tied ? ` (${tied})` : ''} — по данным диагностики одна функция
      не выделяется как ограничение. Выбор фокуса здесь остаётся управленческим решением,
      а не следствием расчёта.</>
    )
  }

  return (
    <div style={S.section} id="ssum">
      <h2 style={S.sectionH2}><span style={S.num}>{sectionNo}</span>Сводная карта контуров</h2>

      <p style={{ ...S.faint, marginBottom: 16, lineHeight: 1.6 }}>
        Контуры оценены по одной шкале, поэтому их зрелость сравнима между собой.
        Гексаграммы контуров описывают зрелость функции и не связаны с гексаграммой раздела 01:
        там линии означают тип бизнеса, здесь — уровень зрелости.
      </p>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={S.th}>Контур</th>
            <th style={S.th}>Сейчас</th>
            <th style={S.th}>Результирующая</th>
            <th style={S.th}>Зрелость</th>
            <th style={S.th}>Подвижных</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const cur = r.hexagram_current || {}
            const res = r.hexagram_resulting
            const mark = r.is_constraint
            const cell = { ...S.td, ...(mark ? { color: '#c0392b', background: 'rgba(192,57,43,0.06)' } : {}) }
            return (
              <tr key={r.contour}>
                <td style={cell}>{r.title}{mark ? ' — вероятная зона ограничения' : ''}</td>
                <td style={cell}>№{cur.number} {cur.name}</td>
                <td style={cell}>{res ? `№${res.number} ${res.name}` : '—'}</td>
                <td style={cell}>{r.maturity_index}/6</td>
                <td style={cell}>{r.moving_count}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div style={{ marginTop: 16, border: '1px solid rgba(192,57,43,0.2)', borderRadius: 6, padding: '16px 20px', background: 'rgba(192,57,43,0.04)' }}>
        <p style={{ ...S.reportText, margin: 0 }}>{verdict}</p>
        {(summary.stable || []).length > 0 && (
          <p style={{ ...S.faint, marginTop: 10 }}>
            Без подвижных линий: {(summary.stable || []).map(titleOf).join(', ')}.
            Конфигурация устойчива, направленной трансформации не требуется.
          </p>
        )}
      </div>
    </div>
  )
}

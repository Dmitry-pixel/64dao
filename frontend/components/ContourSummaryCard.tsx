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

      {(summary.levels || []).length > 0 && (
        <div style={{ marginTop: 16, border: '1px solid rgba(26,37,64,0.12)', borderRadius: 6, padding: '14px 18px', background: 'rgba(255,255,255,0.45)' }}>
          {cap('Уровни по контурам')}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 13 }}>
            <thead>
              <tr>
                <th style={S.th}>Уровень</th>
                {summary.levels[0].cells.map((c: any) => <th key={c.contour} style={S.th}>{c.title}</th>)}
              </tr>
            </thead>
            <tbody>
              {summary.levels.map((row: any) => {
                const bg = row.systemic_weak ? 'rgba(192,57,43,0.06)'
                  : row.systemic_strong ? 'rgba(26,37,64,0.04)' : undefined
                return (
                  <tr key={row.level}>
                    <td style={{ ...S.td, background: bg }}>{row.title}
                      <span style={{ fontSize: 11, color: 'rgba(26,37,64,0.45)' }}> · {row.question}</span>
                    </td>
                    {row.cells.map((c: any) => (
                      <td key={c.contour} style={{ ...S.td, background: bg, textAlign: 'center', color: c.code === 'BB' ? '#c0392b' : undefined }}>{c.label}</td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
          {summary.levels.filter((r: any) => r.reading).map((r: any) => (
            <p key={r.level} style={{ ...S.reportText, marginTop: 8 }}>{r.reading}</p>
          ))}
          {summary.levels_note && <p style={{ ...S.faint, marginTop: 8 }}>{summary.levels_note}</p>}
        </div>
      )}

      {summary.route?.stages?.length > 0 && (
        <div style={{ marginTop: 16, border: '1px solid rgba(26,37,64,0.12)', borderRadius: 6, padding: '14px 18px', background: 'rgba(255,255,255,0.45)' }}>
          {cap('Сводный маршрут компании')}
          {summary.route.stages.map((st: any) => {
            const cur = st.hexagram_current || {}
            const res = st.hexagram_resulting || {}
            return (
              <div key={st.contour} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderTop: '1px solid rgba(26,37,64,0.08)' }}>
                <div style={{ color: '#c0392b', fontFamily: 'sans-serif', fontWeight: 700, fontSize: 12, minWidth: 58 }}>Этап {st.stage}</div>
                <div style={{ flex: 1, fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540' }}>
                  {titleOf(st.contour)}
                  <div style={S.faint}>{st.route_len} шаг(ов) · точка входа: линия {st.entry_line}</div>
                </div>
                <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)' }}>
                  №{cur.number} <span style={{ color: '#c0392b' }}>→</span> №{res.number}
                </div>
              </div>
            )
          })}
          {(summary.route.stable || []).length > 0 && (
            <p style={{ ...S.faint, marginTop: 10 }}>Стабильные контуры (без маршрута): {(summary.route.stable || []).map(titleOf).join(', ')}.</p>
          )}
          {summary.route.focus_first && (
            <p style={{ marginTop: 8, fontFamily: 'sans-serif', fontSize: 12, color: '#c0392b' }}>
              Рекомендуется сфокусировать ресурсы на этапе 1; остальные контуры — в поддерживающем режиме.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

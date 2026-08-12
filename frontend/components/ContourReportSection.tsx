'use client'

import React from 'react'
import { HexLines } from '@/components/HexDiagram'
import HexagramDetailsLink from '@/components/HexagramDetailsLink'

export const FIN_STATE_RU: Record<string, string> = {
  young_yang: 'Ян — устойчивая сильная позиция',
  old_yang: 'Ян, подвижная — сила на пике',
  young_yin: 'Инь — устойчивая слабая позиция',
  old_yin: 'Инь, подвижная — изменение назрело',
}

export type ContourReportSectionProps = {
  sectionNo: string
  title: string
  anchorId?: string
  result: any
  interp: any
  lineTitles?: Record<string, string>
  styles: Record<string, React.CSSProperties>
  /** Профиль стратегии — только у финансовой функции (Поправка П8) */
  children?: React.ReactNode
}

export default function ContourReportSection({
  sectionNo, title, anchorId, result, interp, lineTitles = {}, styles: S, children,
}: ContourReportSectionProps) {
  const fr = result
  const it = interp
  const hc = fr?.hexagram_current || {}
  const linesByNum: Record<number, any> = {}
  ;(fr?.lines || []).forEach((l: any) => { linesByNum[l.line] = l })

  // Сквозная нумерация разделов: раздел про вето условный, и статичные номера
  // при его отсутствии оставляли бы дыру. Порядок вызовов cap = порядок разметки.
  let secNo = 0
  const cap = (t: string) => {
    secNo += 1
    return (
      <div style={{ fontSize: 10, color: '#c0392b', letterSpacing: 2, textTransform: 'uppercase' as const, fontFamily: 'sans-serif', fontWeight: 700, marginBottom: 8 }}>
        <span style={{ opacity: 0.55, marginRight: 6 }}>{String(secNo).padStart(2, '0')}</span>{t}
      </div>
    )
  }
  const fallback = { margin: 0, fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.5)' } as React.CSSProperties

  return (
    <div style={S.section} id={anchorId}>
      <h2 style={S.sectionH2}><span style={S.num}>{sectionNo}</span>{title}</h2>

      <div style={S.stateGrid}>
        <div style={S.stateCell}>
          <span style={S.labelRed}>Гексаграмма</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 6 }}>
            <HexLines combo={fr?.combination_current || ''} />
            <div style={{ ...S.stateVal, marginTop: 0 }}>№ {hc.number} · {hc.name}</div>
          </div>
        </div>
        <div style={S.stateCell}>
          <span style={S.labelRed}>Комбинация</span>
          <div style={{ ...S.stateVal, fontFamily: 'monospace', letterSpacing: 3 }}>{fr?.combination_current}</div>
        </div>
      </div>

      <HexagramDetailsLink combo={fr?.combination_current} />

      <div style={{ marginTop: 16 }}>
        {cap('Диагноз')}
        <div style={S.reportText}>
          <p style={{ marginBottom: 10 }}>
            <strong>{it?.tonality?.title}</strong> (индекс зрелости {fr?.maturity_index}/6). {it?.tonality?.text}
          </p>
          <p>{it?.pattern_current?.essence} <span style={{ color: '#c0392b' }}>Типичная ошибка:</span> {it?.pattern_current?.mistake}</p>
        </div>
      </div>

      {children}

      <div style={{ marginTop: 18 }}>
        {cap('Профиль линий')}
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 13 }}>
          <thead><tr><th style={S.th}>Линия</th><th style={S.th}>Параметр</th><th style={S.th}>Балл</th><th style={S.th}>Состояние</th></tr></thead>
          <tbody>
            {[6, 5, 4, 3, 2, 1].map(n => {
              const l = linesByNum[n]
              if (!l) return null
              const warn = Array.isArray(l.flags) && l.flags.includes('INCONSISTENT_BLOCK') ? ' ⚠' : ''
              return (
                <tr key={n}>
                  <td style={S.td}>{n}</td>
                  <td style={S.td}>{lineTitles[String(n)] || ''}</td>
                  <td style={S.td}>{typeof l.score === 'number' ? l.score.toFixed(2) : l.score}</td>
                  <td style={S.td}>{(FIN_STATE_RU[l.state] || l.state) + warn}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 16 }}>
        {cap('Ресурс и направление')}
        <div style={{ border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '14px 16px', background: 'rgba(255,255,255,0.5)', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.72)', lineHeight: 1.7 }}>
          <p style={{ marginBottom: 8 }}><strong>Квадрант: {it?.quadrant?.title}</strong>. {it?.quadrant?.text}</p>
          <p style={{ marginBottom: 6 }}><strong>Нижняя ({it?.trigrams?.lower?.title}):</strong> {it?.trigrams?.lower?.text}</p>
          <p><strong>Верхняя ({it?.trigrams?.upper?.title}):</strong> {it?.trigrams?.upper?.text}</p>
        </div>
      </div>

      {(it?.levels?.length ?? 0) > 0 && (
        <div style={{ marginTop: 16 }}>
          {cap('Три уровня')}
          <div style={{ border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '14px 16px', background: 'rgba(255,255,255,0.5)', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.72)', lineHeight: 1.7 }}>
            <p style={{ marginTop: 0, marginBottom: 12, fontSize: 12, color: 'rgba(26,37,64,0.6)' }}>{it.levels_caveat}</p>
            {it.levels.map((lv: any) => (
              <div key={lv.level} style={{ marginBottom: 12 }}>
                <div><strong>{lv.title} — {lv.state_title}</strong> <span style={{ color: 'rgba(26,37,64,0.5)' }}>({(lv.line_titles || []).join(' + ')})</span></div>
                <div style={{ fontSize: 12, marginTop: 3 }}>{lv.text}</div>
                {lv.label_resulting && (
                  <div style={{ fontSize: 12, marginTop: 4, color: '#c0392b' }}>Подвижны линии {(lv.moving_lines || []).join(', ')}: состояние переходит в «{lv.label_resulting}».</div>
                )}
                {lv.caveat && <div style={{ fontSize: 11, marginTop: 4, color: 'rgba(26,37,64,0.5)' }}>{lv.caveat}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        {cap('Ключевые напряжения')}
        {it?.tensions?.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: 18, fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.72)', lineHeight: 1.6 }}>
            {it.tensions.map((t: any) => <li key={t.id} style={{ marginBottom: 6 }}>{t.text}</li>)}
          </ul>
        ) : <p style={fallback}>Явных напряжений между линиями не выявлено.</p>}
      </div>

      {it?.veto_block && (
        <div style={{ marginTop: 16 }}>
          {cap('Условие, блокирующее трансформацию')}
          <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b' }}>
            <strong>{it.veto_block.block_title}</strong> — балл {it.veto_block.score}, линия переопределена в Инь по правилу вето: первое лицо не обозначило развитие этой функции как приоритет.
          </div>
          <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', marginTop: 6 }}>{it.veto_block.package_text}</div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        {cap('Приоритеты вмешательства')}
        {it?.priorities?.length > 0 ? it.priorities.map((pr: any, i: number) => (
          <div key={i} style={{ marginBottom: 10 }}>
            <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540' }}>
              <strong>{pr.block_title}</strong> — {FIN_STATE_RU[pr.state] || pr.state}
            </div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', marginTop: 2 }}>{pr.package_text}</div>
          </div>
        )) : <p style={fallback}>Подвижных линий нет — приоритетных зон вмешательства не выделено.</p>}
      </div>

      <div style={{ marginTop: 16 }}>
        {cap('Плановые шаги')}
        {it?.planned_steps?.length > 0 ? it.planned_steps.map((pr: any, i: number) => (
          <div key={i} style={{ marginBottom: 10 }}>
            <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540' }}><strong>{pr.block_title}</strong></div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', marginTop: 2 }}>{pr.package_text}</div>
          </div>
        )) : <p style={fallback}>Плановых шагов не выделено.</p>}
      </div>

      <div style={{ marginTop: 16 }}>
        {cap('Маршрут перехода')}
        {(it?.route?.length > 0) ? (
          <>
            <div style={{ ...S.transitionCard, flexWrap: 'wrap' as const }}>
              <div style={{ textAlign: 'center' as const }}>
                <HexLines combo={fr?.combination_current || ''} />
                <div style={{ ...S.faint, marginTop: 6 }}>№{hc.number}</div>
              </div>
              {it.route.map((st: any, i: number) => (
                <React.Fragment key={i}>
                  <div style={{ color: '#c0392b', alignSelf: 'center' }}>→</div>
                  <div style={{ textAlign: 'center' as const }}>
                    <HexLines combo={st?.hexagram_after?.code || ''} />
                    <div style={{ ...S.faint, marginTop: 6 }}>№{st?.hexagram_after?.number}</div>
                  </div>
                </React.Fragment>
              ))}
            </div>
            <p style={{ ...S.faint, marginTop: 10, lineHeight: 1.6 }}>
              Последовательность — рекомендуемая логика проработки, а не жёсткое предписание:
              темп и параллельность шагов определяются ресурсами компании.
            </p>
            {it.route.map((st: any, i: number) => (
              <div key={i} style={{ border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '12px 16px', background: 'rgba(255,255,255,0.45)', marginBottom: 10 }}>
                <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540' }}>
                  <b>Шаг {st.order}. Линия {st.line} — {lineTitles[String(st.line)] || ''}</b>{' '}
                  <span style={{ color: 'rgba(26,37,64,0.6)' }}>({st.from_state === 'old_yin' ? 'укрепить слабую позицию' : 'стабилизировать перегрев'})</span>
                  {st.is_veto && <span style={{ color: '#c0392b', fontSize: 11 }}> — снятие блокирующего условия</span>}
                </div>
                <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.75)', marginTop: 5 }}>{st.action_text}</div>
                <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.55)', marginTop: 4 }}>Состояние после шага: {st.after_essence}</div>
                {st.is_last && st.mistake && (
                  <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: '#1a2540', marginTop: 6 }}>
                    <span style={{ color: '#c0392b' }}>Предостережение:</span> {st.mistake}
                  </div>
                )}
              </div>
            ))}
          </>
        ) : (
          <p style={{ ...S.reportText, marginTop: 10 }}>Подвижных линий нет — конфигурация стабильна, направленной трансформации не требуется.</p>
        )}
      </div>

      <div style={{ marginTop: 16 }}>
        {cap('Оговорки по данным')}
        {it?.caveats?.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: 18, fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', lineHeight: 1.5 }}>
            {it.caveats.map((c: string, i: number) => <li key={i} style={{ marginBottom: 6 }}>{c}</li>)}
          </ul>
        ) : <p style={fallback}>Оговорок по качеству данных нет.</p>}
      </div>

      <div style={{ marginTop: 16 }}>
        {cap('Следующие шаги')}
        {it?.next_steps?.length > 0 ? (
          <ol style={{ margin: 0, paddingLeft: 18, fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', lineHeight: 1.6 }}>
            {it.next_steps.map((s: string, i: number) => <li key={i} style={{ marginBottom: 6 }}>{s}</li>)}
          </ol>
        ) : <p style={fallback}>Немедленных шагов не требуется.</p>}
      </div>
    </div>
  )
}

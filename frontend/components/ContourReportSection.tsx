'use client'

import React from 'react'
import { HexLines } from '@/components/HexDiagram'

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

  const cap = (t: string) => (
    <div style={{ fontSize: 10, color: '#c0392b', letterSpacing: 2, textTransform: 'uppercase' as const, fontFamily: 'sans-serif', fontWeight: 700, marginBottom: 8 }}>{t}</div>
  )
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
        {cap('Траектория')}
        {(() => {
          // Карта _TARGET_HEXAGRAM к контурам не применяется (план §0.1):
          // целевая гексаграмма строится инверсией подвижных линий, без них цели нет.
          const moving = !!it?.trajectory
          const rightNum = it?.trajectory?.resulting?.number
          return (
            <>
              <div style={S.transitionCard}>
                <div style={{ textAlign: 'center' as const }}>
                  <HexLines combo={fr?.combination_current || ''} />
                  <div style={{ ...S.faint, marginTop: 6 }}>сейчас · №{hc.number}</div>
                </div>
                {moving && (<>
                  <div style={{ flex: 1, borderTop: '1px dashed rgba(26,37,64,0.2)' }} />
                  <div style={{ textAlign: 'center' as const }}>
                    <HexLines combo={fr?.combination_resulting || ''} />
                    <div style={{ ...S.faint, marginTop: 6 }}>результирующая{rightNum ? ` · №${rightNum}` : ''}</div>
                  </div>
                </>)}
              </div>
              <div style={{ ...S.faint, marginTop: 8 }}>
                {moving
                  ? 'Переход определён подвижными линиями гексаграммы контура.'
                  : 'Подвижных линий нет — конфигурация устойчива.'}
              </div>
              <p style={{ ...S.reportText, marginTop: 10 }}>
                {moving
                  ? <>{it.trajectory.essence} <span style={{ color: '#c0392b' }}>Предостережение:</span> {it.trajectory.mistake}</>
                  : 'Подвижных линий нет — конфигурация стабильна, направленной трансформации не требуется.'}
              </p>
            </>
          )
        })()}
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

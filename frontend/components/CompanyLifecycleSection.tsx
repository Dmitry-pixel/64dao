'use client'

import React from 'react'
import LifecycleChart from '@/components/LifecycleChart'

const STAGE_INDEX: Record<string, number> = {
  'зарождение': 1, 'расцвет': 2, 'зрелость': 3, 'упадок': 4, 'обновление': 5,
}


const FLAG_LABEL: Record<string, string> = {
  CONSTRAINT_TIED: 'Несколько контуров делят минимальную зрелость — ограничение неустойчиво, стадия не фиксируется.',
  CONSTRAINT_STABLE: 'Контур-ограничение без подвижных линий: внутреннего запроса на изменение нет, работа начинается со стратегической сессии.',
  GAP_NOT_SIGNIFICANT: 'Отрыв ограничения от остальных контуров незначим — точка условна, опирайтесь на вектор.',
  STAGE_UNKNOWN: 'Для части гексаграмм стадия жизненного цикла не заполнена в базе стратегий.',
  ARCHETYPE_AMBIGUOUS: 'Якорные стадии и во фронте, и в бэке: типовой сценарий неприменим.',
  HIGH_TURBULENCE: 'Высокая доля подвижных линий: система в фазе широкой трансформации.',
  NO_INTERNAL_PRESSURE: 'Подвижных линий нет ни в одном контуре: конфигурация стабильна (в т.ч. возможен стабильный упадок).',
  RENEWAL_PRESSURE: 'Выраженное давление роста: назревшие слабости преобладают над перегревом.',
  OVERHEAT_RISK: 'Выраженный риск перегрева: подвижные сильные позиции преобладают.',
}

export type CompanyLifecycleSectionProps = {
  sectionNo: string
  lc: any
  summary: any
  styles: Record<string, React.CSSProperties>
}

export default function CompanyLifecycleSection({ sectionNo, lc, summary, styles: S }: CompanyLifecycleSectionProps) {
  if (!lc) return null
  const rows: any[] = summary?.rows || []
  const titleOf = (k: string) => rows.find(r => r.contour === k)?.title || k

  const stageIdx = lc.stage ? STAGE_INDEX[lc.stage] : null
  const frame = (lc.playbook && lc.playbook.frame) || {}
  const tactics: any[] = (lc.playbook && lc.playbook.tactics) || []
  const vector: Record<string, any> = lc.vector || {}
  const flags: string[] = lc.quality_flags || []

  const frameBlock = (label: string, text: string) => (
    <div style={{ background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '12px 14px', marginBottom: 8 }}>
      <div style={{ fontSize: 9, fontFamily: 'sans-serif', letterSpacing: 1, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.45)', fontWeight: 600, marginBottom: 6 }}>{label}</div>
      <p style={{ fontSize: 13, color: '#1a2540', lineHeight: 1.6, margin: 0, fontFamily: 'sans-serif' }}>{text}</p>
    </div>
  )

  const th = (h: string, first: boolean) => (
    <th style={{ textAlign: first ? 'left' as const : 'center' as const, padding: '7px 8px', fontSize: 10, textTransform: 'uppercase' as const, letterSpacing: 1, color: 'rgba(26,37,64,0.4)', fontFamily: 'sans-serif', fontWeight: 400 }}>{h}</th>
  )
  const td = (child: React.ReactNode, center: boolean, mono?: boolean) => (
    <td style={{ padding: '7px 8px', textAlign: center ? 'center' as const : 'left' as const, fontSize: 12, color: '#1a2540', fontFamily: mono ? 'monospace' : 'sans-serif' }}>{child}</td>
  )

  return (
    <div style={S.section} id="s-lc">
      <h2 style={S.sectionH2}><span style={S.num}>{sectionNo}</span>Жизненный цикл компании</h2>

      {lc.constraint ? (
        <p style={{ fontSize: 13, color: 'rgba(26,37,64,0.72)', lineHeight: 1.7, margin: '0 0 12px', fontFamily: 'sans-serif' }}>
          Стадия определяется по контуру-ограничению — <b>{titleOf(lc.constraint)}</b>: система движется со скоростью узкого места.
        </p>
      ) : (
        <p style={{ fontSize: 13, color: 'rgba(26,37,64,0.72)', lineHeight: 1.7, margin: '0 0 12px', fontFamily: 'sans-serif' }}>
          Стадия не фиксируется: минимальную зрелость делят контуры — {(lc.tied || []).map(titleOf).join(', ')}. Требуется дообследование или стратегическая сессия.
        </p>
      )}

      {stageIdx ? <LifecycleChart index={stageIdx} /> : null}

      <div style={{ display: 'inline-block', padding: '4px 14px', borderRadius: 4, fontSize: 13, fontFamily: 'sans-serif', background: 'rgba(30,58,138,0.08)', border: '1px solid rgba(30,58,138,0.2)', color: '#1e3a8a', margin: '14px 0 12px' }}>
        Архетип: {lc.archetype_title}
      </div>

      {frame.environment ? frameBlock('Линия 5 — Внешняя среда — стратегическая рамка', frame.environment) : null}
      {frame.strategy ? frameBlock('Линия 6 — Видение и стратегия — стратегическая рамка', frame.strategy) : null}

      {tactics.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <p style={{ fontSize: 12, color: 'rgba(26,37,64,0.6)', fontFamily: 'sans-serif', margin: '0 0 8px' }}>
            Тактика — фактические подвижные линии контура «{titleOf(lc.playbook.tactics_source)}» (детальные действия — в разделе этого контура):
          </p>
          <ul style={{ margin: '0 0 12px', paddingLeft: 18, fontSize: 12, color: '#1a2540', fontFamily: 'sans-serif', lineHeight: 1.5 }}>
            {tactics.map((st, i) => (
              <li key={i} style={{ marginBottom: 6 }}>
                Шаг {st.order}. Линия {st.line} — {st.line_title || st.line_key}{' '}
                <span style={{ color: 'rgba(26,37,64,0.6)' }}>({st.from_state === 'old_yin' ? 'укрепить слабую позицию' : 'стабилизировать перегрев'})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {Object.keys(vector).length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse' as const, marginBottom: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(26,37,64,0.15)' }}>
              {th('Контур', true)}{th('Стадия сейчас', false)}{th('Стадия после перехода', false)}{th('Подвижных линий', false)}
            </tr>
          </thead>
          <tbody>
            {Object.keys(vector).map((k) => {
              const v = vector[k]
              return (
                <tr key={k}>
                  {td(titleOf(k), false)}
                  {td(v.from || '—', true)}
                  {td(v.to || <span style={{ opacity: 0.45 }}>без перехода</span>, true)}
                  {td(v.moving_count ?? 0, true, true)}
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {flags.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11, color: 'rgba(26,37,64,0.6)', fontFamily: 'sans-serif', lineHeight: 1.5 }}>
          {flags.map((f, i) => <li key={i} style={{ marginBottom: 5 }}>{FLAG_LABEL[f] || f}</li>)}
        </ul>
      )}
    </div>
  )
}

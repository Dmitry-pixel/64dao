'use client'
import { HEXAGRAM_DATA } from '@/lib/hexagrams'

// Выбор целевой гексаграммы для раздела 02 отчёта.
// Пишет в strategies.target_combination (миграция 020).
// Поле неуправляемое: форма стратегии работает через formRef, без перерисовки.
const OPTIONS = [...HEXAGRAM_DATA].sort((a, b) => a.n - b.n)

export function TargetHexagramSelect({
  defaultValue,
  onChange,
}: {
  defaultValue?: string
  onChange: (combo: string) => void
}) {
  return (
    <div style={{ marginBottom: 18 }}>
      <label
        style={{
          display: 'block',
          fontSize: 12,
          color: '#c0392b',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 6,
        }}
      >
        Целевая гексаграмма
      </label>
      <select
        defaultValue={defaultValue || ''}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: '100%',
          padding: '10px 12px',
          border: '1px solid rgba(26,37,64,0.2)',
          borderRadius: 6,
          background: '#fff',
          fontSize: 14,
          color: '#1a2540',
          fontFamily: 'inherit',
        }}
      >
        <option value="">— не задана —</option>
        {OPTIONS.map((h) => (
          <option key={h.combo} value={h.combo}>
            {h.n} &middot; {h.name}
          </option>
        ))}
      </select>
      <p style={{ fontSize: 12, color: 'rgba(26,37,64,0.5)', marginTop: 6 }}>
        Определяет раздел 02 отчёта в HTML и PDF.
      </p>
    </div>
  )
}

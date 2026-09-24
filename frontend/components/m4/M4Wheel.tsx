/**
 * Алмазное колесо: 10 спиц, длина — балл модуля 0–100.
 * Порядок спиц — по номеру модуля по часовой стрелке от верха, как на
 * лендинге. Кольца 40 и 70 — границы состояний (низкий / средний / высокий).
 */
import { STATE_COLOR } from './styles'

interface Props {
  scores: Record<number, number | null>
  names: Record<number, string>
  highlight?: number | null          // системное ограничение
}

const CX = 400
const CY = 250
const R = 170

function point(i: number, v: number) {
  const a = (-90 + i * 36) * (Math.PI / 180)
  return [CX + Math.cos(a) * R * (v / 100), CY + Math.sin(a) * R * (v / 100)]
}

function stateOf(v: number | null) {
  if (v == null) return null
  return v < 40 ? 'low' : v >= 70 ? 'high' : 'mid'
}

export default function M4Wheel({ scores, names, highlight }: Props) {
  const mods = Array.from({ length: 10 }, (_, i) => i + 1)
  const poly = mods.map((m, i) => point(i, scores[m] ?? 0).join(',')).join(' ')
  return (
    <svg viewBox="0 0 800 500" width="100%" role="img" aria-label="Алмазное колесо: баллы десяти модулей"
      style={{ display: 'block', maxWidth: 780 }}>
      {[40, 70, 100].map(r => (
        <circle key={r} cx={CX} cy={CY} r={(R * r) / 100} fill="none"
          stroke="rgba(26,37,64,0.15)" strokeDasharray={r === 100 ? undefined : '3 4'} />
      ))}
      {mods.map((m, i) => {
        const [x, y] = point(i, 100)
        return <line key={m} x1={CX} y1={CY} x2={x} y2={y} stroke="rgba(26,37,64,0.12)" />
      })}
      <polygon points={poly} fill="rgba(26,37,64,0.12)" stroke="#1a2540" strokeWidth={1.5} />
      {mods.map((m, i) => {
        const v = scores[m]
        const [x, y] = point(i, v ?? 0)
        const [lx, ly] = point(i, 118)
        const anchor = Math.abs(lx - CX) < 20 ? 'middle' : lx > CX ? 'start' : 'end'
        const st = stateOf(v)
        return (
          <g key={m}>
            <circle cx={x} cy={y} r={m === highlight ? 7 : 4.5}
              fill={st ? STATE_COLOR[st] : '#999'} stroke={m === highlight ? '#1a2540' : 'none'} strokeWidth={2} />
            <text x={lx} y={ly} textAnchor={anchor} fontFamily="sans-serif" fontSize={12}
              fill="#1a2540" fontWeight={m === highlight ? 700 : 400}>
              {m}. {names[m] ?? ''}
            </text>
            <text x={lx} y={ly + 15} textAnchor={anchor} fontFamily="sans-serif" fontSize={12}
              fill={st ? STATE_COLOR[st] : '#999'}>
              {v == null ? '—' : Math.round(v)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

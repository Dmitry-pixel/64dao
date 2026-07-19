'use client'
import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

type Stage = { sort_order: number; name: string; description: string | null }

const Y = [192, 98, 52, 138, 78]
const X0 = 80
const X1 = 740

function catmull(pts: number[][]): string {
  let d = `M ${pts[0][0]} ${pts[0][1]}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[i + 2] || pts[i + 1]
    d += ` C ${p1[0] + (p2[0] - p0[0]) / 6} ${p1[1] + (p2[1] - p0[1]) / 6},`
    d += ` ${p2[0] - (p3[0] - p1[0]) / 6} ${p2[1] - (p3[1] - p1[1]) / 6},`
    d += ` ${p2[0]} ${p2[1]}`
  }
  return d
}

export default function LifecycleChart({ index }: { index?: number | null }) {
  const [stages, setStages] = useState<Stage[]>([])

  useEffect(() => {
    fetch(`${API}/api/strategies/lifecycle-stages`, { credentials: 'include' })
      .then(r => (r.ok ? r.json() : []))
      .then(d => setStages(Array.isArray(d) ? d : []))
      .catch(() => {})
  }, [])

  if (stages.length < 2) return null

  const cur = stages.findIndex(s => s.sort_order === index)
  const stage = cur >= 0 ? stages[cur] : null
  const pts = stages.map((s, i) => [X0 + ((X1 - X0) * i) / (stages.length - 1), Y[i] ?? 120])

  return (
    <div style={{ marginTop: 18 }}>
      <span style={{ fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 }}>
        Стадия жизненного цикла
      </span>
      <div style={{ fontFamily: 'Georgia,serif', fontSize: 19, color: '#1a2540', marginTop: 6 }}>
        {stage ? stage.name : <em style={{ opacity: 0.4, fontSize: 14 }}>Не определена</em>}
      </div>
      <svg viewBox="0 0 820 252" width="100%" style={{ marginTop: 14 }} xmlns="http://www.w3.org/2000/svg">
        <line x1={X0 - 40} y1={206} x2={X1 + 40} y2={206} stroke="rgba(26,37,64,0.2)" />
        <path d={catmull(pts)} fill="none" stroke="#1e3a8a" strokeWidth={2.5} />
        {pts.map((p, i) => {
          const on = i === cur
          return (
            <g key={i}>
              {on && (
                <line x1={p[0]} y1={p[1] + 11} x2={p[0]} y2={206} stroke="#c0392b" strokeWidth={1.5} strokeDasharray="4 4" />
              )}
              <circle cx={p[0]} cy={p[1]} r={on ? 9 : 5} fill={on ? '#c0392b' : '#fdfcf9'} stroke={on ? '#c0392b' : '#1a2540'} strokeWidth={2} />
              <text x={p[0]} y={228} textAnchor="middle" fontFamily="sans-serif" fontSize={on ? 14.5 : 12.5} fontWeight={on ? 600 : 400} fill={on ? '#c0392b' : 'rgba(26,37,64,0.5)'}>
                {stages[i].name}
              </text>
            </g>
          )
        })}
      </svg>
      {stage?.description && (
        <p style={{ fontFamily: 'sans-serif', fontSize: 13.5, lineHeight: 1.6, color: 'rgba(26,37,64,0.7)', margin: '8px 0 0' }}>
          {stage.description}
        </p>
      )}
    </div>
  )
}

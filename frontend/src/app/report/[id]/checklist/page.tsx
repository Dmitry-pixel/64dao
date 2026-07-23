'use client'
import { useEffect, useState, type CSSProperties } from 'react'
import { useRouter, useParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || ''

type Step = {
  line: number
  order: number
  action_text: string | null
  after_essence: string | null
  is_last: boolean
  done: boolean
  done_at: string | null
}
type ContourBlock = { contour: string; title: string; steps: Step[] }
type Checklist = {
  has_route: boolean
  contours: ContourBlock[]
  total: number
  done: number
  progress: number
}

export default function ChecklistPage() {
  const router = useRouter()
  const params = useParams()
  const assessmentId = params.id as string
  const [data, setData] = useState<Checklist | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/assessments/${assessmentId}/checklist`, { credentials: 'include' })
      .then((r) => {
        if (r.status === 401) { router.push('/login'); return null }
        if (!r.ok) throw new Error('load')
        return r.json()
      })
      .then((d) => { if (d) setData(d) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [assessmentId, router])

  async function toggle(contour: string, line: number, done: boolean) {
    const key = `${contour}/${line}`
    setBusy(key)
    try {
      const r = await fetch(`${API}/api/assessments/${assessmentId}/checklist/${contour}/${line}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done }),
      })
      if (!r.ok) throw new Error('toggle')
      setData((prev) => {
        if (!prev) return prev
        const contours = prev.contours.map((c) =>
          c.contour !== contour ? c : {
            ...c,
            steps: c.steps.map((s) =>
              s.line === line ? { ...s, done, done_at: done ? new Date().toISOString() : null } : s),
          })
        const doneCount = contours.reduce((n, c) => n + c.steps.filter((s) => s.done).length, 0)
        const progress = prev.total ? Math.round((100 * doneCount) / prev.total) : 0
        return { ...prev, contours, done: doneCount, progress }
      })
    } catch {
      /* оставляем как есть */
    } finally {
      setBusy(null)
    }
  }

  if (loading) return <div style={S.wrap}><div style={S.muted}>Загрузка…</div></div>

  return (
    <div style={S.wrap}>
      <div style={S.head}>
        <button style={S.back} onClick={() => router.push(`/report/${assessmentId}`)}>← К отчёту</button>
        <h1 style={S.h1}>Чек-лист действий</h1>
      </div>
      {!data || !data.has_route ? (
        <div style={S.card}><div style={S.muted}>Для этой диагностики маршрут перехода не построен.</div></div>
      ) : (
        <>
          <div style={S.progressWrap}>
            <div style={S.progressBar}><div style={{ ...S.progressFill, width: `${data.progress}%` }} /></div>
            <div style={S.progressText}>{data.done} из {data.total} · {data.progress}%</div>
          </div>
          {data.contours.map((c) => (
            <div key={c.contour} style={S.card}>
              <div style={S.cardTitle}>{c.title}</div>
              {c.steps.map((s) => {
                const key = `${c.contour}/${s.line}`
                return (
                  <label key={key} style={S.step}>
                    <input
                      type="checkbox"
                      checked={s.done}
                      disabled={busy === key}
                      onChange={(e) => toggle(c.contour, s.line, e.target.checked)}
                      style={S.cb}
                    />
                    <span style={{ ...S.stepText, ...(s.done ? S.stepDone : {}) }}>
                      {s.action_text || 'Шаг маршрута'}
                    </span>
                  </label>
                )
              })}
            </div>
          ))}
        </>
      )}
    </div>
  )
}

const S: Record<string, CSSProperties> = {
  wrap: { maxWidth: 820, margin: '0 auto', padding: '32px 20px', fontFamily: 'Georgia, serif', color: '#1a2540' },
  head: { display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 },
  back: { background: 'none', border: 'none', color: 'rgba(26,37,64,0.6)', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
  h1: { fontSize: 26, margin: 0 },
  muted: { color: 'rgba(26,37,64,0.55)', fontFamily: 'sans-serif', fontSize: 14 },
  card: { background: '#fff', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '20px 22px', marginBottom: 16 },
  cardTitle: { fontSize: 12, letterSpacing: 1, textTransform: 'uppercase', color: '#c0392b', fontFamily: 'sans-serif', marginBottom: 14 },
  step: { display: 'flex', gap: 12, alignItems: 'flex-start', padding: '10px 0', borderTop: '1px solid rgba(26,37,64,0.06)', cursor: 'pointer' },
  cb: { marginTop: 4, width: 18, height: 18, cursor: 'pointer', accentColor: '#1e3a8a' },
  stepText: { fontSize: 15, lineHeight: 1.6 },
  stepDone: { textDecoration: 'line-through', color: 'rgba(26,37,64,0.4)' },
  progressWrap: { marginBottom: 20 },
  progressBar: { height: 8, background: 'rgba(26,37,64,0.1)', borderRadius: 99, overflow: 'hidden' },
  progressFill: { height: '100%', background: '#1e3a8a', transition: 'width 0.2s' },
  progressText: { marginTop: 6, fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)' },
}

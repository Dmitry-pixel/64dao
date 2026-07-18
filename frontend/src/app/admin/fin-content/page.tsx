'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface FinContentRow {
  id: string
  kind: string
  key: string
  payload: { title?: string; text?: string; condition?: string }
  sort: number
  is_active: boolean
}

const KINDS: { kind: string; label: string; help: string }[] = [
  { kind: 'tonality',       label: 'Тональность',      help: 'Слой A — тон отчёта по индексу зрелости (число Ян-линий).' },
  { kind: 'quadrant',       label: 'Квадранты',        help: 'Слой B — сочетание нижней (двигатель) и верхней (руль) триграмм.' },
  { kind: 'trigram',        label: 'Триграммы',        help: 'Слой B — характеристика триграммы в нижней и верхней позиции.' },
  { kind: 'tension_rule',   label: 'Правила напряжений', help: 'Слой D — R1–R12. Снятый флаг «Активно» убирает правило из отчёта.' },
  { kind: 'action_package', label: 'Пакеты действий',  help: 'Слой E — рекомендации по подвижным линиям.' },
]

export default function AdminFinContentPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState<FinContentRow[]>([])
  const [activeKind, setActiveKind] = useState('tonality')
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [savedKey, setSavedKey] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getMe()
      .then(u => {
        if (u.role !== 'admin') { router.push('/dashboard'); return }
        return fetch(`${API}/api/fin-content`, { credentials: 'include' })
          .then(r => r.ok ? r.json() : [])
          .then((data: FinContentRow[]) => setRows(data))
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  const update = (id: string, patch: Partial<FinContentRow>) => {
    setRows(prev => prev.map(r => (r.id === id ? { ...r, ...patch } : r)))
  }
  const updatePayload = (id: string, patch: Partial<FinContentRow['payload']>) => {
    setRows(prev => prev.map(r => (r.id === id ? { ...r, payload: { ...r.payload, ...patch } } : r)))
  }

  const save = async (row: FinContentRow) => {
    setSavingKey(row.id); setError(''); setSavedKey(null)
    try {
      const res = await fetch(`${API}/api/fin-content/${row.kind}/${row.key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ payload: row.payload, sort: row.sort, is_active: row.is_active }),
      })
      if (!res.ok) { setError(`Не удалось сохранить ${row.kind}/${row.key} (${res.status})`); return }
      setSavedKey(row.id)
      setTimeout(() => setSavedKey(null), 2000)
    } catch {
      setError('Ошибка сети при сохранении.')
    } finally {
      setSavingKey(null)
    }
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</p>
    </div>
  )

  const current = KINDS.find(k => k.kind === activeKind)!
  const visible = rows.filter(r => r.kind === activeKind).sort((a, b) => a.sort - b.sort || a.key.localeCompare(b.key))

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <AdminNav current="fin-content" />
      <div className="admin-shell">
        <AdminSide current="fin-content" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ marginBottom: 24 }}>
            <span className="label-red">Финансовая функция</span>
            <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 6px' }}>Финансовая интерпретация</h1>
            <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', maxWidth: 720, lineHeight: 1.6, margin: 0 }}>
              Контент раздела «Финансовая функция». Тексты подставляются в отчёт детерминированно —
              структура анкеты и скоринг здесь не меняются. Паттерны гексаграмм (суть/ошибка) редактируются
              в карточке стратегии соответствующей комбинации.
            </p>
          </div>

          {error && (
            <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', marginBottom: 16 }}>{error}</div>
          )}

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
            {KINDS.map(k => {
              const count = rows.filter(r => r.kind === k.kind).length
              const on = k.kind === activeKind
              return (
                <button key={k.kind} onClick={() => setActiveKind(k.kind)}
                  style={{
                    border: on ? '1px solid var(--text)' : '1px solid rgba(26,37,64,0.2)',
                    background: on ? 'var(--text)' : 'transparent',
                    color: on ? '#fff' : 'var(--text)',
                    borderRadius: 6, padding: '8px 14px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer',
                  }}>
                  {k.label} <span style={{ opacity: 0.6 }}>({count})</span>
                </button>
              )
            })}
          </div>

          <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginBottom: 16 }}>{current.help}</p>

          {visible.length === 0 && (
            <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>
              Записей нет. Запустите сид: <code>python /app/seed_fin_content.py</code>
            </p>
          )}

          {visible.map(row => (
            <div key={row.id} style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, padding: '16px 20px', marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                <code style={{ fontFamily: 'monospace', fontSize: 13, color: '#c0392b' }}>{row.key}</code>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)' }}>
                    <input type="checkbox" checked={row.is_active} onChange={e => update(row.id, { is_active: e.target.checked })} />
                    Активно
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)' }}>
                    Порядок
                    <input type="number" value={row.sort} onChange={e => update(row.id, { sort: Number(e.target.value) })}
                      style={{ width: 64, padding: '4px 6px', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 4, fontFamily: 'sans-serif', fontSize: 12 }} />
                  </label>
                  <button onClick={() => save(row)} disabled={savingKey === row.id}
                    style={{ background: savedKey === row.id ? '#166534' : 'var(--text)', color: '#fff', border: 'none', borderRadius: 6, padding: '7px 16px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' }}>
                    {savingKey === row.id ? 'Сохранение…' : savedKey === row.id ? '✓ Сохранено' : 'Сохранить'}
                  </button>
                </div>
              </div>

              <label style={{ display: 'block', fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)', marginBottom: 4 }}>Заголовок</label>
              <input value={row.payload.title || ''} onChange={e => updatePayload(row.id, { title: e.target.value })}
                style={{ width: '100%', boxSizing: 'border-box', padding: '8px 10px', border: '1px solid rgba(26,37,64,0.18)', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, marginBottom: 10 }} />

              <label style={{ display: 'block', fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)', marginBottom: 4 }}>Текст</label>
              <textarea value={row.payload.text || ''} onChange={e => updatePayload(row.id, { text: e.target.value })} rows={3}
                style={{ width: '100%', boxSizing: 'border-box', padding: '8px 10px', border: '1px solid rgba(26,37,64,0.18)', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, lineHeight: 1.6, resize: 'vertical' }} />

              {row.payload.condition !== undefined && (
                <div style={{ marginTop: 8, fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)' }}>
                  Условие (справочно, исполняется кодом): <code style={{ fontFamily: 'monospace' }}>{row.payload.condition}</code>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

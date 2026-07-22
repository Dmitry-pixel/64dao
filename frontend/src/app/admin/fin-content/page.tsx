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
  contour: string
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

const CONTOURS: { key: string; label: string }[] = [
  { key: 'common',  label: 'Общий' },
  { key: 'finance', label: 'Финансовая функция' },
  { key: 'product', label: 'Продукт/Сервис' },
  { key: 'process', label: 'Операционные процессы' },
  { key: 'market',  label: 'Рынок и продажи' },
]

export default function AdminFinContentPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState<FinContentRow[]>([])
  const [activeKind, setActiveKind] = useState('tonality')
  const [activeContour, setActiveContour] = useState('common')
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

  const createOverride = (base: FinContentRow) => {
    const tempId = `new:${base.kind}:${base.key}:${activeContour}`
    if (rows.some(r => r.id === tempId)) return
    setRows(prev => [...prev, {
      id: tempId, kind: base.kind, key: base.key, contour: activeContour,
      payload: { ...base.payload }, sort: base.sort, is_active: base.is_active,
    }])
  }

  const save = async (row: FinContentRow) => {
    setSavingKey(row.id); setError(''); setSavedKey(null)
    try {
      const res = await fetch(`${API}/api/fin-content/${row.kind}/${row.key}?contour=${row.contour}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ payload: row.payload, sort: row.sort, is_active: row.is_active }),
      })
      if (!res.ok) { setError(`Не удалось сохранить ${row.kind}/${row.key} (${res.status})`); return }
      const saved: FinContentRow = await res.json()
      setRows(prev => prev.map(r => (r.id === row.id ? saved : r)))
      setSavedKey(saved.id)
      setTimeout(() => setSavedKey(null), 2000)
    } catch {
      setError('Ошибка сети при сохранении.')
    } finally {
      setSavingKey(null)
    }
  }

  const removeOverride = async (row: FinContentRow) => {
    if (!window.confirm(`Убрать переопределение «${row.key}» для контура? Ключ вернётся к общему тексту.`)) return
    if (row.id.startsWith('new:')) { setRows(prev => prev.filter(r => r.id !== row.id)); return }
    setSavingKey(row.id); setError('')
    try {
      const res = await fetch(`${API}/api/fin-content/${row.kind}/${row.key}?contour=${row.contour}`, {
        method: 'DELETE', credentials: 'include',
      })
      if (!res.ok && res.status !== 204) { setError(`Не удалось убрать переопределение (${res.status})`); return }
      setRows(prev => prev.filter(r => r.id !== row.id))
    } catch {
      setError('Ошибка сети при удалении.')
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
  const commonRows = rows
    .filter(r => r.kind === activeKind && r.contour === 'common')
    .sort((a, b) => a.sort - b.sort || a.key.localeCompare(b.key))
  const overrideOf = (key: string) =>
    rows.find(r => r.kind === activeKind && r.contour === activeContour && r.key === key)
  const isCommon = activeContour === 'common'

  const editor = (row: FinContentRow) => (
    <>
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
    </>
  )

  const saveBtn = (row: FinContentRow) => (
    <button onClick={() => save(row)} disabled={savingKey === row.id}
      style={{ background: savedKey === row.id ? '#166534' : 'var(--text)', color: '#fff', border: 'none', borderRadius: 6, padding: '7px 16px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' }}>
      {savingKey === row.id ? 'Сохранение…' : savedKey === row.id ? '✓ Сохранено' : 'Сохранить'}
    </button>
  )

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
              Тексты подставляются в отчёт детерминированно. «Общий» слой применяется ко всем контурам;
              переопределение под конкретный контур перекрывает общий текст только в его секции отчёта.
              Паттерны гексаграмм (суть/ошибка) редактируются в карточке стратегии.
            </p>
          </div>

          {error && (
            <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', marginBottom: 16 }}>{error}</div>
          )}

          {/* Селектор контура */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
            {CONTOURS.map(c => {
              const on = c.key === activeContour
              const ovr = c.key === 'common' ? 0 : rows.filter(r => r.contour === c.key).length
              return (
                <button key={c.key} onClick={() => setActiveContour(c.key)}
                  style={{
                    border: on ? '1px solid var(--red)' : '1px solid rgba(26,37,64,0.2)',
                    background: on ? 'var(--red)' : 'transparent',
                    color: on ? '#fff' : 'var(--text)',
                    borderRadius: 20, padding: '6px 14px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer',
                  }}>
                  {c.label}{ovr > 0 && <span style={{ opacity: 0.7 }}> · {ovr}</span>}
                </button>
              )
            })}
          </div>

          {/* Селектор вида (kind) */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
            {KINDS.map(k => {
              const count = rows.filter(r => r.kind === k.kind && r.contour === 'common').length
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

          {commonRows.length === 0 && (
            <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>
              Записей нет. Запустите сид: <code>python /app/seed_fin_content.py</code>
            </p>
          )}

          {/* Общий слой — прямое редактирование */}
          {isCommon && commonRows.map(row => (
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
                  {saveBtn(row)}
                </div>
              </div>
              {editor(row)}
            </div>
          ))}

          {/* Контур — переопределения поверх общего слоя */}
          {!isCommon && commonRows.map(base => {
            const ovr = overrideOf(base.key)
            return (
              <div key={base.key} style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, padding: '16px 20px', marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <code style={{ fontFamily: 'monospace', fontSize: 13, color: '#c0392b' }}>{base.key}</code>
                    {ovr
                      ? <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: '#166534', background: 'rgba(46,125,50,0.1)', borderRadius: 10, padding: '2px 8px' }}>переопределено</span>
                      : <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)' }}>наследует общий</span>}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {ovr ? (
                      <>
                        <button onClick={() => removeOverride(ovr)} disabled={savingKey === ovr.id}
                          style={{ background: 'transparent', color: '#c0392b', border: '1px solid rgba(192,57,43,0.4)', borderRadius: 6, padding: '6px 12px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' }}>
                          Убрать
                        </button>
                        {saveBtn(ovr)}
                      </>
                    ) : (
                      <button onClick={() => createOverride(base)}
                        style={{ background: 'var(--text)', color: '#fff', border: 'none', borderRadius: 6, padding: '7px 16px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' }}>
                        Переопределить
                      </button>
                    )}
                  </div>
                </div>
                {ovr ? editor(ovr) : (
                  <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', lineHeight: 1.6, borderLeft: '2px solid rgba(26,37,64,0.12)', paddingLeft: 12 }}>
                    <div style={{ fontWeight: 600, color: 'var(--text)' }}>{base.payload.title || '—'}</div>
                    <div>{base.payload.text || '—'}</div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

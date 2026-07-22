'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface ContourFlag {
  contour: string
  title: string
  enabled: boolean
}

export default function AdminContoursPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [flags, setFlags] = useState<ContourFlag[]>([])
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getMe()
      .then(u => {
        if (u.role !== 'admin') { router.push('/dashboard'); return }
        return fetch(`${API}/api/admin/contours`, { credentials: 'include' })
          .then(r => r.ok ? r.json() : { contours: [] })
          .then((data: { contours: ContourFlag[] }) => setFlags(data.contours || []))
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  const toggle = async (row: ContourFlag, next: boolean) => {
    setSavingKey(row.contour); setError('')
    // Оптимистично: PUT возвращает словарь настроек, не список — переиспользуем
    // локальное состояние и откатываем при ошибке.
    setFlags(prev => prev.map(f => (f.contour === row.contour ? { ...f, enabled: next } : f)))
    try {
      const res = await fetch(`${API}/api/admin/contours/${row.contour}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ enabled: next }),
      })
      if (!res.ok) {
        setFlags(prev => prev.map(f => (f.contour === row.contour ? { ...f, enabled: !next } : f)))
        const msg = await res.text().catch(() => '')
        setError(`Не удалось изменить контур «${row.title}» (${res.status}). ${msg}`)
      }
    } catch {
      setFlags(prev => prev.map(f => (f.contour === row.contour ? { ...f, enabled: !next } : f)))
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

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <AdminNav current="contours" />
      <div className="admin-shell">
        <AdminSide current="contours" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ marginBottom: 24 }}>
            <span className="label-red">Диагностика Метода 1</span>
            <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 6px' }}>Контуры диагностики</h1>
            <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', maxWidth: 720, lineHeight: 1.6, margin: 0 }}>
              Включение контура открывает его прохождение из кабинета после основной диагностики.
              Настройка применяется сразу, без пересборки образа. Финансовый контур входит в
              обязательную анкету Метода 1 и отключён быть не может.
            </p>
          </div>

          {error && (
            <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', marginBottom: 16 }}>{error}</div>
          )}

          {flags.map(row => {
            const locked = row.contour === 'finance'
            return (
              <div key={row.contour} style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, padding: '16px 20px', marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontFamily: 'Georgia,serif', fontSize: 17, color: 'var(--text)' }}>{row.title}</div>
                  <code style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-mute)' }}>{row.contour}</code>
                  {locked && (
                    <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginLeft: 10 }}>— обязательный, всегда включён</span>
                  )}
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text)', cursor: locked ? 'default' : 'pointer', opacity: savingKey === row.contour ? 0.6 : 1 }}>
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    disabled={locked || savingKey === row.contour}
                    onChange={e => toggle(row, e.target.checked)}
                    style={{ width: 20, height: 20 }}
                  />
                  {row.enabled ? 'Включён' : 'Выключен'}
                </label>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

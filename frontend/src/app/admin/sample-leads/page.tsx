'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const CHANNEL: Record<string, { label: string; color: string; bg: string }> = {
  email:    { label: 'E-mail',   color: '#c0392b', bg: 'rgba(192,57,43,0.1)' },
  telegram: { label: 'Telegram', color: '#1785b8', bg: 'rgba(42,171,238,0.14)' },
  max:      { label: 'Max',      color: '#6d28d9', bg: 'rgba(124,58,237,0.12)' },
}

interface Lead { id: string; name: string; channel: string; address: string; created_at: string | null }

function fmt(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function AdminSampleLeadsPage() {
  const router = useRouter()
  const [rows, setRows] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))

    fetch(`${API}/api/sample-report/leads`, { credentials: 'include' })
      .then(r => (r.ok ? r.json() : []))
      .then((data: Lead[]) => setRows(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <AdminNav current="sample-leads" />
      <div className="admin-shell">
        <AdminSide current="sample-leads" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <span className="label-red">Система</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>Сбор Адресов</h1>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>
                {loading ? 'Загружаем…' : `Контакты из формы «Посмотреть пример отчёта» · ${rows.length}`}
              </p>
            </div>
            <a className="btn btn-primary" href={`${API}/api/sample-report/leads.csv`} style={{ padding: '9px 20px', fontSize: 13, textDecoration: 'none' }}>
              ↓ Экспорт CSV
            </a>
          </div>

          {loading ? (
            <div style={{ padding: '48px 0', textAlign: 'center', fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text-mute)' }}>Загрузка…</div>
          ) : rows.length === 0 ? (
            <div className="dash-empty">
              <span style={{ fontSize: 40, display: 'block', marginBottom: 12 }}>📭</span>
              <h3>Заявок пока нет</h3>
              <p>Здесь появятся имена и контакты тех, кто запросил пример отчёта.</p>
            </div>
          ) : (
            <table className="tbl">
              <thead><tr><th>Имя</th><th>Канал</th><th>Адрес</th><th>Дата</th></tr></thead>
              <tbody>
                {rows.map(r => {
                  const c = CHANNEL[r.channel] ?? { label: r.channel, color: '#555', bg: 'rgba(0,0,0,0.06)' }
                  return (
                    <tr key={r.id}>
                      <td>{r.name}</td>
                      <td><span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, fontFamily: 'sans-serif', fontSize: 11, fontWeight: 600, color: c.color, background: c.bg }}>{c.label}</span></td>
                      <td style={{ fontFamily: 'monospace' }}>{r.address}</td>
                      <td style={{ fontFamily: 'monospace' }}>{fmt(r.created_at)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

        </div>
      </div>
    </>
  )
}

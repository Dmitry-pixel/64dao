'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

// Какой документ запрашивали. Строки, собранные до переезда формы, могут
// прийти без source — показываем их как «—», а не подставляем догадку.
const SOURCE: Record<string, { label: string; color: string; bg: string }> = {
  sample_m12:  { label: 'Пример · М1-2',  color: '#1e3a8a', bg: 'rgba(30,58,138,0.10)' },
  sample_m3:   { label: 'Пример · М3',    color: '#1785b8', bg: 'rgba(42,171,238,0.14)' },
  methodology: { label: 'Методика',       color: '#6d28d9', bg: 'rgba(124,58,237,0.12)' },
}

interface Lead {
  id: string
  name: string
  channel: string
  address: string
  email: string | null
  phone: string | null
  max_address: string | null
  telegram_address: string | null
  source: string | null
  created_at: string | null
}

function fmt(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// У старых строк контакт лежит в address, у новых — в отдельных колонках.
// Функция сводит оба случая к одному значению, чтобы таблица не показывала
// пустоту там, где контакт на самом деле есть.
function legacy(r: Lead, channel: string, value: string | null): string | null {
  if (value) return value
  return r.channel === channel ? r.address : null
}

const mono = { fontFamily: 'monospace', whiteSpace: 'nowrap' as const }

export default function AdminSampleLeadsPage() {
  const router = useRouter()
  const [rows, setRows] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  // Очистка доступна только после выгрузки CSV в этой вкладке: иначе легко
  // стереть контакты, которые ещё никуда не сохранены.
  const [exported, setExported] = useState(false)
  const [purging, setPurging] = useState(false)
  const [notice, setNotice] = useState('')

  const load = () =>
    fetch(`${API}/api/sample-report/leads`, { credentials: 'include' })
      .then(r => (r.ok ? r.json() : []))
      .then((data: Lead[]) => setRows(data))
      .catch(() => {})
      .finally(() => setLoading(false))

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))
    load()
  }, [])

  async function handlePurge() {
    // Граница: самая свежая заявка из тех, что видны и выгружены. Заявка,
    // пришедшая после загрузки страницы, под удаление не попадёт. Строку
    // времени передаём как пришла с сервера: Date в браузере срезал бы
    // микросекунды, и граничная запись осталась бы в базе.
    const upTo = rows.find(r => r.created_at)?.created_at
    if (!upTo) return
    if (!confirm(`Удалить ${rows.length} заявок из базы?\n\nУбедитесь, что CSV сохранён. Заявки, пришедшие после открытия страницы, останутся.`)) return
    setPurging(true)
    setNotice('')
    try {
      const res = await fetch(`${API}/api/sample-report/leads?up_to=${encodeURIComponent(upTo)}`, {
        method: 'DELETE', credentials: 'include',
      })
      if (!res.ok) throw new Error(String(res.status))
      const data = await res.json()
      setNotice(`Удалено заявок: ${data.deleted}`)
      setExported(false)
      await load()
    } catch {
      setNotice('Не удалось очистить список. Попробуйте ещё раз.')
    } finally {
      setPurging(false)
    }
  }

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
                {loading ? 'Загружаем…' : `Контакты из форм скачивания примеров отчёта и методики · ${rows.length}`}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <a className="btn btn-primary" href={`${API}/api/sample-report/leads.csv`}
                onClick={() => setExported(true)}
                style={{ padding: '9px 20px', fontSize: 13, textDecoration: 'none' }}>
                ↓ Экспорт CSV
              </a>
              <button className="btn btn-danger" style={{ padding: '9px 20px', fontSize: 13 }}
                disabled={!exported || purging || rows.length === 0}
                title={exported ? 'Удалить выгруженные заявки' : 'Сначала скачайте CSV'}
                onClick={handlePurge}>
                {purging ? 'Удаляем…' : 'Очистить'}
              </button>
            </div>
          </div>
          {rows.length > 0 && !exported && (
            <p className="faint" style={{ fontFamily: 'sans-serif', fontSize: 12, margin: '-16px 0 18px' }}>
              Кнопка «Очистить» станет доступна после экспорта CSV.
            </p>
          )}
          {notice && (
            <div style={{ fontFamily: 'sans-serif', fontSize: 13, marginBottom: 16, color: notice.startsWith('Удалено') ? 'var(--green)' : 'var(--red)' }}>
              {notice}
            </div>
          )}

          {loading ? (
            <div style={{ padding: '48px 0', textAlign: 'center', fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text-mute)' }}>Загрузка…</div>
          ) : rows.length === 0 ? (
            <div className="dash-empty">
              <span style={{ fontSize: 40, display: 'block', marginBottom: 12 }}>📭</span>
              <h3>Заявок пока нет</h3>
              <p>Здесь появятся имена и контакты тех, кто запросил пример отчёта или методику.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Имя</th>
                    <th>E-mail</th>
                    <th>Телефон</th>
                    <th>Max</th>
                    <th>Telegram</th>
                    <th>Документ</th>
                    <th>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(r => {
                    const email = legacy(r, 'email', r.email)
                    const max = legacy(r, 'max', r.max_address)
                    const tg = legacy(r, 'telegram', r.telegram_address)
                    const s = r.source ? SOURCE[r.source] : null
                    return (
                      <tr key={r.id}>
                        <td>{r.name}</td>
                        <td style={mono}>{email ?? '—'}</td>
                        <td style={mono}>{r.phone ?? '—'}</td>
                        <td style={mono}>{max ?? '—'}</td>
                        <td style={mono}>{tg ?? '—'}</td>
                        <td>
                          {s ? (
                            <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 20, fontFamily: 'sans-serif', fontSize: 11, fontWeight: 600, color: s.color, background: s.bg, whiteSpace: 'nowrap' }}>{s.label}</span>
                          ) : '—'}
                        </td>
                        <td style={mono}>{fmt(r.created_at)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

        </div>
      </div>
    </>
  )
}

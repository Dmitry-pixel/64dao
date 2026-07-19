'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'
import { HEXAGRAM_DATA } from '@/lib/hexagrams'

function comboToHex(combo: string): string {
  const num = HEXAGRAM_ORDER[combo]
  if (!num) return '?'
  return String.fromCodePoint(0x4DC0 + num - 1)
}

const HEXAGRAM_ORDER: Record<string, number> = Object.fromEntries(
  HEXAGRAM_DATA.map(h => [h.combo, h.n] as [string, number])
)

export default function AdminStrategiesPage() {
  const router = useRouter()
  const [strategies, setStrategies] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        const data = await adminApi.strategies() as any[]
        data.sort((a: any, b: any) => (HEXAGRAM_ORDER[a.combination] ?? 99) - (HEXAGRAM_ORDER[b.combination] ?? 99))
        setStrategies(data)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const filtered = strategies.filter(s =>
    (s.combination ?? '').includes(search.toUpperCase()) ||
    (s.title ?? '').toLowerCase().includes(search.toLowerCase())
  )

  const published = strategies.filter(s => s.is_published).length

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>

  return (
    <>
      <AdminNav current="strategies" />
      <div className="admin-shell">
        <AdminSide current="strategies" />
        <div className="admin-main">
          <div className="admin-header">
            <div>
              <span className="label-red">Контент</span>
              <h1>64 стратегии</h1>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <input
                placeholder="Поиск…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, minWidth: 240, background: 'var(--card)', outline: 'none' }}
              />
            </div>
          </div>

          <div className="card-flat" style={{ marginBottom: 14, display: 'flex', gap: 24, fontFamily: 'sans-serif', fontSize: 13 }}>
            <span><strong>{published} опубликовано</strong> <span className="faint" style={{ marginLeft: 6 }}>· {strategies.length - published} в черновиках</span></span>
            <span style={{ color: 'var(--text-mute)' }}>Каждая запись — одна из 64 гексаграмм.</span>
          </div>

          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: 40 }}>№</th>
                <th style={{ width: 60 }}>Гекс.</th>
                <th style={{ width: 100 }}>Комбинация</th>
                <th>Заголовок</th>
                <th>Стадия</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const num = HEXAGRAM_ORDER[s.combination] ?? '?'
                return (
                  <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => router.push(`/admin/strategies/${s.combination}`)}>
                    <td style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', textAlign: 'center' }}>{num}</td>
                    <td>
                      <span style={{ fontSize: 22 }}>{comboToHex(s.combination)}</span>
                    </td>
                    <td><code style={{ fontSize: 12 }}>{s.combination}</code></td>
                    <td style={{ fontWeight: 500 }}>{s.title ?? <span className="faint">без названия</span>}</td>
                    <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>{s.lifecycle_stage ?? '—'}</td>
                    <td>
                      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: s.is_published ? '#d4edda' : '#f8d7da', color: s.is_published ? '#155724' : '#721c24' }}>
                        {s.is_published ? 'Опубликовано' : 'Черновик'}
                      </span>
                    </td>
                    <td>
                      <button className="btn-sm" onClick={e => { e.stopPropagation(); router.push(`/admin/strategies/${s.combination}`) }}>Редактировать</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

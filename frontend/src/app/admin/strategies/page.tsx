'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

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
        <AdminSide current="strategies" stats={{ users: 0, strategies: published, reports: 0 }} />
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
                <th style={{ width: 60 }}>Гекс.</th>
                <th style={{ width: 100 }}>Комбинация</th>
                <th>Заголовок</th>
                <th>Стадия</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => {
                const hexIdx = HEX_TRIGRAMS.findIndex((_, idx) => idx === i)
                return (
                  <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => router.push(`/admin/strategies/${s.id}`)}>
                    <td>
                      <span className="hex hex-sm">{HEX_TRIGRAMS[i % 64]}</span>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{s.combination}</td>
                    <td><strong>{s.title ?? '—'}</strong></td>
                    <td style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>{s.lifecycle_stage ?? '—'}</td>
                    <td>
                      {s.is_published
                        ? <span className="pill pill-completed">опубликовано</span>
                        : <span className="pill pill-draft">черновик</span>
                      }
                    </td>
                    <td>
                      <div className="row-actions">
                        <button onClick={e => { e.stopPropagation(); router.push(`/admin/strategies/${s.id}`) }}>
                          Редактировать
                        </button>
                      </div>
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

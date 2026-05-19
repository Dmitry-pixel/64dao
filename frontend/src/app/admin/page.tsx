'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe } from '@/lib/api'
import { hexFor } from '@/components/AdminNav'
import { AdminNav, AdminSide } from '@/components/AdminNav'

export default function AdminStatsPage() {
  const router = useRouter()
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        const data = await adminApi.stats()
        setStats(data)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>
  if (!stats) return null

  return (
    <>
      <AdminNav current="stats" />
      <div className="admin-shell">
        <AdminSide current="stats" />
        <div className="admin-main">
          <div className="admin-header">
            <div>
              <span className="label-red">Админ-панель</span>
              <h1>Сводка</h1>
            </div>
          </div>

          <div className="stat-grid">
            <div className="stat-card">
              <span className="label-red">Пользователи</span>
              <div className="stat-num">{stats.total_users}</div>
            </div>
            <div className="stat-card">
              <span className="label-red">Диагностики</span>
              <div className="stat-num">{stats.total_assessments}</div>
            </div>
            <div className="stat-card">
              <span className="label-red">PDF-отчёты</span>
              <div className="stat-num">{stats.total_reports}</div>
            </div>
            <div className="stat-card">
              <span className="label-red">Опубликовано стратегий</span>
              <div className="stat-num">{stats.published_strategies} / 64</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }} className="two-col">
            <div className="card">
              <span className="label-red" style={{ display: 'block', marginBottom: 14 }}>Последние пользователи</span>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Роль</th>
                    <th>Создан</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_users?.map((u: any) => (
                    <tr key={u.id}>
                      <td>{u.email}</td>
                      <td>{u.role}</td>
                      <td>{new Date(u.created_at).toLocaleDateString('ru')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card">
              <span className="label-red" style={{ display: 'block', marginBottom: 14 }}>Последние диагностики</span>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Гексаграмма</th>
                    <th>Статус</th>
                    <th>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_assessments?.map((a: any) => (
                    <tr key={a.id}>
                      <td>
                        <span className="hex hex-sm">{hexFor(a.method1_combination ?? '')}</span>
                        {' '}<span style={{ fontFamily: 'monospace', fontSize: 12 }}>{a.method1_combination ?? '—'}</span>
                      </td>
                      <td>
                        <span className={`pill pill-${a.status}`}>{a.status}</span>
                      </td>
                      <td>{new Date(a.created_at).toLocaleDateString('ru')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

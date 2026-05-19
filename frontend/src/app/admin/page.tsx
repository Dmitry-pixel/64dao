'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe } from '@/lib/api'
import { hexFor } from '@/components/AdminNav'
import { AdminNav, AdminSide } from '@/components/AdminNav'

function PurchasesChart({ data }: { data: { date: string; count: number; amount: number }[] }) {
  if (!data || data.length === 0) return null

  const maxCount = Math.max(...data.map(d => d.count), 1)
  const W = 600, H = 140, PAD = { top: 12, right: 8, bottom: 32, left: 28 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom
  const barW = Math.max(2, chartW / data.length - 2)

  // показываем только каждую 5ю метку даты
  const fmt = (d: string) => {
    const [, m, day] = d.split('-')
    return `${day}.${m}`
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      {/* Горизонтальные линии */}
      {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
        const y = PAD.top + chartH * (1 - ratio)
        return (
          <g key={ratio}>
            <line x1={PAD.left} y1={y} x2={W - PAD.right} y2={y}
              stroke="rgba(26,37,64,0.07)" strokeWidth="1" />
            {ratio > 0 && (
              <text x={PAD.left - 4} y={y + 4} textAnchor="end"
                fontSize="9" fontFamily="sans-serif" fill="rgba(26,37,64,0.35)">
                {Math.round(maxCount * ratio)}
              </text>
            )}
          </g>
        )
      })}

      {/* Бары */}
      {data.map((d, i) => {
        const x = PAD.left + i * (chartW / data.length) + (chartW / data.length - barW) / 2
        const barH = d.count === 0 ? 0 : Math.max(3, (d.count / maxCount) * chartH)
        const y = PAD.top + chartH - barH
        return (
          <g key={d.date}>
            <rect x={x} y={y} width={barW} height={barH}
              fill={d.count > 0 ? '#1e3a8a' : 'rgba(26,37,64,0.08)'}
              rx="2" />
            {/* Метки дат каждые 5 дней */}
            {i % 5 === 0 && (
              <text x={x + barW / 2} y={H - 4} textAnchor="middle"
                fontSize="9" fontFamily="sans-serif" fill="rgba(26,37,64,0.4)">
                {fmt(d.date)}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

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

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка...</div>
  if (!stats) return null

  const totalRevenue = (stats.total_revenue ?? 0).toLocaleString('ru-RU')
  const hasOrders = stats.orders_by_day?.some((d: any) => d.count > 0)

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

          {/* График покупок */}
          <div style={{ padding: '0 24px 24px' }}>
            <div className="card" style={{ padding: '20px 24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div>
                  <span className="label-red" style={{ display: 'block', marginBottom: 4 }}>Статистика покупок</span>
                  <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', margin: 0 }}>
                    Количество заказов за последние 30 дней
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 24, textAlign: 'right' as const }}>
                  <div>
                    <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)', letterSpacing: 1, textTransform: 'uppercase' as const }}>Заказов</div>
                    <div style={{ fontFamily: 'Georgia,serif', fontSize: 24, color: 'var(--text)', lineHeight: 1.2 }}>{stats.total_orders ?? 0}</div>
                  </div>
                  <div>
                    <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)', letterSpacing: 1, textTransform: 'uppercase' as const }}>Выручка</div>
                    <div style={{ fontFamily: 'Georgia,serif', fontSize: 24, color: 'var(--text)', lineHeight: 1.2 }}>{totalRevenue} ₽</div>
                  </div>
                </div>
              </div>

              {hasOrders ? (
                <PurchasesChart data={stats.orders_by_day} />
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column' as const, alignItems: 'center', padding: '32px 0', gap: 8 }}>
                  <PurchasesChart data={stats.orders_by_day} />
                  <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', marginTop: 8 }}>
                    Покупок пока нет — график обновится автоматически
                  </p>
                </div>
              )}

              <div style={{ display: 'flex', gap: 16, marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(26,37,64,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)' }}>
                  <div style={{ width: 12, height: 12, borderRadius: 2, background: '#1e3a8a' }} />
                  Заказов в день
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, padding: '0 24px 24px' }} className="two-col">
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

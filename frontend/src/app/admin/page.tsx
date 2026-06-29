'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

export default function AdminPage() {
  const router = useRouter()
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then(u => {
        if (u.role !== 'admin') { router.push('/dashboard'); return }
        return adminApi.stats().then((s: any) => setStats(s))
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif', color: '#999' }}>
      Загрузка...
    </div>
  )

  return (
    <>
      <AdminNav current="stats" />
      <div className="admin-shell">
        <AdminSide current="stats" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <span className="label-red">Обзор</span>
          <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: '#1a2540', margin: '6px 0 28px' }}>
            Сводка
          </h1>

          {stats && (
            <div className="admin-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 32 }}>
              {[
                ['Пользователей', stats.total_users],
                ['Диагностик', stats.total_assessments],
                ['Отчётов', stats.total_reports],
                ['Стратегий', `${stats.published_strategies}/64`],
              ].map(([label, value]) => (
                <div key={label as string} style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.08)', borderRadius: 10, padding: 24, textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', marginBottom: 6 }}>{value}</div>
                  <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.45)' }}>{label}</div>
                </div>
              ))}
            </div>
          )}

          {stats?.recent_users?.length > 0 && (
            <div style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.08)', borderRadius: 10, padding: 24, marginBottom: 16 }}>
              <span className="label-red">Последние регистрации</span>
              <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12, fontFamily: 'sans-serif', fontSize: 13 }}>
                <thead>
                  <tr>{['Email', 'Имя', 'Компания', 'Дата'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '6px 12px', color: 'rgba(26,37,64,0.4)', fontWeight: 500, borderBottom: '1px solid rgba(26,37,64,0.08)' }}>{h}</th>
                  ))}</tr>
                </thead>
                <tbody>
                  {stats.recent_users.map((u: any) => (
                    <tr key={u.id}>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid rgba(26,37,64,0.05)', color: '#1a2540' }}>{u.email}</td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid rgba(26,37,64,0.05)', color: '#1a2540' }}>{u.full_name || '—'}</td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid rgba(26,37,64,0.05)', color: '#1a2540' }}>{u.company_name || '—'}</td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid rgba(26,37,64,0.05)', color: 'rgba(26,37,64,0.45)' }}>{new Date(u.created_at).toLocaleDateString('ru-RU')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

        </div>
      </div>
    </>
  )
}

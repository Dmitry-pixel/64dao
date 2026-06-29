'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getMe, adminApi, listAssessments, reportDownloadUrl } from '@/lib/api'

export default function AdminUserPage() {
  const router = useRouter()
  const params = useParams()
  const userId = params.id as string
  const [userData, setUserData] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then(me => {
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        return Promise.all([
          adminApi.users().then((users: unknown) => { const userList = users as any[];
            const u = userList.find((u: any) => u.id === userId)
            if (u) setUserData(u)
          }),
          adminApi.reports().then((assessments: unknown) => { const assessList = assessments as any[];
            setAssessments(assessList.filter((a: any) => a.user_id === userId))
          }),
        ])
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router, userId])

  if (loading) return (
    <div style={S.center}><p style={{ color: '#666', fontFamily: 'sans-serif' }}>Загрузка...</p></div>
  )

  if (!userData) return (
    <div style={S.center}><p style={{ color: '#666', fontFamily: 'sans-serif' }}>Пользователь не найден</p></div>
  )

  return (
    <div style={S.page}>
      <div style={S.container}>

        <div style={S.header}>
          <div>
            <button onClick={() => router.push('/admin')} style={S.backBtn}>← Назад в админку</button>
            <h1 style={S.h1}>{userData.full_name || userData.email}</h1>
            <p style={{ color: '#666', fontFamily: 'sans-serif', fontSize: 14, marginTop: 4 }}>
              {userData.email} · <span style={userData.role === 'admin' ? S.badgeAdmin : S.badgeUser}>{userData.role}</span>
            </p>
          </div>
        </div>

        {/* Информация о пользователе */}
        <div style={S.card}>
          <h2 style={S.h2}>Информация</h2>
          <div className="admin-info-grid" style={S.infoGrid}>
            <div><span style={S.infoLabel}>Email</span><span style={S.infoValue}>{userData.email}</span></div>
            <div><span style={S.infoLabel}>Имя</span><span style={S.infoValue}>{userData.full_name || '—'}</span></div>
            <div><span style={S.infoLabel}>Компания</span><span style={S.infoValue}>{userData.company_name || '—'}</span></div>
            <div><span style={S.infoLabel}>Роль</span><span style={S.infoValue}>{userData.role}</span></div>
            <div><span style={S.infoLabel}>Зарегистрирован</span><span style={S.infoValue}>{new Date(userData.created_at).toLocaleDateString('ru-RU')}</span></div>
          </div>
        </div>

        {/* Диагностики пользователя */}
        <div style={S.card}>
          <h2 style={S.h2}>Диагностики ({assessments.length})</h2>
          {assessments.length === 0 ? (
            <p style={{ color: '#999', fontFamily: 'sans-serif', fontSize: 13 }}>Нет диагностик</p>
          ) : (
            <table style={S.table}>
              <thead>
                <tr>{['Комбинация', 'Статус', 'Отчётов', 'Дата', ''].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {assessments.map((a: any) => (
                  <tr key={a.id}>
                    <td style={{ ...S.td, fontFamily: 'monospace', letterSpacing: 2, fontWeight: 700 }}>{a.method1_combination || '—'}</td>
                    <td style={S.td}>{a.status}</td>
                    <td style={S.td}>{a.reports.length}</td>
                    <td style={S.td}>{new Date(a.created_at).toLocaleDateString('ru-RU')}</td>
                    <td style={S.td}>
                      {a.reports[0] && (
                        <a href={reportDownloadUrl(a.reports[0].id)} target="_blank" rel="noreferrer"
                          style={{ color: '#1a2540', fontWeight: 600, textDecoration: 'none', fontSize: 13 }}>
                          ↓ PDF
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#e8e4db', fontFamily: 'Arial,sans-serif', padding: '32px 16px' },
  center: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#e8e4db' },
  container: { maxWidth: 800, margin: '0 auto' },
  header: { marginBottom: 24 },
  backBtn: { background: 'none', border: 'none', color: '#c0392b', fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif', padding: 0, marginBottom: 12, display: 'block' },
  h1: { color: '#1a2540', margin: 0, fontSize: 24, fontWeight: 700, fontFamily: 'Georgia,serif' },
  h2: { color: '#1a2540', margin: '0 0 16px', fontSize: 16, fontWeight: 600, fontFamily: 'sans-serif' },
  card: { background: '#fff', borderRadius: 10, padding: '20px 24px', marginBottom: 16 },
  infoGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 },
  infoLabel: { display: 'block', fontSize: 11, color: '#999', fontFamily: 'sans-serif', marginBottom: 2 },
  infoValue: { fontSize: 14, color: '#1a2540', fontFamily: 'sans-serif', fontWeight: 500 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'sans-serif' },
  th: { padding: '8px 12px', textAlign: 'left', color: '#999', fontWeight: 500, borderBottom: '1px solid #f0ede8' },
  td: { padding: '10px 12px', borderBottom: '1px solid #f7f5f2', color: '#333' },
  badgeAdmin: { background: '#fef3c7', color: '#92400e', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500, fontFamily: 'sans-serif' },
  badgeUser: { background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500, fontFamily: 'sans-serif' },
}

'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, logout, type AuthUser } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface Order {
  id: string
  assessment_id: string
  amount: number
  currency: string
  status: string
  payment_id: string | null
  paid_at: string | null
  created_at: string
  assessment?: {
    method1_combination: string | null
    method2_data: any
    reports: { id: string }[]
  }
}

export default function PurchasesPage() {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then(u => {
        setUser(u)
        return fetch(`${API}/api/payments/orders`, { credentials: 'include' })
          .then(r => r.ok ? r.json() : [])
          .then(data => setOrders(Array.isArray(data) ? data : []))
          .catch(() => setOrders([]))
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  async function handleLogout() {
    await logout()
    router.push('/login')
  }

  function statusLabel(status: string) {
    return { pending: 'Ожидает', paid: 'Оплачен', failed: 'Ошибка', refunded: 'Возврат' }[status] ?? status
  }

  function statusStyle(status: string): React.CSSProperties {
    const styles: Record<string, React.CSSProperties> = {
      paid: { background: '#dcfce7', color: '#166534' },
      pending: { background: '#fef9c3', color: '#854d0e' },
      failed: { background: '#fee2e2', color: '#991b1b' },
      refunded: { background: '#f1f5f9', color: '#475569' },
    }
    return { ...S.pill, ...(styles[status] || styles.pending) }
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка...</p>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      {/* Навигация */}
      <nav style={S.nav}>
        <div style={S.navInner}>
          <div style={S.navLogo} onClick={() => router.push('/dashboard')}>
            <span style={S.logo64}>64</span><span style={S.logoDao}> ДАО</span>
          </div>
          <div style={S.navLinks}>
            <button style={S.navLink} onClick={() => router.push('/dashboard')}>Личный кабинет</button>
            <button style={S.navLink} onClick={() => router.push('/reports')}>Мои отчёты</button>
            <button style={{ ...S.navLink, ...S.navLinkOn }}>Мои покупки</button>
            <button style={S.navLink} onClick={() => router.push('/profile')}>Профиль</button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={S.navEmail}>{user?.email}</span>
            <div style={S.avatar}>{(user?.full_name || user?.email || 'U')[0].toUpperCase()}</div>
            <button style={S.navLogout} onClick={handleLogout}>Выйти</button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div style={S.hero}>
        <span style={S.labelRed}>Личный кабинет</span>
        <h1 style={S.heroH1}>Мои покупки</h1>
        <p style={S.heroSub}>История оплат и доступ к отчётам</p>
      </div>

      {/* Таблица */}
      <div style={S.content}>
        {orders.length === 0 ? (
          <div style={S.emptyCard}>
            <div style={S.emptyHex}>䷿</div>
            <h3 style={S.emptyH3}>Покупок пока нет</h3>
            <p style={S.emptyText}>После оплаты диагностики здесь появится история ваших покупок и доступы к отчётам.</p>
            <button style={S.btnPrimary} onClick={() => router.push('/assessment')}>Начать диагностику →</button>
          </div>
        ) : (
          <div style={S.tableWrap}>
            <table style={S.table}>
              <thead>
                <tr>
                  {['ID', 'Гексаграмма', 'Метод', 'Сумма', 'Статус', 'Дата', ''].map(h => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orders.map((o, i) => {
                  const combo = o.assessment?.method1_combination || '—'
                  const hasMethod2 = o.assessment?.method2_data && Object.keys(o.assessment.method2_data).length > 0
                  const method = hasMethod2 ? '1+2' : '1'
                  const reportId = o.assessment?.reports?.[0]?.id
                  return (
                    <tr key={o.id} style={S.tr}>
                      <td style={{ ...S.td, fontFamily: 'monospace', fontSize: 12, color: 'rgba(26,37,64,0.5)' }}>
                        а-{String(100 + i).padStart(3, '0')}
                      </td>
                      <td style={S.td}>
                        <span style={{ fontFamily: 'monospace', fontSize: 13, letterSpacing: 2, color: '#1e3a8a', fontWeight: 700 }}>{combo}</span>
                      </td>
                      <td style={S.td}>
                        <span style={{ fontFamily: 'sans-serif', fontSize: 13 }}>{method}</span>
                      </td>
                      <td style={S.td}>
                        <span style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
                          {o.amount.toLocaleString('ru-RU')} {o.currency === 'RUB' ? '₽' : o.currency}
                        </span>
                      </td>
                      <td style={S.td}>
                        <span style={statusStyle(o.status)}>{statusLabel(o.status)}</span>
                      </td>
                      <td style={S.td}>
                        <span style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)' }}>
                          {new Date(o.created_at).toLocaleDateString('ru-RU')} {new Date(o.created_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </td>
                      <td style={{ ...S.td, display: 'flex', gap: 8 }}>
                        <button style={S.btnAction} onClick={() => router.push(`/report/${o.assessment_id}`)}>
                          Открыть
                        </button>
                        {reportId && (
                          <a href={`${API}/api/reports/${reportId}/download`} target="_blank" rel="noreferrer" style={S.btnActionGhost}>
                            ↓ PDF
                          </a>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  nav: { background: '#cde3e3', borderBottom: '1px solid rgba(26,37,64,0.08)' },
  navInner: { maxWidth: 1200, margin: '0 auto', padding: '0 60px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 },
  navLogo: { display: 'flex', alignItems: 'baseline', cursor: 'pointer', flexShrink: 0 },
  logo64: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#c0392b' },
  logoDao: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#1a2540' },
  navLinks: { display: 'flex', gap: 4, flex: 1, justifyContent: 'center' },
  navLink: { background: 'none', border: 'none', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', cursor: 'pointer', padding: '6px 12px', borderRadius: 5 },
  navLinkOn: { background: 'rgba(26,37,64,0.08)', color: '#1a2540' },
  navEmail: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.55)' },
  navLogout: { background: 'none', border: 'none', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', cursor: 'pointer', padding: 0 },
  avatar: { width: 32, height: 32, borderRadius: '50%', background: '#1a2540', color: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Georgia,serif', fontSize: 14, flexShrink: 0 },
  hero: { maxWidth: 1200, margin: '0 auto', padding: '48px 60px 24px' },
  heroH1: { fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', margin: '8px 0 6px' },
  heroSub: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', margin: 0 },
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 },
  content: { maxWidth: 1200, margin: '0 auto', padding: '0 60px 60px' },
  tableWrap: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 10, overflow: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 13 },
  th: { padding: '12px 16px', textAlign: 'left' as const, fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)', fontWeight: 600, borderBottom: '1px solid rgba(26,37,64,0.08)' },
  td: { padding: '14px 16px', borderBottom: '1px solid rgba(26,37,64,0.06)', verticalAlign: 'middle' as const },
  tr: {},
  pill: { fontFamily: 'sans-serif', fontSize: 11, padding: '3px 10px', borderRadius: 20, fontWeight: 500, display: 'inline-block' },
  btnAction: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 5, padding: '5px 12px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' },
  btnActionGhost: { background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 5, padding: '5px 12px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer', textDecoration: 'none', display: 'inline-block' },
  emptyCard: { background: 'rgba(255,255,255,0.65)', border: '1px dashed rgba(26,37,64,0.2)', borderRadius: 10, padding: '60px 40px', textAlign: 'center' as const },
  emptyHex: { fontSize: 52, color: '#1e3a8a', marginBottom: 18, display: 'block', fontFamily: 'serif' },
  emptyH3: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, marginBottom: 8, color: '#1a2540' },
  emptyText: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', maxWidth: 360, margin: '0 auto 22px', lineHeight: 1.6 },
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '11px 22px', fontFamily: 'sans-serif', fontSize: 14, fontWeight: 500, cursor: 'pointer' },
}

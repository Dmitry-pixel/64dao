'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, listAssessments, logout, type AuthUser, type Assessment } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function ReportsPage() {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getMe(), listAssessments()])
      .then(([u, a]) => { setUser(u); setAssessments(a) })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  async function handleLogout() {
    await logout()
    router.push('/login')
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка...</p>
    </div>
  )

  const completed = assessments.filter(a => a.status === 'completed' || a.status === 'paid')
  const drafts = assessments.filter(a => a.status === 'draft')

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
            <button style={{ ...S.navLink, ...S.navLinkOn }}>Мои отчёты</button>
            <button style={S.navLink} onClick={() => router.push('/purchases')}>Мои покупки</button>
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
        <div style={S.heroBetween}>
          <div>
            <h1 style={S.heroH1}>Здравствуйте, {user?.full_name?.split(' ')[0] || user?.email}</h1>
            <p style={S.heroSub}>
              У вас {completed.length} готов{completed.length === 1 ? 'ый отчёт' : 'ых отчёта'} и {drafts.length} черновик{drafts.length === 1 ? '' : 'а'}. Завершите диагностику или начните новую.
            </p>
          </div>
          <button style={S.btnPrimary} onClick={() => router.push('/assessment')}>+ Новая диагностика</button>
        </div>
      </div>

      {/* Сетка */}
      <div style={S.grid}>
        <div>
          <div style={S.listHeader}>
            <span style={S.labelRed}>Мои отчёты</span>
            <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}>{assessments.length} записей</span>
          </div>

          {assessments.length === 0 ? (
            <div style={S.emptyCard}>
              <div style={S.emptyHex}>䷿</div>
              <h3 style={S.emptyH3}>Пока нет диагностик</h3>
              <p style={S.emptyText}>Пройдите диагностику, чтобы получить персональную стратегию.</p>
              <button style={S.btnPrimary} onClick={() => router.push('/assessment')}>Начать диагностику →</button>
            </div>
          ) : (
            <div style={S.list}>
              {assessments.map((a, i) => (
                <div key={a.id}
                  style={{ ...S.card, cursor: (a.status === 'completed' || a.status === 'paid') ? 'pointer' : 'default' }}
                  onClick={() => (a.status === 'completed' || a.status === 'paid') && router.push(`/report/${a.id}`)}>
                  <div style={S.cardNum}>{String(i + 1).padStart(2, '0')}</div>
                  <div style={S.cardHex}>{a.method1_combination || '——'}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={S.cardMeta}>
                      {a.method1_combination} · {new Date(a.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}
                    </div>
                    <div style={S.cardTitle}>
                      {a.status === 'completed' || a.status === 'paid'
                        ? (a.method2_data !== null
                            ? `Бизнес-модель${a.method1_combination ? ' · ' + a.method1_combination : ''}`
                            : `Стратегический отчёт${a.method1_combination ? ' · ' + a.method1_combination : ''}`)
                        : 'Незавершённая диагностика'}
                    </div>
                    <div style={S.cardDetail}>
                      {a.reports.length > 0 ? `${a.reports.length} отчёт сформирован` : 'Отчёт формируется'}
                    </div>
                  </div>
                  <div style={S.cardActions}>
                    <span style={a.status === 'completed' || a.status === 'paid' ? S.pillDone : S.pillDraft}>
                      {a.status === 'completed' || a.status === 'paid' ? 'Готов' : 'Черновик'}
                    </span>
                    {a.reports.length > 0 ? (
                      <a href={`${API}/api/reports/${a.reports[0].id}/download`} target="_blank" rel="noreferrer"
                        style={S.btnGhost} onClick={e => e.stopPropagation()}>
                        Скачать PDF
                      </a>
                    ) : a.status === 'draft' ? (
                      <button style={S.btnSoft} onClick={e => { e.stopPropagation(); router.push('/assessment') }}>Продолжить →</button>
                    ) : (
                      <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)' }}>Генерация...</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Сайдбар */}
        <aside style={S.side}>
          <div style={S.sideCard}>
            <span style={{ ...S.labelRed, display: 'block', marginBottom: 10 }}>Статистика</span>
            <div style={S.statRow}><span style={S.statLabel}>Завершено</span><strong style={S.statVal}>{completed.length}</strong></div>
            <div style={S.statRow}><span style={S.statLabel}>В работе</span><strong style={S.statVal}>{drafts.length}</strong></div>
            <div style={{ ...S.statRow, marginBottom: 0 }}><span style={S.statLabel}>Всего</span><strong style={S.statVal}>{assessments.length}</strong></div>
          </div>
          <div style={S.sideCard}>
            <span style={{ ...S.labelRed, display: 'block', marginBottom: 10 }}>Поддержка</span>
            <p style={S.sideText}>Вопрос по отчёту? Напишите нам — ответим в течение рабочего дня.</p>
            <a href="mailto:admin@64dao.ru" style={S.btnGhost}>Написать в поддержку</a>
          </div>
        </aside>
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
  hero: { padding: '48px 60px 24px', maxWidth: 1200, margin: '0 auto' },
  heroBetween: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 8, gap: 24, flexWrap: 'wrap' as const },
  heroH1: { fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', margin: '0 0 6px' },
  heroSub: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', lineHeight: 1.6, margin: 0 },
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 },
  grid: { maxWidth: 1200, margin: '0 auto', padding: '0 60px 60px', display: 'grid', gridTemplateColumns: '1fr 320px', gap: 32 },
  listHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  list: { display: 'flex', flexDirection: 'column', gap: 14 },
  card: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '22px 26px', display: 'grid', gridTemplateColumns: '34px 90px 1fr auto', gap: 18, alignItems: 'center' },
  cardNum: { fontFamily: 'Georgia,serif', fontSize: 22, color: '#c0392b', textAlign: 'center' as const, lineHeight: '1' },
  cardHex: { fontFamily: 'monospace', fontSize: 13, color: '#1e3a8a', textAlign: 'center' as const, letterSpacing: 2, fontWeight: 700 },
  cardMeta: { fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', letterSpacing: 1, textTransform: 'uppercase' as const, marginBottom: 6 },
  cardTitle: { fontFamily: 'Georgia,serif', fontSize: 17, color: '#1a2540', marginBottom: 4, fontWeight: 400 },
  cardDetail: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.5 },
  cardActions: { display: 'flex', flexDirection: 'column' as const, alignItems: 'flex-end', gap: 8 },
  pillDone: { fontFamily: 'sans-serif', fontSize: 11, padding: '3px 10px', borderRadius: 20, background: '#dcfce7', color: '#166534', fontWeight: 500 },
  pillDraft: { fontFamily: 'sans-serif', fontSize: 11, padding: '3px 10px', borderRadius: 20, background: '#f1f5f9', color: '#475569', fontWeight: 500 },
  emptyCard: { background: 'rgba(255,255,255,0.65)', border: '1px dashed rgba(26,37,64,0.2)', borderRadius: 10, padding: '60px 40px', textAlign: 'center' as const },
  emptyHex: { fontSize: 52, color: '#1e3a8a', marginBottom: 18, display: 'block', fontFamily: 'serif' },
  emptyH3: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, marginBottom: 8, color: '#1a2540' },
  emptyText: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', maxWidth: 360, margin: '0 auto 22px', lineHeight: 1.6 },
  side: { display: 'flex', flexDirection: 'column' as const, gap: 18 },
  sideCard: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: 22 },
  sideText: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.6, margin: '0 0 12px' },
  statRow: { display: 'flex', justifyContent: 'space-between', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 8 },
  statLabel: { color: 'rgba(26,37,64,0.6)' },
  statVal: { color: '#1a2540', fontFamily: 'Georgia,serif', fontSize: 15 },
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '11px 22px', fontFamily: 'sans-serif', fontSize: 14, fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap' as const },
  btnGhost: { background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '7px 14px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer', textDecoration: 'none', display: 'inline-block' },
  btnSoft: { background: 'rgba(26,37,64,0.06)', color: '#1a2540', border: 'none', borderRadius: 6, padding: '7px 14px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' },
}

'use client'
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getMe, getCompanies, logout, type AuthUser, type Company } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

// Та же страница для пользователя и администратора. Разница только в обвязке:
// администратор видит свою верхнюю навигацию и левую колонку админки,
// пользователь — навигацию личного кабинета, как на «Моих покупках».
// Содержимое одно и то же: каждый видит только свои компании.

const METHOD_LABEL: Record<string, string> = {
  method1: 'Стратегическая диагностика',
  method2: 'Бизнес-модель',
  method3: 'Матрица силы · Метод 3',
}

const fmt = (iso: string) => new Date(iso).toLocaleDateString('ru-RU')

function plural(n: number, one: string, few: string, many: string): string {
  const m10 = n % 10, m100 = n % 100
  const word = m10 === 1 && m100 !== 11 ? one
    : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many
  return `${n} ${word}`
}

const reportHref = (method: string, id: string) =>
  method === 'method3' ? `/report/m3/${id}` : `/report/${id}`

export default function CompaniesPage() {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [companies, setCompanies] = useState<Company[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    getMe()
      .then(u => { setUser(u); return getCompanies() })
      .then(setCompanies)
      .catch(() => setError('Не удалось загрузить компании'))
      .finally(() => setLoading(false))
  }, [router])

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка…</p>
    </div>
  )

  const total = companies.reduce((n, c) => n + c.assessment_count, 0)
  const summary = companies.length === 0
    ? 'Здесь появятся компании, по которым вы прошли диагностику.'
    : `${plural(companies.length, 'компания', 'компании', 'компаний')} · ${plural(total, 'диагностика', 'диагностики', 'диагностик')}`

  const content = (
    <>
      {error && <div style={{ color: '#c0392b', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 16 }}>{error}</div>}
      {companies.length === 0 ? (
        <div style={S.emptyCard}>
          <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', margin: 0 }}>
            Пока нет компаний. Пройдите первую диагностику.
          </p>
        </div>
      ) : companies.map(c => <CompanyCard key={c.id ?? `m3-${c.name}`} c={c} />)}
      <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', margin: '20px 0 0', lineHeight: 1.6 }}>
        Диагностики сгруппированы по названию компании. «Динамика» открывается со второй
        диагностики Методов 1–2. Удалённые диагностики и черновики здесь не показываются.
      </p>
    </>
  )

  if (user?.role === 'admin') {
    return (
      <>
        <AdminNav current="companies" />
        <div className="admin-shell">
          <AdminSide current="companies" />
          <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>
            <div className="admin-page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
              <div>
                <span className="label-red">Диагностики</span>
                <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>Мои компании</h1>
                <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>{summary}</p>
              </div>
              <Link href="/assessment" className="btn btn-primary btn-lg">+ Новая диагностика</Link>
            </div>
            {content}
          </div>
        </div>
      </>
    )
  }

  return (
    <UserShell user={user} onLogout={async () => { await logout(); router.push('/login') }}>
      <div style={S.hero}>
        <span style={S.labelRed}>Личный кабинет</span>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <h1 style={S.heroH1}>Мои компании</h1>
            <p style={S.heroSub}>{summary}</p>
          </div>
          <button style={S.btnPrimary} onClick={() => router.push('/assessment')}>+ Новая диагностика</button>
        </div>
      </div>
      <div style={S.content}>{content}</div>
    </UserShell>
  )
}

function CompanyCard({ c }: { c: Company }) {
  const repeatDue = c.next_repeat_at ? new Date(c.next_repeat_at) : null
  const repeatReady = repeatDue !== null && repeatDue.getTime() <= Date.now()
  const period = c.first_at && c.latest_at && fmt(c.first_at) !== fmt(c.latest_at)
    ? `с ${fmt(c.first_at)} по ${fmt(c.latest_at)}`
    : c.latest_at ? fmt(c.latest_at) : ''

  return (
    <div style={S.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontFamily: 'Georgia,serif', fontSize: 19, color: '#1a2540' }}>{c.name}</div>
          <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.55)', marginTop: 3 }}>
            {plural(c.assessment_count, 'диагностика', 'диагностики', 'диагностик')}{period ? ` · ${period}` : ''}
          </div>
        </div>
        {c.id && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            {c.dynamics_available ? (
              <Link href={`/companies/${c.id}/dynamics`} style={S.btnDark}>Динамика →</Link>
            ) : (
              <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)' }}>
                Динамика откроется со 2-й диагностики
              </span>
            )}
            <Link href={`/assessment?method=1&company=${c.id}&company_name=${encodeURIComponent(c.name)}`} style={S.btnGhost}>
              Повторить
            </Link>
          </div>
        )}
      </div>

      {repeatDue && (
        <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: repeatReady ? '#c0392b' : 'rgba(26,37,64,0.55)', marginTop: 10 }}>
          {repeatReady ? 'Пора повторить диагностику' : `Повторную диагностику рекомендуем пройти после ${fmt(c.next_repeat_at!)}`}
          {c.followup_available ? ' · повтор входит в стоимость' : ''}
        </div>
      )}

      <ul style={{ listStyle: 'none', margin: '12px 0 0', padding: '10px 0 0', borderTop: '1px solid rgba(26,37,64,0.08)' }}>
        {c.assessments.map(a => (
          <li key={a.id} style={{ fontFamily: 'sans-serif', fontSize: 13, padding: '3px 0' }}>
            <Link href={reportHref(a.method, a.id)} style={{ color: '#1a2540', textDecoration: 'none' }}>
              {fmt(a.created_at)} · {METHOD_LABEL[a.method] ?? a.method}
            </Link>
            {a.is_followup && <span style={S.tag}>повтор</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}

function UserShell({ user, onLogout, children }: { user: AuthUser | null; onLogout: () => void; children: ReactNode }) {
  const router = useRouter()
  return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      <nav style={S.nav}>
        <div style={S.navInner}>
          <div style={S.navLogo} onClick={() => router.push('/dashboard')}>
            <span style={S.logo64}>64</span><span style={S.logoDao}> ДАО</span>
          </div>
          <div style={S.navLinks}>
            <button style={S.navLink} onClick={() => router.push('/dashboard')}>Личный кабинет</button>
            <button style={{ ...S.navLink, ...S.navLinkOn }}>Мои компании</button>
            <button style={S.navLink} onClick={() => router.push('/purchases')}>Мои покупки</button>
            <button style={S.navLink} onClick={() => router.push('/profile')}>Профиль</button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={S.navEmail}>{user?.email}</span>
            <div style={S.avatar}>{(user?.full_name || user?.email || 'U')[0].toUpperCase()}</div>
            <button style={S.navLogout} onClick={onLogout}>Выйти</button>
          </div>
        </div>
      </nav>
      {children}
    </div>
  )
}

// Стили повторяют «Мои покупки» и личный кабинет: одна система на все
// страницы пользователя.
const S: Record<string, CSSProperties> = {
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
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600 },
  content: { maxWidth: 1200, margin: '0 auto', padding: '0 60px 60px' },
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '11px 22px', fontFamily: 'sans-serif', fontSize: 14, fontWeight: 500, cursor: 'pointer' },
  card: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 10, padding: '18px 22px', marginBottom: 12 },
  emptyCard: { background: 'rgba(255,255,255,0.65)', border: '1px dashed rgba(26,37,64,0.2)', borderRadius: 10, padding: '40px', textAlign: 'center' },
  btnDark: { background: '#1a2540', color: '#fff', borderRadius: 6, padding: '8px 16px', fontFamily: 'sans-serif', fontSize: 13, textDecoration: 'none' },
  btnGhost: { border: '1px solid rgba(26,37,64,0.2)', color: '#1a2540', borderRadius: 6, padding: '8px 16px', fontFamily: 'sans-serif', fontSize: 13, textDecoration: 'none' },
  tag: { marginLeft: 8, fontSize: 11, color: 'rgba(26,37,64,0.55)', border: '1px solid rgba(26,37,64,0.15)', borderRadius: 4, padding: '1px 6px' },
}

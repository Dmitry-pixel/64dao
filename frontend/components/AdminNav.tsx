'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { logout } from '@/lib/api'
import { Logo } from '@/components/Logo'

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

export function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

interface AdminNavProps {
  current: string
}

export function AdminNav({ current }: AdminNavProps) {
  const router = useRouter()

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  return (
    <nav className="appnav">
      <Logo />
      <div className="appnav-links">
        <Link href="/admin" className={current === 'stats' ? 'on' : ''}>Сводка</Link>
        <Link href="/admin/users" className={current === 'users' ? 'on' : ''}>Пользователи</Link>
        <Link href="/admin/strategies" className={current === 'strategies' ? 'on' : ''}>Стратегии</Link>
        <Link href="/admin/reports" className={current === 'reports' ? 'on' : ''}>Отчёты</Link>
      </div>
      <div className="appnav-user">
        <span className="pill pill-pending" style={{ textTransform: 'uppercase', letterSpacing: 1 }}>admin</span>
        <div className="avatar" style={{ background: 'rgba(192,57,43,0.15)', color: 'var(--red)' }}>A</div>
        <button onClick={handleLogout} style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>
          Выйти
        </button>
      </div>
    </nav>
  )
}

interface AdminSideProps {
  current: string
  stats?: { users: number; strategies: number; reports: number }
}

export function AdminSide({ current, stats }: AdminSideProps) {
  return (
    <aside className="admin-side">
      <h4>Обзор</h4>
      <Link href="/admin" className={current === 'stats' ? 'on' : ''}>Сводка</Link>

      <h4>Контент</h4>
      <Link href="/admin/strategies" className={current === 'strategies' ? 'on' : ''}>
        64 стратегии <span className="num">{stats?.strategies ?? '—'} / 64</span>
      </Link>

      <h4>Пользователи</h4>
      <Link href="/admin/users" className={current === 'users' ? 'on' : ''}>
        Все пользователи <span className="num">{stats?.users ?? '—'}</span>
      </Link>

      <h4>Диагностики</h4>
      <Link href="/admin/reports" className={current === 'reports' ? 'on' : ''}>
        Отчёты <span className="num">{stats?.reports ?? '—'}</span>
      </Link>
    </aside>
  )
}

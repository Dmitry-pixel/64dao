'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { logout, adminApi } from '@/lib/api'
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
        <Link href="/admin/my-reports" className={current === 'my-reports' ? 'on' : ''}>Мои отчёты</Link>
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
}

export function AdminSide({ current }: AdminSideProps) {
  const [stats, setStats] = useState<{ users: number; strategies: number; reports: number } | null>(null)

  useEffect(() => {
    adminApi.stats()
      .then((data: any) => setStats({
        users: data.total_users,
        strategies: data.published_strategies,
        reports: data.total_reports,
      }))
      .catch(() => {})
  }, [])

  return (
    <aside className="admin-side">
      <Link href="/admin" style={{ display: 'block', marginBottom: 16, fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', textDecoration: 'none' }}>← Вернуться в кабинет</Link>
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
      <Link href="/dashboard" className={current === 'reports' ? 'on' : ''}>
        Мои отчёты <span className="num">{stats?.reports ?? '—'}</span>
      </Link>

      <h4>Система</h4>
      <Link href="/admin/pricing" className={current === 'pricing' ? 'on' : ''}>Тариф & цена</Link>
      <Link href="/admin/email-templates" className={current === 'email-templates' ? 'on' : ''}>Email-шаблоны</Link>
      <Link href="/admin/logs" className={current === 'logs' ? 'on' : ''}>Логи</Link>
    </aside>
  )
}

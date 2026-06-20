'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { getMe, adminApi, logout } from '@/lib/api'

interface Stats {
  total_users: number
  total_reports: number
  total_orders: number
  published_strategies: number
}

export function AdminNav({ current }: { current: string }) {
  const router = useRouter()
  async function handleLogout() {
    await logout()
    router.push('/login')
  }
  return (
    <nav style={{
      height: 65, background: '#1a2540', display: 'flex',
      alignItems: 'center', justifyContent: 'space-between',
      padding: '0 32px', position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
        <Link href="/admin" style={{ textDecoration: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, background: '#c0392b', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#fff', fontFamily: 'sans-serif', letterSpacing: 0.5 }}>64<br/>ДАО</div>
            <span style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: '#e8e4db', fontWeight: 400 }}>64 ДАО</span>
          </div>
        </Link>
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { key: 'stats', label: 'Сводка', href: '/admin' },
            { key: 'users', label: 'Пользователи', href: '/admin/users' },
            { key: 'strategies', label: 'Стратегии', href: '/admin/strategies' },
            { key: 'my-reports', label: 'Мои отчёты', href: '/admin/my-reports' },
          ].map(item => (
            <Link key={item.key} href={item.href} style={{ textDecoration: 'none' }}>
              <span style={{
                fontFamily: 'sans-serif', fontSize: 13, padding: '6px 14px', borderRadius: 6,
                color: current === item.key ? '#fff' : 'rgba(232,228,219,0.6)',
                background: current === item.key ? 'rgba(255,255,255,0.12)' : 'transparent',
                display: 'inline-block',
              }}>{item.label}</span>
            </Link>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(232,228,219,0.5)', letterSpacing: 1 }}>● ADMIN</span>
        <div style={{ width: 32, height: 32, background: '#c0392b', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontFamily: 'sans-serif', fontSize: 14, fontWeight: 600 }}>A</div>
        <button onClick={handleLogout} style={{ background: 'none', border: 'none', color: 'rgba(232,228,219,0.6)', fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif' }}>Выйти</button>
      </div>
    </nav>
  )
}

export function AdminSide({ current }: { current: string }) {
  const [stats, setStats] = useState<Stats | null>(null)
  useEffect(() => {
    adminApi.stats().then((s: any) => setStats(s)).catch(() => {})
  }, [])

  const isActive = (key: string) => current === key

  return (
    <aside style={{ background: '#e0dbd1', borderRight: '1px solid rgba(26,37,64,0.08)', padding: '24px 0', overflowY: 'auto' }}>
      <nav>
        <Group label="ОБЗОР" />
        <Item href="/admin" label="Сводка" active={isActive('stats')} />
        <Group label="КОНТЕНТ" />
        <Item href="/admin/strategies" label="64 стратегии" badge={stats ? `${stats.published_strategies} / 64` : undefined} active={isActive('strategies')} />
        <Group label="ПОЛЬЗОВАТЕЛИ" />
        <Item href="/admin/users" label="Все пользователи" badge={stats ? String(stats.total_users) : undefined} active={isActive('users')} />
        <Group label="ДИАГНОСТИКИ" />
        <Item href="/admin/my-reports" label="Отчёты" badge={stats ? String(stats.total_reports) : undefined} active={isActive('my-reports')} />
        <Item href="/admin" label="Количество заказов" badge={stats ? String(stats.total_orders) : undefined} active={false} />
        <Group label="СИСТЕМА" />
        <Item href="/admin/pricing" label="Тариф & цена" active={isActive('pricing')} />
        <Item href="/admin/email-templates" label="Email-шаблоны" active={isActive('email-templates')} />
        <Item href="/admin/logs" label="Логи" active={isActive('logs')} />
      </nav>
    </aside>
  )
}

function Group({ label }: { label: string }) {
  return (
    <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.35)', padding: '16px 20px 6px', fontWeight: 600 }}>
      {label}
    </div>
  )
}

function Item({ href, label, badge, active }: { href: string; label: string; badge?: string; active: boolean }) {
  return (
    <Link href={href} style={{ textDecoration: 'none' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '9px 20px', margin: '1px 8px', borderRadius: 7,
        background: active ? 'rgba(26,37,64,0.08)' : 'transparent',
      }}>
        <span style={{ fontFamily: 'sans-serif', fontSize: 14, color: active ? '#1a2540' : 'rgba(26,37,64,0.65)', fontWeight: active ? 600 : 400 }}>
          {label}
        </span>
        {badge !== undefined && (
          <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}>{badge}</span>
        )}
      </div>
    </Link>
  )
}

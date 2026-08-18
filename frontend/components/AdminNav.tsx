'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { logout, adminApi } from '@/lib/api'
import { Logo } from '@/components/Logo'
import { HEX_TUPLE } from '@/lib/hexagrams'

// [номер по Вэнь-вану, название] — единый источник истины для символа и имени
const HEX_INFO: Record<string, [number, string]> = HEX_TUPLE

// Символ через номер гексаграммы — оставлен для обратной совместимости
export function hexFor(combo: string): string {
  const info = HEX_INFO[combo]
  if (!info) return '䷀'
  return String.fromCodePoint(0x4DC0 + info[0] - 1)
}

export function hexNameFor(combo: string): string {
  if (!combo || combo.length !== 6) return '—'
  return HEX_INFO[combo]?.[1] ?? combo
}

// SVG-гексаграмма — рисует линии по комбинации AABBAA.
// A = сплошная линия (янь), B = прерывистая (инь).
// Индекс 0 = нижняя линия, 5 = верхняя (порядок И Цзин снизу вверх).
// Работает в любом браузере без шрифтов.
interface AdminNavProps {
  current: string
}

export function AdminNav({ current }: AdminNavProps) {
  const router = useRouter()

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const toggleSidebar = () => {
    document.body.classList.toggle('admin-sidebar-open')
  }

  return (
    <nav className="appnav">
      <Logo />
      <div className="appnav-links">
        <Link href="/admin" className={current === 'stats' ? 'on' : ''}>Сводка</Link>
        <Link href="/admin/users" className={current === 'users' ? 'on' : ''}>Пользователи</Link>
        <Link href="/admin/strategies" className={current === 'strategies' ? 'on' : ''}>Стратегии</Link>
        <Link href="/admin/my-reports" className={current === 'my-reports' ? 'on' : ''}>Мои отчёты</Link>
        <Link href="/companies" className={current === 'companies' ? 'on' : ''}>Мои компании</Link>
      </div>
      <button
        type="button"
        className="appnav-burger"
        aria-label="Открыть меню разделов"
        onClick={toggleSidebar}
        style={{ display: 'none', flexDirection: 'column', justifyContent: 'center', gap: 5, width: 32, height: 32, padding: 0, background: 'transparent', border: 'none', cursor: 'pointer' }}
      >
        <span style={{ display: 'block', width: '100%', height: 2, borderRadius: 1, background: 'var(--dark)' }} />
        <span style={{ display: 'block', width: '100%', height: 2, borderRadius: 1, background: 'var(--dark)' }} />
        <span style={{ display: 'block', width: '100%', height: 2, borderRadius: 1, background: 'var(--dark)' }} />
      </button>
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
  const [stats, setStats] = useState<{ users: number; strategies: number; total_orders: number } | null>(null)
  const [myReportsCount, setMyReportsCount] = useState<number | null>(null)

  useEffect(() => {
    adminApi.stats()
      .then((data: any) => setStats({
        users: data.total_users,
        strategies: data.published_strategies,
        total_orders: data.total_orders,
      }))
      .catch(() => {})

    import('@/lib/api').then(({ listAssessments }) =>
      listAssessments()
        .then(data => setMyReportsCount(data.length))
        .catch(() => {})
    )
  }, [])

  const closeSidebar = () => {
    document.body.classList.remove('admin-sidebar-open')
  }

  return (
    <aside className="admin-side">
      <button
        type="button"
        className="admin-side-close"
        onClick={closeSidebar}
        aria-label="Закрыть меню"
        style={{ display: 'none', marginBottom: 12, background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}
      >
        ✕ Закрыть
      </button>
      <Link href="/admin" onClick={closeSidebar} style={{ display: 'block', marginBottom: 16, fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', textDecoration: 'none' }}>← Вернуться в кабинет</Link>
      <h4>Обзор</h4>
      <Link href="/admin" className={current === 'stats' ? 'on' : ''}>Сводка</Link>

      <h4>Контент</h4>
      <Link href="/admin/strategies" className={current === 'strategies' ? 'on' : ''}>
        64 стратегии <span className="num">{stats?.strategies ?? '—'} / 64</span>
      </Link>
      <Link href="/admin/fin-content" className={current === 'fin-content' ? 'on' : ''}>Финансовая интерпретация</Link>
      <Link href="/admin/m3" className={current === 'm3' ? 'on' : ''}>Метод 3 · Матрица силы</Link>
      <Link href="/admin/contours" className={current === 'contours' ? 'on' : ''}>Контуры диагностики</Link>
      <Link href="/admin/lifecycle-stages" className={current === 'lifecycle-stages' ? 'on' : ''}>Стадии жизненного цикла</Link>
      <Link href="/admin/documents/about" className={current === 'doc-about' ? 'on' : ''}>О нас</Link>

      <h4>Пользователи</h4>
      <Link href="/admin/users" className={current === 'users' ? 'on' : ''}>
        Все пользователи <span className="num">{stats?.users ?? '—'}</span>
      </Link>
      <Link href="/admin/access-grants" className={current === 'access-grants' ? 'on' : ''}>
        Тестовый доступ
      </Link>

      <h4>Диагностики</h4>
      <Link href="/admin/my-reports" className={current === 'my-reports' ? 'on' : ''}>
        Мои отчёты <span className="num">{myReportsCount ?? '—'}</span>
      </Link>
      <Link href="/companies" className={current === 'companies' ? 'on' : ''}>
        Мои компании
      </Link>

      <h4>Документы</h4>
      <Link href="/admin/documents/user-agreement" className={current === 'doc-user-agreement' ? 'on' : ''}>Пользовательское соглашение</Link>
      <Link href="/admin/documents/privacy-policy" className={current === 'doc-privacy-policy' ? 'on' : ''}>Политика обработки ПД</Link>
      <Link href="/admin/documents/personal-data-consent" className={current === 'doc-personal-data-consent' ? 'on' : ''}>Согласие на обработку ПД</Link>
      <Link href="/admin/sample-report" className={current === 'sample-report' ? 'on' : ''}>Документы лендинга</Link>

      <h4>Система</h4>
      <Link href="/admin" className="">
        Количество заказов <span className="num">{stats?.total_orders ?? '—'}</span>
      </Link>
      <Link href="/admin/pricing" className={current === 'pricing' ? 'on' : ''}>Тариф & цена</Link>
      <Link href="/admin/payment-settings" className={current === 'payment-settings' ? 'on' : ''}>Настройка оплаты</Link>
      <Link href="/admin/orders" className={current === 'orders' ? 'on' : ''}>Заказы и возвраты</Link>
      <Link href="/admin/test-payment" className={current === 'test-payment' ? 'on' : ''}>Тест оплаты</Link>
      <Link href="/admin/email-templates" className={current === 'email-templates' ? 'on' : ''}>Email-шаблоны</Link>
      <Link href="/admin/reminders" className={current === 'reminders' ? 'on' : ''}>Рассылка</Link>
      <Link href="/admin/social-links" className={current === 'social-links' ? 'on' : ''}>Соц. сети</Link>
      <Link href="/admin/site-mode" className={current === 'site-mode' ? 'on' : ''}>Режим заглушки</Link>
      <Link href="/admin/logs" className={current === 'logs' ? 'on' : ''}>Логи</Link>
      <Link href="/404" className={current === '404' ? 'on' : ''}>Страница 404</Link>
      <Link href="/admin/sample-leads" className={current === 'sample-leads' ? 'on' : ''}>Сбор Адресов</Link>
    </aside>
  )
}

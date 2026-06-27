'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { logout, adminApi } from '@/lib/api'
import { Logo } from '@/components/Logo'

// [номер по Вэнь-вану, название] — единый источник истины для символа и имени
const HEX_INFO: Record<string, [number, string]> = {
  'AAAAAA':[1,'Действие'],'BBBBBB':[2,'Реакция'],'ABBBAB':[3,'Появление'],
  'BABBBA':[4,'Формализация'],'AAABAB':[5,'Бдительность'],'BABAAA':[6,'Раздор'],
  'BABBBB':[7,'Управление'],'BBBBAB':[8,'Объединение'],'AAABAA':[9,'Развитие'],
  'AABAAA':[10,'Последовательность'],'AAABBB':[11,'Достижение'],'BBBAAA':[12,'Препятствие'],
  'ABAAAA':[13,'Осознанность'],'AAAABA':[14,'Процветание'],'BBABBB':[15,'Смирение'],
  'BBBABB':[16,'Радость'],'ABBAAB':[17,'Соответствие'],'BAABBA':[18,'Диссонанс'],
  'AABBBB':[19,'Подход'],'BBBBAA':[20,'Наблюдать'],'ABBABA':[21,'Устранять'],
  'ABABBA':[22,'Изящество'],'BBBBBA':[23,'Разрушение'],'ABBBBB':[24,'Возрождение'],
  'ABBAAA':[25,'Естественность'],'AAABBA':[26,'Изобилие'],'ABBBBA':[27,'Умеренность'],
  'BAAAAB':[28,'Избыток'],'BABBAB':[29,'Решимость'],'ABAABA':[30,'Великолепие'],
  'BBAAAB':[31,'Влияние'],'BAAABB':[32,'Выносливость'],'BBAAAA':[33,'Благоразумие'],
  'AAAABB':[34,'Сила'],'BBBABA':[35,'Благоприятный'],'ABABBB':[36,'Неблагоприятный'],
  'ABABAA':[37,'Гармония'],'AABABA':[38,'Полярность'],'BBABAB':[39,'Трудность'],
  'BABABB':[40,'Избавление'],'AABBBA':[41,'Убыток'],'ABBBAA':[42,'Прибыль'],
  'AAAAAB':[43,'Прорыв'],'BAAAAA':[44,'Встреча'],'BBBAAB':[45,'Объединение'],
  'BAABBB':[46,'Самоотдача'],'BABAAB':[47,'Понимание'],'BAABAB':[48,'Глубина'],
  'ABAAAB':[49,'Реформа'],'BAAABA':[50,'Ценности'],'ABBABB':[51,'Смелость'],
  'BBABBA':[52,'Сосредоточенность'],'BBABAA':[53,'Готовность'],'AABABB':[54,'Амбиции'],
  'ABAABB':[55,'Изобилие'],'BBAABA':[56,'Стимулирование'],'BABBAA':[57,'Интуиция'],
  'AABAAB':[58,'Бодрость'],'BAABAA':[59,'Установление связей'],'AABBAB':[60,'Реализм'],
  'AABBAA':[61,'Внутренняя правда'],'BBAABB':[62,'Точность'],'ABABAB':[63,'Завершение'],
  'BABABA':[64,'Незавершённость'],
}

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
export function HexagramSVG({
  combo,
  size = 48,
  color = 'currentColor',
}: {
  combo: string
  size?: number
  color?: string
}) {
  if (!combo || combo.length !== 6) combo = 'AAAAAA'
  // lineH + gap должны давать totalH < size, иначе линии вылезают за viewBox
  // 6*lineH + 5*gap = totalH; при lineH=size*0.10, gap=size*0.06 → totalH=0.90*size ✓
  const lineH  = size * 0.10         // высота линии (янь)
  const gap    = size * 0.06         // промежуток между линиями
  const step   = lineH + gap
  const totalH = 6 * lineH + 5 * gap  // = 0.90 * size (всегда меньше size)
  const yOffset = (size - totalH) / 2
  const w  = size * 0.82
  const x0 = (size - w) / 2
  const brk = w * 0.22               // ширина разрыва в прерывистой линии (инь)

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      xmlns="http://www.w3.org/2000/svg"
      aria-label={hexNameFor(combo)}
    >
      {[...combo].map((ch, i) => {
        // i=0 → нижняя линия → рисуем снизу вверх
        const y = yOffset + (5 - i) * step
        if (ch === 'A') {
          return <rect key={i} x={x0} y={y} width={w} height={lineH} fill={color} rx={lineH / 4} />
        }
        return (
          <g key={i}>
            <rect x={x0}              y={y} width={(w - brk) / 2} height={lineH} fill={color} rx={lineH / 4} />
            <rect x={x0 + (w + brk) / 2} y={y} width={(w - brk) / 2} height={lineH} fill={color} rx={lineH / 4} />
          </g>
        )
      })}
    </svg>
  )
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

  return (
    <aside className="admin-side">
      <Link href="/admin" style={{ display: 'block', marginBottom: 16, fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', textDecoration: 'none' }}>← Вернуться в кабинет</Link>
      <h4>Обзор</h4>
      <Link href="/admin" className={current === 'stats' ? 'on' : ''}>Сводка</Link>

      <h4>Контент</h4>
      <Link href="/admin/strategies" className={current === 'strategies' ? 'on' : ''}>
        64 стратегии <span className="num">{stats?.strategies ?? '—'} / 64</span>
      </Link>
      <Link href="/admin/documents/about" className={current === 'doc-about' ? 'on' : ''}>О нас</Link>

      <h4>Пользователи</h4>
      <Link href="/admin/users" className={current === 'users' ? 'on' : ''}>
        Все пользователи <span className="num">{stats?.users ?? '—'}</span>
      </Link>

      <h4>Диагностики</h4>
      <Link href="/admin/my-reports" className={current === 'my-reports' ? 'on' : ''}>
        Мои отчёты <span className="num">{myReportsCount ?? '—'}</span>
      </Link>

      <h4>Документы</h4>
      <Link href="/admin/documents/user-agreement" className={current === 'doc-user-agreement' ? 'on' : ''}>Пользовательское соглашение</Link>
      <Link href="/admin/documents/privacy-policy" className={current === 'doc-privacy-policy' ? 'on' : ''}>Политика обработки ПД</Link>
      <Link href="/admin/documents/personal-data-consent" className={current === 'doc-personal-data-consent' ? 'on' : ''}>Согласие на обработку ПД</Link>
      <Link href="/admin/sample-report" className={current === 'sample-report' ? 'on' : ''}>Пример отчёта</Link>

      <h4>Система</h4>
      <Link href="/admin" className="">
        Количество заказов <span className="num">{stats?.total_orders ?? '—'}</span>
      </Link>
      <Link href="/admin/pricing" className={current === 'pricing' ? 'on' : ''}>Тариф & цена</Link>
      <Link href="/admin/email-templates" className={current === 'email-templates' ? 'on' : ''}>Email-шаблоны</Link>
      <Link href="/admin/social-links" className={current === 'social-links' ? 'on' : ''}>Соц. сети</Link>
      <Link href="/admin/logs" className={current === 'logs' ? 'on' : ''}>Логи</Link>
      <Link href="/404" className={current === '404' ? 'on' : ''}>Страница 404</Link>
    </aside>
  )
}

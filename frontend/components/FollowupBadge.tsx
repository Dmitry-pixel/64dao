'use client'

import { useRouter } from 'next/navigation'
import { isMethod2, type Assessment } from '@/lib/api'

/**
 * Бейдж повторной диагностики для карточки отчёта.
 *
 * Право на один бесплатный повтор живёт на первичной диагностике и приходит
 * с сервера полями followup_allowed / followup_used. Компонент общий для
 * кабинета и админки: разметка карточек там разная, но этот блок обязан
 * выглядеть и вести себя одинаково.
 */

const chip: React.CSSProperties = {
  fontFamily: 'sans-serif',
  fontSize: 9,
  letterSpacing: 1.5,
  textTransform: 'uppercase',
  fontWeight: 700,
  borderRadius: 4,
  padding: '3px 9px',
  whiteSpace: 'nowrap',
}

export function FollowupBadge({ a }: { a: Assessment }) {
  const router = useRouter()

  const done = a.status === 'completed' || a.status === 'paid'
  if (!done) return null

  // Повторная диагностика и «Динамика» работают только с Методом 1:
  // Метод 2 это оценка бизнес-модели по шкале, сравнивать там нечего.
  if (isMethod2(a)) return null

  if (a.is_followup) {
    return (
      <div style={{ marginTop: 8 }}>
        <span style={{
          ...chip,
          color: '#1e3a8a',
          background: 'rgba(30,58,138,0.08)',
          border: '1px solid rgba(30,58,138,0.2)',
        }}>
          Повторная диагностика
        </span>
      </div>
    )
  }

  if ((a.followup_allowed ?? 0) <= (a.followup_used ?? 0)) return null

  const start = (e: React.MouseEvent) => {
    // Карточка целиком кликабельна и ведёт в отчёт. Без остановки всплытия
    // нажатие на кнопку открывало бы отчёт вместо запуска диагностики.
    e.stopPropagation()
    const params = new URLSearchParams({ method: '1' })
    if (a.company_id) params.set('company', a.company_id)
    if (a.company_name) params.set('company_name', a.company_name)
    router.push(`/assessment?${params.toString()}`)
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      marginTop: 10, flexWrap: 'wrap',
    }}>
      <span style={{
        ...chip,
        color: '#c0392b',
        background: 'rgba(192,57,43,0.08)',
        border: '1px solid rgba(192,57,43,0.2)',
      }}>
        Доступна одна повторная диагностика
      </span>
      <button
        onClick={start}
        style={{
          fontFamily: 'sans-serif', fontSize: 12, color: '#fff',
          background: '#1a2540', border: 'none', borderRadius: 5,
          padding: '6px 14px', cursor: 'pointer', whiteSpace: 'nowrap',
        }}
      >
        Повторная диагностика →
      </button>
    </div>
  )
}

'use client'

import { useRouter } from 'next/navigation'
import type { Assessment } from '@/lib/api'

/**
 * Повторные диагностики внутри карточки первичной.
 *
 * Повтор это продолжение основного отчёта, а не самостоятельная строка
 * списка: в отрыве от первичной диагностики он бессмыслен. Разметка общая
 * для кабинета и админки.
 */

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

const linkBtn: React.CSSProperties = {
  fontFamily: 'sans-serif',
  fontSize: 13,
  color: 'var(--blue)',
  background: 'none',
  border: 'none',
  padding: 0,
  cursor: 'pointer',
  textDecoration: 'underline',
}

export function NestedFollowups({ items }: { items: Assessment[] }) {
  const router = useRouter()
  if (!items.length) return null

  return (
    <div
      onClick={e => e.stopPropagation()}
      style={{
        marginTop: 12,
        paddingTop: 12,
        borderTop: '1px solid rgba(26,37,64,0.08)',
      }}
    >
      <div style={{
        fontFamily: 'sans-serif',
        fontSize: 9,
        letterSpacing: 1.5,
        textTransform: 'uppercase',
        color: 'rgba(26,37,64,0.4)',
        fontWeight: 700,
        marginBottom: 8,
      }}>
        Повторная диагностика
      </div>

      {items.map(f => (
        <div key={f.id} style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          flexWrap: 'wrap',
          marginBottom: 6,
        }}>
          <span style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text)' }}>
            {new Date(f.created_at).toLocaleDateString('ru-RU', {
              day: 'numeric', month: 'long', year: 'numeric',
            })}
          </span>
          <button style={linkBtn} onClick={() => router.push(`/report/${f.id}`)}>
            Открыть отчёт
          </button>
          <a style={linkBtn} href={`${API}/api/assessments/${f.id}/pdf`}>
            Скачать PDF
          </a>
          {f.company_id && (
            <button style={linkBtn}
              onClick={() => router.push(`/companies/${f.company_id}/dynamics`)}>
              Динамика
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getMe, getCompanies, type Company } from '@/lib/api'

export default function CompaniesPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [companies, setCompanies] = useState<Company[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    getMe()
      .then(() => getCompanies())
      .then(setCompanies)
      .catch(() => setError('Не удалось загрузить компании'))
      .finally(() => setLoading(false))
  }, [router])

  if (loading) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</p>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: '32px 20px' }}>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <Link href="/dashboard" style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--red)', textDecoration: 'none' }}>← В кабинет</Link>
        <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '10px 0 6px' }}>Мои компании</h1>
        <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: '0 0 24px', lineHeight: 1.6 }}>
          Диагностики сгруппированы по компаниям. При двух и более диагностиках компании открывается раздел «Динамика».
        </p>

        {error && <div style={{ color: '#c0392b', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 16 }}>{error}</div>}

        {companies.length === 0 ? (
          <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>Пока нет компаний. Пройдите первую диагностику.</p>
        ) : companies.map(c => {
          const canDynamics = c.assessment_count >= 2
          return (
            <div key={c.id} style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, padding: '16px 20px', marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontFamily: 'Georgia,serif', fontSize: 18, color: 'var(--text)' }}>{c.name}</div>
                <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginTop: 2 }}>
                  {c.assessment_count} диагностик{c.latest_at ? ` · последняя ${new Date(c.latest_at).toLocaleDateString('ru-RU')}` : ''}
                </div>
              </div>
              {canDynamics ? (
                <Link href={`/companies/${c.id}/dynamics`}
                  style={{ background: 'var(--text)', color: '#fff', borderRadius: 6, padding: '8px 16px', fontFamily: 'sans-serif', fontSize: 13, textDecoration: 'none' }}>
                  Динамика →
                </Link>
              ) : (
                <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)' }} title="Нужно ≥2 диагностик">
                  Динамика откроется со 2-й диагностики
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

'use client'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Logo } from '@/components/Logo'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const DOC_TITLES: Record<string, string> = {
  'user-agreement':        'Пользовательское соглашение',
  'privacy-policy':        'Политика обработки персональных данных',
  'personal-data-consent': 'Согласие на обработку персональных данных',
}

interface DocData {
  title: string
  content: string
  published: boolean
  updated_at: string | null
}

export default function PublicDocumentPage() {
  const params = useParams()
  const slug = params.slug as string

  const [doc, setDoc] = useState<DocData | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/documents/${slug}`)
      .then(r => {
        if (!r.ok) { setNotFound(true); return null }
        return r.json()
      })
      .then(data => { if (data) setDoc(data) })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [slug])

  const fmtDate = (iso: string | null) => {
    if (!iso) return null
    return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg, #f5f3ef)' }}>
      {/* Шапка */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 40px', height: 60,
        background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(8px)',
        borderBottom: '1px solid rgba(26,37,64,0.07)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <Logo />
        <Link href="/" style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute, rgba(26,37,64,0.5))', textDecoration: 'none' }}>
          ← На главную
        </Link>
      </nav>

      <div style={{ maxWidth: 760, margin: '0 auto', padding: '56px 40px 80px' }}>
        {loading && (
          <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.4)' }}>Загрузка...</p>
        )}

        {!loading && notFound && (
          <div style={{ textAlign: 'center', paddingTop: 60 }}>
            <p style={{ fontFamily: 'Georgia,serif', fontSize: 22, color: 'var(--text, #1a2540)', marginBottom: 12 }}>
              {DOC_TITLES[slug] ?? 'Документ'}
            </p>
            <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.45)' }}>
              Документ пока не опубликован.
            </p>
          </div>
        )}

        {!loading && doc && (
          <>
            {/* Заголовок */}
            <div style={{ marginBottom: 40 }}>
              <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2.5, textTransform: 'uppercase', color: '#c0392b', fontWeight: 700, marginBottom: 14 }}>
                64 ДАО · Юридические документы
              </div>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 30, fontWeight: 400, color: '#1a2540', margin: '0 0 12px', lineHeight: 1.3 }}>
                {doc.title}
              </h1>
              {doc.updated_at && (
                <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)', margin: 0 }}>
                  Последнее обновление: {fmtDate(doc.updated_at)}
                </p>
              )}
            </div>

            {/* Контент */}
            <div
              style={{
                fontFamily: 'sans-serif',
                fontSize: 15,
                lineHeight: 1.9,
                color: 'rgba(26,37,64,0.85)',
              }}
              dangerouslySetInnerHTML={{ __html: doc.content }}
            />
          </>
        )}
      </div>
    </div>
  )
}

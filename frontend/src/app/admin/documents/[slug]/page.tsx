'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const DOC_TITLES: Record<string, string> = {
  'user-agreement':        'Пользовательское соглашение',
  'privacy-policy':        'Политика обработки персональных данных',
  'personal-data-consent': 'Согласие на обработку персональных данных',
  'about':                 'О нас',
}

const DOC_SIDEBAR_KEY: Record<string, string> = {
  'user-agreement':        'doc-user-agreement',
  'privacy-policy':        'doc-privacy-policy',
  'personal-data-consent': 'doc-personal-data-consent',
  'about':                 'doc-about',
}

interface DocData {
  slug: string
  title: string
  content: string
  published: boolean
  updated_at: string | null
}

export default function AdminDocumentPage() {
  const router = useRouter()
  const params = useParams()
  const slug = params.slug as string

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [doc, setDoc] = useState<DocData>({
    slug,
    title: DOC_TITLES[slug] ?? slug,
    content: '',
    published: false,
    updated_at: null,
  })

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }

        const res = await fetch(`${API}/api/admin/documents/${slug}`, { credentials: 'include' })
        if (res.ok) {
          const data = await res.json()
          setDoc(data)
        }
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [slug])

  const save = useCallback(async (publish?: boolean) => {
    setSaving(true)
    try {
      const payload = {
        ...doc,
        published: publish !== undefined ? publish : doc.published,
      }
      const res = await fetch(`${API}/api/admin/documents/${slug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        if (publish !== undefined) setDoc(prev => ({ ...prev, published: publish }))
        setSaved(true)
        setTimeout(() => setSaved(false), 2500)
      }
    } catch {
      alert('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }, [doc, slug])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка...
    </div>
  )

  const title = DOC_TITLES[slug] ?? slug
  const sideKey = DOC_SIDEBAR_KEY[slug] ?? ''
  const publicUrl = `/documents/${slug}`

  const fmtDate = (iso: string | null) => {
    if (!iso) return null
    return new Date(iso).toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <>
      <AdminNav current={sideKey} />
      <div className="admin-shell">
        <AdminSide current={sideKey} />
        <div className="admin-main">

          <div className="admin-header">
            <div>
              <span className="label-red">Документы</span>
              <h1>{title}</h1>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' as const }}>
              {/* Статус */}
              <span className={`pill ${doc.published ? 'pill-completed' : 'pill-pending'}`}
                style={{ fontSize: 12 }}>
                {doc.published ? '● Опубликован' : '○ Черновик'}
              </span>

              {doc.published && (
                <a href={publicUrl} target="_blank" rel="noreferrer"
                  style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', textDecoration: 'underline' }}>
                  Открыть публичную страницу ↗
                </a>
              )}

              <button
                onClick={() => save()}
                disabled={saving}
                className="btn btn-ghost"
                style={{ fontSize: 13, padding: '8px 18px' }}
              >
                {saving ? 'Сохранение...' : saved ? '✓ Сохранено' : 'Сохранить черновик'}
              </button>

              {doc.published ? (
                <button
                  onClick={() => save(false)}
                  disabled={saving}
                  className="btn btn-ghost"
                  style={{ fontSize: 13, padding: '8px 18px', color: '#c0392b', borderColor: 'rgba(192,57,43,0.3)' }}
                >
                  Снять с публикации
                </button>
              ) : (
                <button
                  onClick={() => save(true)}
                  disabled={saving}
                  className="btn btn-primary"
                  style={{ fontSize: 13, padding: '8px 20px' }}
                >
                  Опубликовать
                </button>
              )}
            </div>
          </div>

          <div style={{ padding: '0 24px 40px' }}>

            {/* Инфо */}
            {doc.updated_at && (
              <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', margin: '0 0 18px' }}>
                Последнее сохранение: {fmtDate(doc.updated_at)}
              </p>
            )}

            {/* Подсказка */}
            <div className="card" style={{ padding: '14px 20px', marginBottom: 18, background: 'rgba(26,37,64,0.03)' }}>
              <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', margin: 0, lineHeight: 1.7 }}>
                Поддерживается HTML-разметка. Например: <code style={{ background: 'rgba(26,37,64,0.07)', padding: '1px 5px', borderRadius: 3, fontSize: 11 }}>&lt;b&gt;жирный&lt;/b&gt;</code>,{' '}
                <code style={{ background: 'rgba(26,37,64,0.07)', padding: '1px 5px', borderRadius: 3, fontSize: 11 }}>&lt;p&gt;абзац&lt;/p&gt;</code>,{' '}
                <code style={{ background: 'rgba(26,37,64,0.07)', padding: '1px 5px', borderRadius: 3, fontSize: 11 }}>&lt;ul&gt;&lt;li&gt;...&lt;/li&gt;&lt;/ul&gt;</code>.{' '}
                Публичная страница отобразит текст как HTML.
              </p>
            </div>

            {/* Редактор */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <textarea
                value={doc.content}
                onChange={e => setDoc(prev => ({ ...prev, content: e.target.value }))}
                placeholder={`Введите текст документа «${title}»...\n\nПоддерживается HTML-разметка.`}
                style={{
                  width: '100%',
                  minHeight: 520,
                  padding: '20px 24px',
                  fontFamily: 'monospace',
                  fontSize: 13,
                  lineHeight: 1.8,
                  color: 'var(--text)',
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  resize: 'vertical',
                  boxSizing: 'border-box' as const,
                }}
              />
            </div>

            {/* Предпросмотр */}
            {doc.content && (
              <div style={{ marginTop: 32 }}>
                <span className="label-red" style={{ display: 'block', marginBottom: 14 }}>Предпросмотр</span>
                <div className="card" style={{ padding: '28px 32px' }}>
                  <h2 style={{ fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, color: 'var(--text)', marginTop: 0, marginBottom: 20 }}>
                    {title}
                  </h2>
                  <div
                    style={{ fontFamily: 'sans-serif', fontSize: 14, lineHeight: 1.85, color: 'rgba(26,37,64,0.82)' }}
                    dangerouslySetInnerHTML={{ __html: doc.content }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

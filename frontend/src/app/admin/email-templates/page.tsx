'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import type { EmailTemplate } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const TEMPLATE_META: Record<string, { label: string; vars: string[] }> = {
  otp: {
    label: 'Код входа (OTP)',
    vars: ['{code}', '{name}', '{name_part}'],
  },
  welcome: {
    label: 'Приветствие при регистрации',
    vars: ['{name}', '{name_part}'],
  },
  forgot_password: {
    label: 'Сброс пароля',
    vars: ['{name}', '{name_part}', '{reset_link}'],
  },
  account_deactivated: {
    label: 'Блокировка аккаунта',
    vars: ['{name}', '{name_part}'],
  },
  account_activated: {
    label: 'Восстановление доступа',
    vars: ['{name}', '{name_part}'],
  },
  repeat_diagnostic: {
    label: 'Пора повторить диагностику',
    vars: ['{name}', '{name_part}', '{company}', '{company_part}', '{days_since}', '{app_url}'],
  },
}

const VAR_HINTS: Record<string, string> = {
  '{company}':      'Название компании',
  '{company_part}': 'Оборот « компании «Х»» или пусто, если названия нет',
  '{days_since}':   'Сколько дней прошло с последней диагностики',
  '{app_url}':      'Адрес сайта, без слэша на конце',
  '{code}':       'OTP-код (6 цифр)',
  '{name}':       'Имя пользователя',
  '{name_part}':  'Имя с запятой: «, Иван» или пусто если нет имени',
  '{reset_link}': 'Ссылка для сброса пароля',
}

function PreviewPanel({ html }: { html: string }) {
  const full = `<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<style>body{font-family:Arial,sans-serif;color:#1a2540;max-width:520px;margin:20px auto;padding:24px;background:#f5f3ef;}p{line-height:1.7;margin:0 0 14px;}</style>
</head><body>${html}</body></html>`
  return (
    <iframe
      srcDoc={full}
      style={{ width: '100%', height: 260, border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, background: '#f5f3ef' }}
      sandbox="allow-same-origin"
    />
  )
}

export default function AdminEmailTemplatesPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [templates, setTemplates] = useState<Record<string, EmailTemplate>>({})
  const [activeKey, setActiveKey] = useState('otp')
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))

    adminApi.emailTemplates()
      .then(data => setTemplates(data as Record<string, EmailTemplate>))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const active = templates[activeKey]

  const update = (field: keyof EmailTemplate, value: string) => {
    setSaved(false)
    setTemplates(prev => ({
      ...prev,
      [activeKey]: { ...prev[activeKey], [field]: value },
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await adminApi.saveEmailTemplates(templates)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      alert('Не удалось сохранить. Попробуйте ещё раз.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка…
    </div>
  )

  const keys = Object.keys(TEMPLATE_META)

  return (
    <>
      <AdminNav current="email-templates" />
      <div className="admin-shell">
        <AdminSide current="email-templates" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <span className="label-red">Система</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>
                Email-шаблоны
              </h1>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>
                {keys.length} шаблона · редактируйте тему и HTML-текст писем
              </p>
            </div>
            <button
              className={`btn ${saved ? 'btn-ghost' : 'btn-primary'}`}
              style={{ padding: '9px 24px', fontSize: 13, opacity: saving ? 0.6 : 1 }}
              disabled={saving}
              onClick={handleSave}
            >
              {saving ? 'Сохраняем…' : saved ? '✓ Сохранено' : 'Сохранить'}
            </button>
          </div>

          <div className="admin-email-grid" style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 24, alignItems: 'start' }}>

            {/* Sidebar — template list */}
            <div style={{ border: '1px solid rgba(26,37,64,0.09)', borderRadius: 10, overflow: 'hidden', background: 'rgba(255,255,255,0.55)' }}>
              {keys.map(key => {
                const meta = TEMPLATE_META[key]
                const isActive = key === activeKey
                return (
                  <button
                    key={key}
                    onClick={() => { setActiveKey(key); setShowPreview(false) }}
                    style={{
                      display: 'block', width: '100%', textAlign: 'left',
                      padding: '14px 18px', border: 'none', cursor: 'pointer',
                      borderBottom: '1px solid rgba(26,37,64,0.06)',
                      background: isActive ? 'rgba(26,37,64,0.06)' : 'transparent',
                      fontFamily: 'sans-serif', fontSize: 13,
                      color: isActive ? 'var(--text)' : 'var(--text-mute)',
                      fontWeight: isActive ? 600 : 400,
                    }}
                  >
                    <div style={{ marginBottom: 2 }}>{meta.label}</div>
                    <div style={{ fontSize: 11, opacity: 0.55, fontFamily: 'monospace' }}>{key}</div>
                  </button>
                )
              })}
            </div>

            {/* Editor */}
            {active ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

                {/* Description */}
                {active.description && (
                  <div style={{
                    padding: '10px 16px', borderRadius: 8,
                    background: 'rgba(30,58,138,0.06)', border: '1px solid rgba(30,58,138,0.15)',
                    fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.7)', lineHeight: 1.6,
                  }}>
                    {active.description}
                  </div>
                )}

                {/* Subject */}
                <div>
                  <label style={{ display: 'block', fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#c0392b', marginBottom: 8 }}>
                    Тема письма
                  </label>
                  <input
                    type="text"
                    value={active.subject}
                    onChange={e => update('subject', e.target.value)}
                    style={{
                      width: '100%', padding: '10px 14px',
                      border: '1px solid rgba(26,37,64,0.18)', borderRadius: 8,
                      fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)',
                      background: 'rgba(255,255,255,0.8)', outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                </div>

                {/* Body */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <label style={{ fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#c0392b' }}>
                      Текст письма (HTML)
                    </label>
                    <button
                      onClick={() => setShowPreview(p => !p)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', textDecoration: 'underline' }}
                    >
                      {showPreview ? 'Скрыть превью' : 'Показать превью'}
                    </button>
                  </div>
                  <textarea
                    value={active.body_html}
                    onChange={e => update('body_html', e.target.value)}
                    rows={12}
                    style={{
                      width: '100%', padding: '12px 14px',
                      border: '1px solid rgba(26,37,64,0.18)', borderRadius: 8,
                      fontFamily: 'monospace', fontSize: 13, color: 'var(--text)',
                      background: 'rgba(255,255,255,0.8)', outline: 'none',
                      resize: 'vertical', boxSizing: 'border-box', lineHeight: 1.6,
                    }}
                  />
                </div>

                {/* Preview */}
                {showPreview && (
                  <div>
                    <div style={{ fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: 'rgba(26,37,64,0.4)', marginBottom: 8 }}>
                      Превью
                    </div>
                    <PreviewPanel html={active.body_html} />
                  </div>
                )}

                {/* Variables reference */}
                <div style={{ border: '1px solid rgba(26,37,64,0.09)', borderRadius: 8, padding: '16px 20px', background: 'rgba(255,255,255,0.4)' }}>
                  <div style={{ fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: 'rgba(26,37,64,0.4)', marginBottom: 12 }}>
                    Доступные переменные
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {(TEMPLATE_META[activeKey]?.vars ?? []).map(v => (
                      <div key={v} style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
                        <code style={{ fontFamily: 'monospace', fontSize: 13, color: '#1e3a8a', background: 'rgba(30,58,138,0.08)', padding: '2px 8px', borderRadius: 4, flexShrink: 0 }}>
                          {v}
                        </code>
                        <span style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)' }}>
                          {VAR_HINTS[v] ?? ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            ) : (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-mute)', fontFamily: 'sans-serif' }}>
                Выберите шаблон слева
              </div>
            )}
          </div>

        </div>
      </div>
    </>
  )
}

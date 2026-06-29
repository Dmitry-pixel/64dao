'use client'

import { useState } from 'react'

interface FormState {
  name:    string
  email:   string
  message: string
}

export default function ContactSection() {
  const [form, setForm]       = useState<FormState>({ name: '', email: '', message: '' })
  const [submitted, setSubmitted] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setSending(true)
    try {
      const res = await fetch('/api/contact/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) {
        throw new Error('request failed')
      }
      setSubmitted(true)
    } catch {
      setError('Не удалось отправить сообщение. Попробуйте ещё раз или напишите на support@64dao.ru.')
    } finally {
      setSending(false)
    }
  }

  return (
    <section
      id="contact"
      style={{
        borderBottom: '1px solid rgba(0,0,0,0.06)',
        background: 'color-mix(in oklab, var(--brand-teal) 12%, var(--background))',
      }}
    >
      <div
        className="contact-grid"
        style={{
          maxWidth: 1280,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 64,
          padding: '96px 40px',
        }}
      >
        {/* ── Левая колонка — информация ── */}
        <div>
          <div style={{ marginBottom: 24, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--accent)' }}>
            Контакты
          </div>
          <h2
            style={{
              margin: 0,
              fontFamily: "'Golos Text',sans-serif",
              fontSize: 'clamp(36px,5vw,60px)',
              lineHeight: 1.05,
              color: 'var(--foreground)',
            }}
          >
            Свяжитесь<br />с нами
          </h2>
          <p style={{ marginTop: 32, maxWidth: 420, fontSize: 16, color: 'var(--muted-foreground)' }}>
            Оставьте сообщение, если хотите обсудить внедрение 64 ДАО, стратегическую сессию или доступ для команды.
          </p>
          <dl
            style={{
              marginTop: 48,
              borderTop: '1px solid rgba(0,0,0,0.1)',
              paddingTop: 32,
              display: 'flex',
              flexDirection: 'column',
              gap: 24,
            }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'auto 1fr',
                alignItems: 'baseline',
                columnGap: 24,
                borderBottom: '1px solid rgba(0,0,0,0.1)',
                paddingBottom: 24,
              }}
            >
              <dt style={{ fontFamily: "'Golos Text',sans-serif", fontSize: 18, color: 'var(--foreground)' }}>
                64dao.ru
              </dt>
              <dd style={{ margin: 0, fontSize: 14, color: 'var(--muted-foreground)' }}>
                платформа стратегической диагностики
              </dd>
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'auto 1fr',
                alignItems: 'baseline',
                columnGap: 24,
              }}
            >
              <dt style={{ maxWidth: 96, fontFamily: "'Golos Text',sans-serif", fontSize: 18, color: 'var(--foreground)' }}>
                Ответ по форме
              </dt>
              <dd style={{ margin: 0, fontSize: 14, color: 'var(--muted-foreground)' }}>
                обратная связь для запросов и партнёров
              </dd>
            </div>
          </dl>
        </div>

        {/* ── Правая колонка — форма ── */}
        <div>
          {submitted ? (
            <div
              style={{
                borderRadius: 6,
                border: '1px solid var(--border)',
                background: 'var(--card)',
                padding: 32,
                textAlign: 'center',
                color: 'var(--foreground)',
                boxShadow: '0 30px 80px -40px rgba(20,30,60,0.25)',
              }}
            >
              Спасибо! Ваше сообщение отправлено.
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 20 }}>
              <label style={{ display: 'block' }}>
                <span
                  style={{
                    marginBottom: 8,
                    display: 'block',
                    fontSize: 14,
                    fontWeight: 500,
                    color: 'var(--foreground)',
                  }}
                >
                  Имя
                </span>
                <input
                  required
                  maxLength={100}
                  placeholder="Как к вам обращаться"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  style={{
                    width: '100%',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--card)',
                    padding: '12px 16px',
                    fontSize: 16,
                    color: 'var(--foreground)',
                    outline: 'none',
                    fontFamily: 'Inter,sans-serif',
                  }}
                />
              </label>

              <label style={{ display: 'block' }}>
                <span
                  style={{
                    marginBottom: 8,
                    display: 'block',
                    fontSize: 14,
                    fontWeight: 500,
                    color: 'var(--foreground)',
                  }}
                >
                  Email
                </span>
                <input
                  required
                  type="email"
                  maxLength={255}
                  placeholder="name@company.ru"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  style={{
                    width: '100%',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--card)',
                    padding: '12px 16px',
                    fontSize: 16,
                    color: 'var(--foreground)',
                    outline: 'none',
                    fontFamily: 'Inter,sans-serif',
                  }}
                />
              </label>

              <label style={{ display: 'block' }}>
                <span
                  style={{
                    marginBottom: 8,
                    display: 'block',
                    fontSize: 14,
                    fontWeight: 500,
                    color: 'var(--foreground)',
                  }}
                >
                  Сообщение
                </span>
                <textarea
                  required
                  maxLength={1000}
                  rows={5}
                  placeholder="Расскажите, какой вопрос хотите обсудить"
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  style={{
                    width: '100%',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--card)',
                    padding: '12px 16px',
                    fontSize: 16,
                    color: 'var(--foreground)',
                    outline: 'none',
                    resize: 'vertical',
                    fontFamily: 'Inter,sans-serif',
                  }}
                />
              </label>

              {error && (
                <div style={{ fontSize: 13, color: 'var(--accent)' }}>{error}</div>
              )}

              <button
                type="submit"
                disabled={sending}
                style={{
                  marginTop: 8,
                  display: 'inline-flex',
                  width: '100%',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 6,
                  background: 'var(--foreground)',
                  padding: '16px 32px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--background)',
                  border: 'none',
                  cursor: sending ? 'default' : 'pointer',
                  opacity: sending ? 0.6 : 1,
                }}
              >
                {sending ? 'Отправляем…' : 'Отправить'}
              </button>
            </form>
          )}
        </div>
      </div>

      <style jsx>{`
        @media (max-width: 880px) {
          .contact-grid {
            grid-template-columns: 1fr !important;
            gap: 40px !important;
            padding: 56px 24px !important;
          }
        }
        @media (max-width: 480px) {
          .contact-grid {
            padding: 40px 16px !important;
          }
        }
      `}</style>
    </section>
  )
}

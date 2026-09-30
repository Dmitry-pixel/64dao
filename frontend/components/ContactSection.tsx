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

  // Оформление варианта B: стили в src/app/landing-b.css (классы lb-contact*).
  // Компонент используется только на главной, внутри обёртки .lb.
  return (
    <section id="contact" className="lb-sec lb-sec--cream">
      <div className="lb-wrap lb-contact">
        {/* ── Левая колонка — информация ── */}
        <div>
          <span className="lb-eyebrow">Контакты</span>
          <h2 className="lb-h2">Свяжитесь с нами</h2>
          <p className="lb-lead">
            Оставьте сообщение, если хотите обсудить внедрение 64 ДАО, стратегическую сессию или доступ для команды.
          </p>
          <dl className="lb-contact__info">
            <div className="lb-contact__row">
              <dt>64dao.ru</dt>
              <dd>платформа стратегической диагностики</dd>
            </div>
            <div className="lb-contact__row">
              <dt>Ответ по форме</dt>
              <dd>обратная связь для запросов и партнёров</dd>
            </div>
          </dl>
        </div>

        {/* ── Правая колонка — форма ── */}
        <div className="lb-contact__card">
          {submitted ? (
            <div className="lb-contact__done" role="status">
              <span className="lb-contact__done-mark" aria-hidden="true">✓</span>
              Спасибо! Ваше сообщение отправлено.
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="lb-contact__form">
              <label className="lb-field">
                <span>Имя</span>
                <input
                  required
                  maxLength={100}
                  placeholder="Как к вам обращаться"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </label>

              <label className="lb-field">
                <span>Email</span>
                <input
                  required
                  type="email"
                  maxLength={255}
                  placeholder="name@company.ru"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </label>

              <label className="lb-field">
                <span>Сообщение</span>
                <textarea
                  required
                  maxLength={1000}
                  rows={5}
                  placeholder="Расскажите, какой вопрос хотите обсудить"
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                />
              </label>

              {error && <div className="lb-contact__error" role="alert">{error}</div>}

              <button type="submit" disabled={sending} className="lb-btn lb-btn--red lb-btn--block">
                {sending ? 'Отправляем…' : 'Отправить'}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  )
}

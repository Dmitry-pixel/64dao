'use client'
import { useState } from 'react'
import Link from 'next/link'
import { forgotPassword } from '@/lib/api'
import { AuthSide, SocialRow } from '@/components/Logo'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await forgotPassword(email)
      setSent(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка отправки')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-split">
      <AuthSide eyebrow="Восстановление доступа" title="Стратегическая диагностика бизнеса." />
      <div className="auth-form-wrap">
        <h2>Забыли пароль?</h2>

        {sent ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{
              background: 'rgba(26,37,64,0.06)', border: '1px solid rgba(26,37,64,0.15)',
              borderRadius: 8, padding: '18px 20px',
              fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)', lineHeight: 1.7,
            }}>
              Если адрес <strong>{email}</strong> зарегистрирован в системе, на него отправлена ссылка для сброса пароля. Проверьте почту.
            </div>
            <p className="auth-foot" style={{ marginTop: 0 }}>
              <Link href="/login">← Вернуться к входу</Link>
            </p>
          </div>
        ) : (
          <>
            <p className="auth-sub">Введите email — отправим ссылку для сброса пароля.</p>

            {error && (
              <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 6, padding: '10px 14px', marginBottom: 18, fontSize: 13, color: 'var(--red)', fontFamily: 'sans-serif' }}>
                {error}
              </div>
            )}

            <form onSubmit={submit} className="auth-form">
              <div className="field">
                <label>Email</label>
                <input
                  type="email"
                  required
                  placeholder="email@company.ru"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>
              <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={loading}>
                {loading ? 'Отправляем…' : 'Отправить ссылку →'}
              </button>
              <SocialRow />
              <p className="auth-foot">
                Вспомнили пароль?{' '}
                <Link href="/login">Войти</Link>
              </p>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

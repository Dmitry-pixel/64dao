'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { sendOTP } from '@/lib/api'
import { AuthSide, SocialRow } from '@/components/Logo'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await sendOTP(email)
      router.push(`/verify?email=${encodeURIComponent(email)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка отправки')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-split">
      <AuthSide eyebrow="Вход в систему" title="Стратегическая диагностика бизнеса." />
      <div className="auth-form-wrap">
        <h2>Войти</h2>
        <p className="auth-sub">Введите email — отправим 5-значный код для входа. Без пароля.</p>

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
            {loading ? 'Отправляем код…' : 'Получить код →'}
          </button>
          <SocialRow />
          <p className="auth-foot">
            <Link href="/forgot-password">Забыли пароль?</Link>
          </p>
          <p className="auth-foot">
            Нет аккаунта?{' '}
            <Link href="/register">Зарегистрироваться</Link>
          </p>
        </form>
      </div>
    </div>
  )
}

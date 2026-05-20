'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { resetPassword } from '@/lib/api'
import { AuthSide, SocialRow } from '@/components/Logo'

function ResetPasswordForm() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = searchParams.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) setError('Недействительная ссылка. Запросите сброс пароля повторно.')
  }, [token])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Пароль должен быть не менее 8 символов.')
      return
    }
    if (password !== confirm) {
      setError('Пароли не совпадают.')
      return
    }
    setLoading(true)
    try {
      await resetPassword(token, password)
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сброса пароля')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-split">
      <AuthSide eyebrow="Новый пароль" title="Стратегическая диагностика бизнеса." />
      <div className="auth-form-wrap">
        <h2>Сброс пароля</h2>

        {done ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{
              background: 'rgba(26,37,64,0.06)', border: '1px solid rgba(26,37,64,0.15)',
              borderRadius: 8, padding: '18px 20px',
              fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)', lineHeight: 1.7,
            }}>
              Пароль успешно изменён. Теперь вы можете войти.
            </div>
            <button
              className="btn btn-primary btn-block"
              onClick={() => router.push('/login')}
            >
              Войти →
            </button>
          </div>
        ) : (
          <>
            <p className="auth-sub">Придумайте новый пароль (не менее 8 символов).</p>

            {error && (
              <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 6, padding: '10px 14px', marginBottom: 18, fontSize: 13, color: 'var(--red)', fontFamily: 'sans-serif' }}>
                {error}
              </div>
            )}

            <form onSubmit={submit} className="auth-form">
              <div className="field">
                <label>Новый пароль</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Минимум 8 символов"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="new-password"
                  disabled={!token}
                />
              </div>
              <div className="field">
                <label>Повторите пароль</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="Повторите пароль"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  autoComplete="new-password"
                  disabled={!token}
                />
              </div>
              <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={loading || !token}>
                {loading ? 'Сохраняем…' : 'Сохранить пароль →'}
              </button>
              <SocialRow />
              <p className="auth-foot">
                <Link href="/login">← Вернуться к входу</Link>
              </p>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  )
}

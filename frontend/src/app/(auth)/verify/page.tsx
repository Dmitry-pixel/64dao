'use client'
import { useState, useRef, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { verifyOTP, resendOTP, ApiError } from '@/lib/api'
import { AuthSide } from '@/components/Logo'

function VerifyForm() {
  const router = useRouter()
  const params = useSearchParams()
  const email = params.get('email') ?? ''

  const [digits, setDigits] = useState(['', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [resending, setResending] = useState(false)
  const [resentAt, setResentAt] = useState<number | null>(null)
  const inputs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => { inputs.current[0]?.focus() }, [])

  const handleChange = (i: number, val: string) => {
    if (!/^\d*$/.test(val)) return
    const next = [...digits]
    next[i] = val.slice(-1)
    setDigits(next)
    if (val && i < 4) inputs.current[i + 1]?.focus()
    if (val && i === 4 && next.every(d => d)) doVerify(next.join(''))
  }

  const handleKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) inputs.current[i - 1]?.focus()
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 5)
    if (pasted.length === 5) { setDigits(pasted.split('')); doVerify(pasted) }
  }

  const doVerify = async (code: string) => {
    if (!email) { setError('Email не передан. Вернитесь на страницу входа.'); return }
    setError(''); setLoading(true)
    try {
      const { role } = await verifyOTP(email, code)
      router.push(role === 'admin' ? '/admin' : '/dashboard')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('Сессия истекла. Войдите заново.')
        setTimeout(() => router.push('/login'), 1500)
        return
      }
      setError(err instanceof ApiError ? err.message : 'Неверный код')
      setDigits(['', '', '', '', ''])
      inputs.current[0]?.focus()
    } finally { setLoading(false) }
  }

  const handleResend = async () => {
    setResending(true); setError('')
    try { await resendOTP(email); setResentAt(Date.now()) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'Ошибка отправки') }
    finally { setResending(false) }
  }

  const canResend = !resentAt || Date.now() - resentAt > 30_000

  return (
    <div className="auth-split">
      <AuthSide eyebrow="Шаг 2 / 2" title="Подтверждение входа." />
      <div className="auth-form-wrap">
        <h2>Введите код</h2>
        <p className="auth-sub">
          Отправили 5-значный код на{' '}
          <strong style={{ color: 'var(--dark)' }}>{email}</strong>.{' '}
          Код действителен 10 минут.
        </p>

        {error && (
          <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 6, padding: '10px 14px', marginBottom: 18, fontSize: 13, color: 'var(--red)', fontFamily: 'sans-serif', textAlign: 'center' }}>
            {error}
          </div>
        )}

        <div className="auth-form">
          <div className="otp-row" onPaste={handlePaste}>
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={el => { inputs.current[i] = el }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={e => handleChange(i, e.target.value)}
                onKeyDown={e => handleKeyDown(i, e)}
                disabled={loading}
              />
            ))}
          </div>

          <p className="field-hint">
            Не пришёл код?{' '}
            <button
              onClick={handleResend}
              disabled={resending || !canResend}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--blue)', fontSize: 11, fontFamily: 'sans-serif', textDecoration: 'underline', padding: 0 }}
            >
              {resending ? 'Отправляем…' : 'Отправить повторно'}
            </button>
            {resentAt && !canResend && <span style={{ color: 'var(--green)', marginLeft: 6 }}>✓ Отправлен</span>}
          </p>

          <div className="row" style={{ marginTop: 24, gap: 10 }}>
            <Link href="/login" className="btn btn-ghost">Назад</Link>
            <button
              className="btn btn-primary"
              style={{ flex: 1, justifyContent: 'center' }}
              disabled={loading || digits.some(d => !d)}
              onClick={() => doVerify(digits.join(''))}
            >
              {loading ? 'Проверяем…' : 'Войти →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>}>
      <VerifyForm />
    </Suspense>
  )
}

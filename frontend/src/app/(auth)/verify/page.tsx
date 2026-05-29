'use client'
import { useState, useRef, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { verifyOTP, resendOTP, ApiError } from '@/lib/api'
import { AuthSide } from '@/components/Logo'

const dark = '#1a2540'
const blue = '#1e3a8a'
const red  = '#c0392b'

function VerifyForm() {
  const router  = useRouter()
  const params  = useSearchParams()
  const email   = params.get('email') ?? ''

  const [digits,   setDigits]   = useState(['', '', '', '', ''])
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [resending, setResending] = useState(false)
  const [resentAt,  setResentAt]  = useState<number | null>(null)
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
    setError('')
    setLoading(true)
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
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setResending(true)
    setError('')
    try {
      await resendOTP(email)
      setResentAt(Date.now())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Ошибка отправки')
    } finally {
      setResending(false)
    }
  }

  const canResend = !resentAt || Date.now() - resentAt > 30_000

  return (
    <div className="auth-split">
      <AuthSide eyebrow="Подтверждение входа" title="Почти готово — введите код из письма." />
      <div className="auth-form-wrap">
        <h2>Введите код</h2>
        <p className="auth-sub">
          Мы отправили 5-значный код на{' '}
          <strong style={{ color: dark }}>{email}</strong>
        </p>

        {error && (
          <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 6, padding: '10px 14px', marginBottom: 18, fontSize: 13, color: red, fontFamily: 'sans-serif' }}>
            {error}
          </div>
        )}

        <div
          style={{ display: 'flex', gap: '10px', marginBottom: '26px' }}
          onPaste={handlePaste}
        >
          {digits.map((digit, i) => (
            <input
              key={i}
              ref={el => { inputs.current[i] = el }}
              type="text" inputMode="numeric" maxLength={1}
              value={digit}
              onChange={e => handleChange(i, e.target.value)}
              onKeyDown={e => handleKeyDown(i, e)}
              disabled={loading}
              style={{
                width: '52px', height: '60px', textAlign: 'center',
                fontSize: '24px', fontWeight: 600, color: dark,
                background: digit ? 'rgba(30,58,138,0.06)' : 'rgba(26,37,64,0.04)',
                border: `1px solid ${digit ? 'rgba(30,58,138,0.4)' : 'rgba(26,37,64,0.15)'}`,
                borderRadius: '8px', outline: 'none',
                transition: 'border-color 0.15s, background 0.15s',
              }}
            />
          ))}
        </div>

        <button
          disabled={loading || digits.some(d => !d)}
          onClick={() => doVerify(digits.join(''))}
          className="btn btn-primary btn-block btn-lg"
          style={{ opacity: (loading || digits.some(d => !d)) ? 0.6 : 1 }}
        >
          {loading ? 'Проверяем…' : 'Подтвердить'}
        </button>

        <div style={{ marginTop: '18px' }}>
          {resentAt && !canResend ? (
            <p style={{ fontSize: '12px', color: '#2a7a2a', margin: 0, fontFamily: 'sans-serif' }}>✓ Код отправлен повторно</p>
          ) : (
            <button
              onClick={handleResend} disabled={resending || !canResend}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: blue, opacity: resending ? 0.5 : 0.8, fontFamily: 'sans-serif', padding: 0 }}
            >
              {resending ? 'Отправляем…' : 'Отправить код ещё раз'}
            </button>
          )}
        </div>

        <p className="auth-foot">
          Не тот email?{' '}
          <Link href="/login">Вернуться</Link>
        </p>
      </div>
    </div>
  )
}

export default function VerifyPage() {
  return (
    <Suspense fallback={
      <div className="auth-split" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: dark, opacity: 0.5, fontFamily: 'sans-serif' }}>Загрузка…</p>
      </div>
    }>
      <VerifyForm />
    </Suspense>
  )
}

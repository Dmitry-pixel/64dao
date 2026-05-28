'use client'
import { useState, useRef, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { verifyOTP, resendOTP, ApiError } from '@/lib/api'

const dark = '#1a2540'
const blue = '#1e3a8a'
const red  = '#c0392b'
const card = { background: 'rgba(255,255,255,0.75)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: '10px', padding: '36px' }

function VerifyForm() {
  const router        = useRouter()
  const params        = useSearchParams()
  const email         = params.get('email') ?? ''

  const [digits,   setDigits]   = useState(['', '', '', '', ''])
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [resending, setResending] = useState(false)
  const [resentAt,  setResentAt]  = useState<number | null>(null)
  const inputs = useRef<(HTMLInputElement | null)[]>([])

  // Фокус на первый инпут при загрузке
  useEffect(() => { inputs.current[0]?.focus() }, [])

  const handleChange = (i: number, val: string) => {
    if (!/^\d*$/.test(val)) return
    const next = [...digits]
    next[i] = val.slice(-1)
    setDigits(next)
    if (val && i < 4) inputs.current[i + 1]?.focus()
    // Автосабмит при вводе последней цифры
    if (val && i === 4 && next.every(d => d)) {
      doVerify(next.join(''))
    }
  }

  const handleKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) {
      inputs.current[i - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 5)
    if (pasted.length === 5) {
      setDigits(pasted.split(''))
      doVerify(pasted)
    }
  }

  const doVerify = async (code: string) => {
    if (!email) { setError('Email не передан. Вернитесь на страницу входа.'); return }
    setError('')
    setLoading(true)
    try {
      // POST /api/auth/verify → FastAPI ставит куку auth-token и возвращает role
      const { role } = await verifyOTP(email, code)
      // Редирект: admin → /admin, user → /dashboard
      router.push(role === 'admin' ? '/admin' : '/dashboard')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Кука протухла или сессия истекла — редиректим на логин
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
    <div style={card}>
      <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: '26px', fontWeight: 400, color: dark, margin: '0 0 10px', textAlign: 'center' }}>
        Подтверждение входа
      </h1>
      <p style={{ fontSize: '13px', color: dark, opacity: 0.55, lineHeight: '1.6', margin: '0 0 26px', textAlign: 'center' }}>
        Мы отправили 5-значный код на<br />
        <strong style={{ color: dark, opacity: 0.85 }}>{email}</strong>
      </p>

      {error && (
        <div style={{ background: 'rgba(192,57,43,0.08)', border: `1px solid rgba(192,57,43,0.25)`, borderRadius: '6px', padding: '10px 14px', marginBottom: '18px', fontSize: '13px', color: red, textAlign: 'center' }}>
          {error}
        </div>
      )}

      {/* OTP inputs */}
      <div
        style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginBottom: '26px' }}
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

      {/* Submit button */}
      <button
        disabled={loading || digits.some(d => !d)}
        onClick={() => doVerify(digits.join(''))}
        style={{
          width: '100%', padding: '12px', background: blue, color: '#fff',
          border: 'none', borderRadius: '6px', fontSize: '14px', fontWeight: 500,
          cursor: (loading || digits.some(d => !d)) ? 'not-allowed' : 'pointer',
          opacity: (loading || digits.some(d => !d)) ? 0.6 : 1,
        }}
      >
        {loading ? 'Проверяем…' : 'Подтвердить'}
      </button>

      {/* Resend + back */}
      <div style={{ textAlign: 'center', marginTop: '18px' }}>
        {resentAt && !canResend ? (
          <p style={{ fontSize: '12px', color: '#2a7a2a', margin: 0 }}>✓ Код отправлен повторно</p>
        ) : (
          <button
            onClick={handleResend} disabled={resending || !canResend}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: blue, opacity: resending ? 0.5 : 0.8 }}
          >
            {resending ? 'Отправляем…' : 'Отправить код ещё раз'}
          </button>
        )}
      </div>

      <p style={{ textAlign: 'center', fontSize: '12px', color: dark, opacity: 0.4, margin: '14px 0 0' }}>
        Не тот email?{' '}
        <Link href="/login" style={{ color: blue, textDecoration: 'none' }}>Вернуться</Link>
      </p>
    </div>
  )
}

// Suspense boundary — обязательно для useSearchParams в Next.js 14
export default function VerifyPage() {
  return (
    <Suspense fallback={
      <div style={{ ...card, textAlign: 'center', color: '#1a2540', opacity: 0.5 } as React.CSSProperties}>
        Загрузка…
      </div>
    }>
      <VerifyForm />
    </Suspense>
  )
}

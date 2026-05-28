'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { sendOTP, ApiError } from '@/lib/api'

const dark = '#1a2540'
const blue = '#1e3a8a'
const red  = '#c0392b'

export default function LoginPage() {
  const router  = useRouter()
  const [email,   setEmail]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      // Отправляем ТОЛЬКО email. Бэкенд генерирует OTP и шлёт на почту.
      await sendOTP(email)
      router.push(`/verify?email=${encodeURIComponent(email)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      background: 'rgba(255,255,255,0.75)',
      border: '1px solid rgba(26,37,64,0.12)',
      borderRadius: '10px',
      padding: '36px',
    }}>
      <h1 style={{
        fontFamily: "'Cormorant Garamond', Georgia, serif",
        fontSize: '26px', fontWeight: 400, color: dark,
        margin: '0 0 6px', textAlign: 'center',
      }}>
        Войти в кабинет
      </h1>
      <p style={{ fontSize: '13px', color: dark, opacity: 0.5, textAlign: 'center', margin: '0 0 26px' }}>
        На ваш email придёт 5-значный код подтверждения
      </p>

      {error && (
        <div style={{
          background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)',
          borderRadius: '6px', padding: '10px 14px', marginBottom: '18px',
          fontSize: '13px', color: red,
        }}>
          {error}
        </div>
      )}

      <form onSubmit={submit}>
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '12px', color: dark, opacity: 0.55, marginBottom: '6px' }}>
            Email
          </label>
          <input
            type="email" required value={email} autoComplete="email"
            placeholder="email@company.ru"
            onChange={e => setEmail(e.target.value)}
            style={{
              width: '100%', padding: '10px 14px',
              background: 'rgba(26,37,64,0.04)', border: '1px solid rgba(26,37,64,0.15)',
              borderRadius: '6px', fontSize: '14px', color: dark, outline: 'none',
            }}
          />
        </div>

        <button
          type="submit" disabled={loading}
          style={{
            width: '100%', padding: '12px', background: blue, color: '#fff',
            border: 'none', borderRadius: '6px', fontSize: '14px', fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1,
            transition: 'opacity 0.15s',
          }}
        >
          {loading ? 'Отправляем код…' : 'Войти'}
        </button>
      </form>

      <p style={{ textAlign: 'center', fontSize: '13px', color: dark, opacity: 0.5, margin: '18px 0 0' }}>
        Нет аккаунта?{' '}
        <Link href="/register" style={{ color: blue, textDecoration: 'none', fontWeight: 500 }}>
          Зарегистрироваться
        </Link>
      </p>
    </div>
  )
}

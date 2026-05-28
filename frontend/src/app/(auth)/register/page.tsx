'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { register, ApiError } from '@/lib/api'

const dark = '#1a2540'
const blue = '#1e3a8a'
const red  = '#c0392b'
const cardStyle = { background: 'rgba(255,255,255,0.75)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: '10px', padding: '36px' } as React.CSSProperties
const inpStyle  = { width: '100%', padding: '10px 14px', background: 'rgba(26,37,64,0.04)', border: '1px solid rgba(26,37,64,0.15)', borderRadius: '6px', fontSize: '14px', color: dark, outline: 'none' } as React.CSSProperties
const lblStyle  = { display: 'block', fontSize: '12px', color: dark, opacity: 0.55, marginBottom: '6px' } as React.CSSProperties

export default function RegisterPage() {
  const router = useRouter()
  const [form, setForm] = useState({ full_name: '', company_name: '', email: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) { setError('Пароли не совпадают'); return }
    if (form.password.length < 8)       { setError('Пароль должен быть не менее 8 символов'); return }
    setLoading(true)
    try {
      await register({ email: form.email, password: form.password, full_name: form.full_name, company_name: form.company_name })
      router.push(`/verify?email=${encodeURIComponent(form.email)}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={cardStyle}>
      <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: '26px', fontWeight: 400, color: dark, margin: '0 0 6px', textAlign: 'center' }}>Создать аккаунт</h1>
      <p style={{ fontSize: '13px', color: dark, opacity: 0.5, textAlign: 'center', margin: '0 0 22px' }}>Начните стратегическую диагностику вашей компании</p>

      {error && <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: '6px', padding: '10px 14px', marginBottom: '16px', fontSize: '13px', color: red }}>{error}</div>}

      <form onSubmit={submit}>
        {([
          { label: 'Ваше имя',          name: 'full_name' as const,    type: 'text',     ph: 'Иван Иванов' },
          { label: 'Название компании',  name: 'company_name' as const, type: 'text',     ph: 'ООО «Пример»' },
          { label: 'Email',             name: 'email' as const,        type: 'email',    ph: 'email@company.ru' },
          { label: 'Пароль',            name: 'password' as const,     type: 'password', ph: 'Минимум 8 символов' },
          { label: 'Повторите пароль',  name: 'confirm' as const,      type: 'password', ph: 'Повторите пароль' },
        ] as const).map(f => (
          <div key={f.name} style={{ marginBottom: '14px' }}>
            <label style={lblStyle}>{f.label}</label>
            <input type={f.type} required value={form[f.name]} onChange={set(f.name)} placeholder={f.ph} style={inpStyle} />
          </div>
        ))}
        <button type="submit" disabled={loading} style={{ width: '100%', marginTop: '8px', padding: '12px', background: blue, color: '#fff', border: 'none', borderRadius: '6px', fontSize: '14px', fontWeight: 500, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}>
          {loading ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
        </button>
      </form>

      <p style={{ textAlign: 'center', fontSize: '13px', color: dark, opacity: 0.5, margin: '16px 0 0' }}>
        Уже есть аккаунт?{' '}<Link href="/login" style={{ color: blue, textDecoration: 'none', fontWeight: 500 }}>Войти</Link>
      </p>
    </div>
  )
}

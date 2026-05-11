'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { register } from '@/lib/api'
import { AuthSide, SocialRow } from '@/components/Logo'

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ full_name: '', company_name: '', email: '', password: '' })

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
      router.push(`/verify?email=${encodeURIComponent(form.email)}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-split">
      <AuthSide eyebrow="Создание аккаунта" title="Один отчёт — полная ясность." />
      <div className="auth-form-wrap">
        <h2>Регистрация</h2>
        <p className="auth-sub">После регистрации придёт код подтверждения на email.</p>

        {error && (
          <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 6, padding: '10px 14px', marginBottom: 18, fontSize: 13, color: 'var(--red)', fontFamily: 'sans-serif' }}>
            {error}
          </div>
        )}

        <form onSubmit={submit} className="auth-form">
          <div className="field">
            <label>Имя и фамилия</label>
            <input type="text" placeholder="Анна Петрова" required value={form.full_name} onChange={set('full_name')} />
          </div>
          <div className="field">
            <label>Компания</label>
            <input type="text" placeholder="ООО «Перспектива»" value={form.company_name} onChange={set('company_name')} />
          </div>
          <div className="field">
            <label>Email</label>
            <input type="email" placeholder="email@company.ru" required value={form.email} onChange={set('email')} autoComplete="email" />
          </div>
          <div className="field">
            <label>Пароль</label>
            <input type="password" placeholder="Не менее 8 символов" required minLength={8} value={form.password} onChange={set('password')} />
            <p className="field-hint">Используется при входе как альтернатива OTP. Не короче 8 символов.</p>
          </div>
          <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={loading}>
            {loading ? 'Создаём аккаунт…' : 'Создать аккаунт →'}
          </button>
          <SocialRow />
          <p className="auth-foot">
            Уже есть аккаунт?{' '}
            <Link href="/login">Войти</Link>
          </p>
          <p className="faint" style={{ marginTop: 14, lineHeight: 1.6 }}>
            Регистрируясь, вы соглашаетесь с{' '}
            <Link href="/legal" style={{ textDecoration: 'underline' }}>условиями использования</Link>
            {' '}и политикой конфиденциальности.
          </p>
        </form>
      </div>
    </div>
  )
}

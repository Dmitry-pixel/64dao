'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { register, ApiError } from '@/lib/api'
import { AuthSide } from '@/components/Logo'

export default function RegisterPage() {
  const router = useRouter()
  const [form, setForm] = useState({ full_name: '', company_name: '', email: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) { setError('Пароли не совпадают'); return }
    if (form.password.length < 8) { setError('Пароль должен быть не менее 8 символов'); return }
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
    <div className="auth-split">
      <AuthSide eyebrow="Регистрация" title="Начните стратегическую диагностику вашего бизнеса." />
      <div className="auth-form-wrap">
        <h2>Создать аккаунт</h2>
        <p className="auth-sub">Заполните форму — войдёте через код из письма.</p>

        {error && (
          <div style={{ background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.25)', borderRadius: 6, padding: '10px 14px', marginBottom: 18, fontSize: 13, color: 'var(--red)', fontFamily: 'sans-serif' }}>
            {error}
          </div>
        )}

        <form onSubmit={submit} className="auth-form">
          {([
            { label: 'Ваше имя',         name: 'full_name' as const,    type: 'text',     ph: 'Иван Иванов' },
            { label: 'Название компании', name: 'company_name' as const, type: 'text',     ph: 'ООО «Пример»' },
            { label: 'Email',            name: 'email' as const,        type: 'email',    ph: 'email@company.ru' },
            { label: 'Пароль',           name: 'password' as const,     type: 'password', ph: 'Минимум 8 символов' },
            { label: 'Повторите пароль', name: 'confirm' as const,      type: 'password', ph: 'Повторите пароль' },
          ] as const).map(f => (
            <div key={f.name} className="field">
              <label>{f.label}</label>
              <input type={f.type} required value={form[f.name]} onChange={set(f.name)} placeholder={f.ph} />
            </div>
          ))}
          <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
          </button>
          <p className="auth-foot">
            Уже есть аккаунт?{' '}
            <Link href="/login">Войти</Link>
          </p>
        </form>
      </div>
    </div>
  )
}

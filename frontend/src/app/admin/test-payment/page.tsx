'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function AdminTestPaymentPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [result, setResult] = useState<{ order_id: string; payment_link: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const createTestPayment = async () => {
    setCreating(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`${API}/api/payments/test-create`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Ошибка ${res.status}`)
      }
      setResult(await res.json())
    } catch (e: any) {
      setError(e.message || 'Ошибка создания тестового платежа')
    } finally {
      setCreating(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка...
    </div>
  )

  const S: Record<string, React.CSSProperties> = {
    sectionTitle: { fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: 'var(--text-mute)', fontWeight: 600, margin: '0 0 14px' },
  }

  return (
    <>
      <AdminNav current="test-payment" />
      <div className="admin-shell">
        <AdminSide current="test-payment" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ marginBottom: 28 }}>
            <span className="label-red">Система</span>
            <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--dark)', margin: '6px 0 0' }}>Тест оплаты</h1>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 560 }}>
            <div className="card" style={{ padding: '20px 24px' }}>
              <h3 style={S.sectionTitle}>Проверка платёжного шлюза</h3>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--dark)', lineHeight: 1.6, marginTop: 0 }}>
                Создаёт реальный платёж на <b>1 ₽</b> через Точку (не полную цену диагностики) — для проверки
                прохождения оплаты, чека и вебхука. Работает независимо от переключателя «Оплата включена».
                Заказ привязывается к служебной записи, не влияет на кредиты и отчёты.
              </p>
              <button
                onClick={createTestPayment}
                disabled={creating}
                style={{ background: 'var(--dark)', color: '#fff', border: 'none', borderRadius: 6, padding: '12px 24px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', fontWeight: 500, marginTop: 8 }}
              >
                {creating ? 'Создаём...' : 'Создать тестовый платёж на 1 ₽'}
              </button>

              {error && (
                <div style={{ marginTop: 16, background: '#fff5f5', border: '1px solid rgba(192,57,43,0.2)', borderRadius: 8, padding: '12px 14px', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b' }}>
                  {error}
                </div>
              )}

              {result && (
                <div style={{ marginTop: 16, background: '#f0fdf4', border: '1px solid rgba(22,101,52,0.2)', borderRadius: 8, padding: '14px 16px', fontFamily: 'sans-serif', fontSize: 13, color: 'var(--dark)' }}>
                  <div style={{ marginBottom: 8 }}>Заказ создан: <code>{result.order_id}</code></div>
                  <a href={result.payment_link} target="_blank" rel="noopener noreferrer" style={{ color: '#1e3a8a', fontWeight: 500 }}>
                    Перейти к оплате →
                  </a>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </>
  )
}

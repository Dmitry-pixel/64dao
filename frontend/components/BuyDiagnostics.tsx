'use client'
/**
 * Покупка диагностики из личного кабинета.
 *
 * Заказ — это покупка кредита на продукт, а не оплата конкретной пройденной
 * диагностики: пользователь платит заранее и потом проходит. Поэтому кнопка
 * живёт в кабинете, а не на экране готового отчёта.
 *
 * Балансы продуктов раздельные: кредит Методов 1 и 2 нельзя потратить на
 * Метод 3 — цены разные.
 */
import { useEffect, useState } from 'react'
import { getPricing, type PricingProduct } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || ''

type Product = 'm12' | 'm3'

const LABEL: Record<Product, string> = {
  m12: 'Метод 1 + Метод 2',
  m3: 'Метод 3 · Матрица силы',
}

interface CreditsResponse {
  products?: Record<Product, { credits: number }>
}

export default function BuyDiagnostics({ m3Enabled }: { m3Enabled: boolean }) {
  const [products, setProducts] = useState<Record<Product, PricingProduct> | null>(null)
  const [credits, setCredits] = useState<Record<Product, number>>({ m12: 0, m3: 0 })
  const [busy, setBusy] = useState<Product | null>(null)
  const [note, setNote] = useState<string | null>(null)

  useEffect(() => {
    getPricing().then(d => setProducts(d.products)).catch(() => setProducts(null))
    fetch(`${API}/api/payments/credits`, { credentials: 'include' })
      .then(r => (r.ok ? r.json() : {}))
      .then((d: CreditsResponse) => setCredits({
        m12: d.products?.m12?.credits ?? 0,
        m3: d.products?.m3?.credits ?? 0,
      }))
      .catch(() => {})
  }, [])

  async function buy(code: Product) {
    const item = products?.[code]
    setNote(null)
    // Оплата выключена — показываем текст заглушки этого продукта, а не
    // общий: флаги у продуктов раздельные и могут расходиться.
    if (item && !item.payment_enabled) {
      setNote(item.payment_note || 'Приём платежей временно отключён.')
      return
    }
    setBusy(code)
    try {
      const res = await fetch(`${API}/api/payments/create?product=${code}`, {
        method: 'POST',
        credentials: 'include',
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.payment_link) {
        window.location.href = data.payment_link
        return
      }
      setNote(data.detail || 'Не удалось создать платёж. Попробуйте позже.')
    } catch {
      setNote('Не удалось создать платёж. Проверьте соединение.')
    } finally {
      setBusy(null)
    }
  }

  if (!products) return null

  const visible: Product[] = m3Enabled ? ['m12', 'm3'] : ['m12']

  return (
    <div style={{
      background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(26,37,64,0.1)',
      borderRadius: 10, padding: '16px 18px', marginBottom: 16,
    }}>
      <span style={{
        fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2,
        textTransform: 'uppercase', color: '#c0392b', fontWeight: 700,
        display: 'block', marginBottom: 12,
      }}>Купить диагностику</span>

      {visible.map(code => {
        const item = products[code]
        if (!item) return null
        return (
          <div key={code} style={{ marginBottom: 14 }}>
            <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', marginBottom: 2 }}>
              {LABEL[code]}
            </div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 20, color: '#1a2540', marginBottom: 6 }}>
              {item.price.toLocaleString('ru-RU')} {item.currency}
            </div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.5)', marginBottom: 8 }}>
              Доступно: {credits[code]}
            </div>
            <button
              onClick={() => buy(code)}
              disabled={busy === code}
              style={{
                width: '100%', padding: '9px 14px', borderRadius: 6, cursor: 'pointer',
                fontFamily: 'sans-serif', fontSize: 13,
                background: item.payment_enabled ? '#1a2540' : 'rgba(26,37,64,0.08)',
                color: item.payment_enabled ? '#fff' : 'rgba(26,37,64,0.6)',
                border: item.payment_enabled ? 'none' : '1px solid rgba(26,37,64,0.15)',
              }}
            >
              {busy === code ? 'Создаём платёж…' : 'Купить →'}
            </button>
          </div>
        )
      })}

      {note && (
        <div style={{
          background: '#fff5f5', border: '1px solid rgba(192,57,43,0.2)', borderRadius: 8,
          padding: '10px 12px', fontFamily: 'sans-serif', fontSize: 12,
          color: 'rgba(26,37,64,0.7)', lineHeight: 1.5,
        }}>{note}</div>
      )}
    </div>
  )
}

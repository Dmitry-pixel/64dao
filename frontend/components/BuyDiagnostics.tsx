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
 *
 * Экран подтверждения перед оплатой (2026-09-13).
 *
 * Точка перешла на сертификат НУЦ Минцифры — проверено openssl s_client:
 * лист *.tochka.com выпущен Russian Trusted Sub CA, корень Russian Trusted
 * Root CA. Этого корня нет в хранилищах Chrome, Firefox и Safari, поэтому
 * страница оплаты у таких браузеров открывается экраном ошибки безопасности.
 * Сервер этого не видит: TLS падает до редиректа, failRedirectUrl не
 * срабатывает, заказ навсегда остаётся pending и выглядит как «клиент
 * передумал».
 *
 * Отсюда порядок: сначала предупреждение, потом создание платежа. Платёж
 * создаётся только после нажатия «Продолжить» — иначе каждая отмена оставляла
 * бы в базе висящий pending-заказ и портила воронку.
 *
 * Подсказка внизу карточки при этом сохранена: экран подтверждения — это
 * профилактика до перехода, а подсказка — путь восстановления для того, кто
 * уже упёрся в ошибку и вернулся кнопкой «назад».
 */
import Link from 'next/link'
import { useEffect, useState, type CSSProperties } from 'react'
import { getPricing, type PricingProduct } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || ''

type Product = 'm12' | 'm3'

const LABEL: Record<Product, string> = {
  m12: 'Метод 1 + Метод 2',
  m3: 'Метод 3 + Метод 4',
}

const CARD: CSSProperties = {
  background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(26,37,64,0.1)',
  borderRadius: 10, padding: '16px 18px', marginBottom: 16,
}

const KICKER: CSSProperties = {
  fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2,
  textTransform: 'uppercase', color: '#c0392b', fontWeight: 700,
  display: 'block', marginBottom: 12,
}

interface CreditsResponse {
  products?: Record<Product, { credits: number }>
}

export default function BuyDiagnostics({ m3Enabled }: { m3Enabled: boolean }) {
  const [products, setProducts] = useState<Record<Product, PricingProduct> | null>(null)
  const [credits, setCredits] = useState<Record<Product, number>>({ m12: 0, m3: 0 })
  const [busy, setBusy] = useState<Product | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<Product | null>(null)

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

  // Первый шаг: проверки и предупреждение. Заказ здесь не создаётся.
  function start(code: Product) {
    const item = products?.[code]
    setNote(null)
    // Оплата выключена — показываем текст заглушки этого продукта, а не
    // общий: флаги у продуктов раздельные и могут расходиться.
    if (item && !item.payment_enabled) {
      setNote(item.payment_note || 'Приём платежей временно отключён.')
      return
    }
    setConfirm(code)
  }

  // Второй шаг: только после явного подтверждения создаём платёж и уходим.
  async function pay(code: Product) {
    setNote(null)
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
      setConfirm(null)
      setNote(data.detail || 'Не удалось создать платёж. Попробуйте позже.')
    } catch {
      setConfirm(null)
      setNote('Не удалось создать платёж. Проверьте соединение.')
    } finally {
      setBusy(null)
    }
  }

  if (!products) return null

  if (confirm) {
    const item = products[confirm]
    return (
      <div style={CARD}>
        <span style={KICKER}>Перед оплатой</span>

        <div style={{
          fontFamily: 'Georgia,serif', fontSize: 17, lineHeight: 1.35,
          color: '#1a2540', marginBottom: 10,
        }}>
          Оплата откроется на сайте банка «Точка»
        </div>

        <div style={{
          fontFamily: 'sans-serif', fontSize: 12, lineHeight: 1.6,
          color: 'rgba(26,37,64,0.7)', marginBottom: 10,
        }}>
          Банк использует сертификат НУЦ Минцифры. Chrome, Firefox и Safari его не
          знают и могут показать предупреждение безопасности. Это не сбой оплаты —
          платёж исправен, браузер просто не знаком с российским удостоверяющим
          центром.
        </div>

        <div style={{
          background: 'rgba(26,37,64,0.04)', borderRadius: 8, padding: '10px 12px',
          fontFamily: 'sans-serif', fontSize: 12, lineHeight: 1.6,
          color: 'rgba(26,37,64,0.7)', marginBottom: 12,
        }}>
          Чтобы страница открылась сразу:
          <div style={{ marginTop: 6 }}>
            — откройте оплату в Яндекс.Браузере или Atom: они знают этот сертификат;
          </div>
          <div>
            — либо один раз установите сертификат с{' '}
            <a href="https://www.gosuslugi.ru/crt" target="_blank" rel="noreferrer"
               style={{ color: '#1a2540' }}>gosuslugi.ru/crt</a>.
          </div>
          <div style={{ marginTop: 6 }}>
            <Link href="/help/payment-certificate" style={{ color: 'rgba(26,37,64,0.6)' }}>
              Подробная инструкция →
            </Link>
          </div>
        </div>

        {item && (
          <div style={{
            fontFamily: 'sans-serif', fontSize: 12,
            color: 'rgba(26,37,64,0.55)', marginBottom: 10,
          }}>
            {LABEL[confirm]} · {item.price.toLocaleString('ru-RU')} {item.currency}
          </div>
        )}

        <button
          onClick={() => pay(confirm)}
          disabled={busy === confirm}
          style={{
            width: '100%', padding: '9px 14px', borderRadius: 6, cursor: 'pointer',
            fontFamily: 'sans-serif', fontSize: 13, background: '#1a2540',
            color: '#fff', border: 'none', marginBottom: 8,
          }}
        >
          {busy === confirm ? 'Создаём платёж…' : 'Продолжить к оплате →'}
        </button>

        <button
          onClick={() => { setConfirm(null); setNote(null) }}
          disabled={busy === confirm}
          style={{
            width: '100%', padding: '9px 14px', borderRadius: 6, cursor: 'pointer',
            fontFamily: 'sans-serif', fontSize: 13,
            background: 'transparent', color: 'rgba(26,37,64,0.6)',
            border: '1px solid rgba(26,37,64,0.15)',
          }}
        >
          Отмена
        </button>

        {note && (
          <div style={{
            background: '#fff5f5', border: '1px solid rgba(192,57,43,0.2)', borderRadius: 8,
            padding: '10px 12px', fontFamily: 'sans-serif', fontSize: 12,
            color: 'rgba(26,37,64,0.7)', lineHeight: 1.5, marginTop: 10,
          }}>{note}</div>
        )}
      </div>
    )
  }

  const visible: Product[] = m3Enabled ? ['m12', 'm3'] : ['m12']

  return (
    <div style={CARD}>
      <span style={KICKER}>Купить диагностику</span>

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
              onClick={() => start(code)}
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

      {/* Путь восстановления, а не предупреждение: клиент, у которого браузер
          заблокировал страницу оплаты Точки, возвращается сюда кнопкой «назад».
          Сервер эту ошибку не видит — TLS падает до редиректа, failRedirectUrl
          не срабатывает. Профилактика живёт на экране подтверждения выше.
          Подробности: DEPLOY.md, раздел 8a. */}
      <div style={{
        fontFamily: 'sans-serif', fontSize: 11, lineHeight: 1.5,
        color: 'rgba(26,37,64,0.45)', marginBottom: 10,
      }}>
        Не открывается страница оплаты?{' '}
        <Link href="/help/payment-certificate" style={{ color: 'rgba(26,37,64,0.6)' }}>
          Возможно, нужен сертификат Минцифры →
        </Link>
      </div>

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

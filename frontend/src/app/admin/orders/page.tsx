'use client'
/**
 * Заказы и возвраты.
 *
 * Эндпоинт возврата (POST /api/payments/{id}/refund) существовал с самого
 * начала, но интерфейса к нему не было: операцию выполняли из консоли
 * браузера. Для движения денег это недопустимо — ошибка в id возвращала
 * средства не тому клиенту, без подтверждения и без следа в UI.
 *
 * Подтверждение сделано двухшаговым прямо в строке, а не через confirm():
 * системный диалог показывает текст без суммы и email в привычном виде, и
 * промах по кнопке в нём стоит дороже, чем в остальной админке.
 */
import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe, type AdminOrder } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const PAGE_SIZE = 100

const STATUS_LABEL: Record<string, string> = {
  pending: 'Ожидает',
  paid: 'Оплачен',
  failed: 'Ошибка',
  refunded: 'Возврат',
}

const PRODUCT_LABEL: Record<string, string> = {
  m12: 'Методы 1 + 2',
  m3: 'Метод 3',
}

const FILTERS: { key: string; label: string }[] = [
  { key: '', label: 'Все' },
  { key: 'paid', label: 'Оплачены' },
  { key: 'pending', label: 'Ожидают' },
  { key: 'refunded', label: 'Возвращены' },
  { key: 'failed', label: 'Ошибки' },
]

function statusPill(status: string) {
  if (status === 'paid') return <span className="pill pill-completed">{STATUS_LABEL.paid}</span>
  if (status === 'pending') return <span className="pill pill-pending">{STATUS_LABEL.pending}</span>
  if (status === 'refunded') {
    return (
      <span className="pill" style={{ background: 'rgba(26,37,64,0.08)', color: 'rgba(26,37,64,0.65)' }}>
        {STATUS_LABEL.refunded}
      </span>
    )
  }
  return (
    <span className="pill" style={{ background: 'rgba(192,57,43,0.1)', color: 'var(--red)' }}>
      {STATUS_LABEL[status] ?? status}
    </span>
  )
}

export default function AdminOrdersPage() {
  const router = useRouter()

  const [orders, setOrders] = useState<AdminOrder[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [ready, setReady] = useState(false)

  const [status, setStatus] = useState('')
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)

  const [confirming, setConfirming] = useState<string | null>(null)
  const [refunding, setRefunding] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await adminApi.orders({ status, q: search, limit: PAGE_SIZE, offset })
      setOrders(data.items)
      setTotal(data.total)
    } catch (e: unknown) {
      setNotice({ kind: 'err', text: e instanceof Error ? e.message : 'Не удалось загрузить заказы' })
    } finally {
      setLoading(false)
    }
  }, [status, search, offset])

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        setReady(true)
      } catch {
        router.push('/login')
      }
    }
    init()
  }, [router])

  useEffect(() => {
    if (ready) load()
  }, [ready, load])

  async function handleRefund(order: AdminOrder) {
    setRefunding(order.id)
    setNotice(null)
    try {
      const res = await adminApi.refundOrder(order.id)
      setNotice({
        kind: 'ok',
        text: `Возврат ${order.amount.toLocaleString('ru-RU')} ${order.currency} для ${order.user_email} проведён. `
          + `Снято диагностик: ${res.revoked_assessments}, прав на повтор: ${res.revoked_followup_rights}.`,
      })
      setOrders(prev => prev.map(o =>
        o.id === order.id ? { ...o, status: 'refunded', can_refund: false } : o))
    } catch (e: unknown) {
      // Текст банка приходит в detail — без него «502» не объясняет причину.
      setNotice({ kind: 'err', text: e instanceof Error ? e.message : 'Возврат не прошёл' })
    } finally {
      setRefunding(null)
      setConfirming(null)
    }
  }

  if (!ready) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)',
      }}>Загрузка…</div>
    )
  }

  const shown = offset + orders.length

  return (
    <>
      <AdminNav current="orders" />
      <div className="admin-shell">
        <AdminSide current="orders" />
        <div className="admin-main">

          <div className="admin-header">
            <div>
              <span className="label-red">Оплата</span>
              <h1>Заказы и возвраты</h1>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <input
                placeholder="Email покупателя или id операции…"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') { setOffset(0); setSearch(query) }
                }}
                style={{
                  padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 5,
                  fontFamily: 'sans-serif', fontSize: 13, minWidth: 280,
                  background: 'var(--card)', outline: 'none',
                }}
              />
              <button
                className="btn btn-ghost"
                style={{ padding: '7px 14px', fontSize: 12 }}
                onClick={() => { setOffset(0); setSearch(query) }}
              >
                Найти
              </button>
            </div>
          </div>

          <div className="row" style={{ gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
            {FILTERS.map(f => (
              <button
                key={f.key || 'all'}
                onClick={() => { setOffset(0); setStatus(f.key) }}
                className="btn btn-ghost"
                style={{
                  padding: '5px 12px', fontSize: 12,
                  background: status === f.key ? '#1a2540' : undefined,
                  color: status === f.key ? '#fff' : undefined,
                  borderColor: status === f.key ? '#1a2540' : undefined,
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {notice && (
            <div style={{
              borderRadius: 8, padding: '10px 14px', marginBottom: 16,
              fontFamily: 'sans-serif', fontSize: 13, lineHeight: 1.5,
              background: notice.kind === 'ok' ? 'rgba(26,37,64,0.05)' : '#fff5f5',
              border: notice.kind === 'ok'
                ? '1px solid rgba(26,37,64,0.15)'
                : '1px solid rgba(192,57,43,0.25)',
              color: notice.kind === 'ok' ? '#1a2540' : 'var(--red)',
            }}>
              {notice.text}
            </div>
          )}

          <table className="tbl">
            <thead>
              <tr>
                <th>Создан</th>
                <th>Покупатель</th>
                <th>Продукт</th>
                <th>Сумма</th>
                <th>Статус</th>
                <th>Операция в Точке</th>
                <th>Возврат</th>
              </tr>
            </thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.id}>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13, whiteSpace: 'nowrap' }}>
                    {new Date(o.created_at).toLocaleString('ru', {
                      day: '2-digit', month: '2-digit', year: '2-digit',
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13 }}>{o.user_email}</td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
                    {PRODUCT_LABEL[o.product] ?? o.product}
                  </td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13, whiteSpace: 'nowrap' }}>
                    {o.amount.toLocaleString('ru-RU')} {o.currency}
                  </td>
                  <td>{statusPill(o.status)}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'rgba(26,37,64,0.55)' }}>
                    {o.tochka_operation_id ?? '—'}
                  </td>
                  <td>
                    {!o.can_refund && (
                      <span className="faint" style={{ fontSize: 12 }}>
                        {o.status === 'refunded' ? 'уже возвращён' : '—'}
                      </span>
                    )}

                    {o.can_refund && confirming !== o.id && (
                      <button
                        onClick={() => { setNotice(null); setConfirming(o.id) }}
                        className="btn btn-ghost"
                        style={{ padding: '5px 12px', fontSize: 12, color: 'var(--red)' }}
                      >
                        Вернуть
                      </button>
                    )}

                    {o.can_refund && confirming === o.id && (
                      <div style={{ fontFamily: 'sans-serif', fontSize: 12, lineHeight: 1.5 }}>
                        <div style={{ marginBottom: 6, color: 'var(--red)' }}>
                          Вернуть {o.amount.toLocaleString('ru-RU')} {o.currency} на карту
                          покупателя {o.user_email}? Доступ к купленным диагностикам будет снят.
                        </div>
                        <button
                          onClick={() => handleRefund(o)}
                          disabled={refunding === o.id}
                          className="btn"
                          style={{
                            padding: '5px 12px', fontSize: 12, marginRight: 6,
                            background: 'var(--red)', color: '#fff', border: 'none',
                            opacity: refunding === o.id ? 0.5 : 1,
                          }}
                        >
                          {refunding === o.id ? 'Возвращаем…' : 'Да, вернуть'}
                        </button>
                        <button
                          onClick={() => setConfirming(null)}
                          disabled={refunding === o.id}
                          className="btn btn-ghost"
                          style={{ padding: '5px 12px', fontSize: 12 }}
                        >
                          Отмена
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}

              {!loading && orders.length === 0 && (
                <tr>
                  <td colSpan={7} className="faint" style={{ padding: '18px 0' }}>
                    Заказов по заданным условиям нет.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="row" style={{ justifyContent: 'space-between', marginTop: 18, gap: 12 }}>
            <span className="faint">
              {loading ? 'Загрузка…' : `Показано ${shown} из ${total}`}
            </span>
            <span className="row" style={{ gap: 6 }}>
              <button
                className="btn btn-ghost"
                style={{ padding: '5px 12px', fontSize: 12 }}
                disabled={offset === 0 || loading}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                ← назад
              </button>
              <button
                className="btn btn-ghost"
                style={{ padding: '5px 12px', fontSize: 12 }}
                disabled={shown >= total || loading}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                вперёд →
              </button>
            </span>
          </div>

        </div>
      </div>
    </>
  )
}

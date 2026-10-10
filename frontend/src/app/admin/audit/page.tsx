'use client'
/**
 * Журнал: действия администратора и история статусов заказов.
 *
 * Пишут его backend-middleware (каждый изменяющий запрос админа или во
 * время имперсонации) и слушатель смены статуса заказа — см. app/audit.py.
 * Страница читает журнал и умеет удалить действия админа старше 30 дней
 * (срок задан на сервере). История статусов заказов не удаляется, сама
 * очистка записывается в журнал с числом удалённых строк.
 */
import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe, type AuditEventItem } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const PAGE_SIZE = 100

const FILTERS: { key: '' | 'admin' | 'order'; label: string }[] = [
  { key: '', label: 'Все' },
  { key: 'admin', label: 'Действия админа' },
  { key: 'order', label: 'Статусы заказов' },
]

// Человеческие названия частых действий. Остальные показываются как есть.
const ACTION_LABEL: Record<string, string> = {
  'PUT /api/admin/pricing': 'Изменение цены и оплаты',
  'PUT /api/admin/tochka-settings': 'Изменение настроек Точки',
  'PUT /api/admin/site-mode': 'Режим заглушки',
  'PATCH /api/admin/users/{user_id}/role': 'Смена роли пользователя',
  'PATCH /api/admin/users/{user_id}/status': 'Блокировка / разблокировка',
  'POST /api/admin/users/{user_id}/revoke-sessions': 'Завершение сессий пользователя',
  'DELETE /api/admin/users/{user_id}': 'Удаление пользователя',
  'POST /api/admin/impersonate/{user_id}': 'Вход от лица пользователя',
  'POST /api/admin/impersonate/stop': 'Выход из режима «от лица»',
  'POST /api/admin/users/{user_id}/access-grants': 'Выдача тестового доступа',
  'POST /api/admin/access-grants/{grant_id}/revoke': 'Отзыв тестового доступа',
  'POST /api/payments/{order_id}/refund': 'Возврат денег',
  'POST /api/payments/test-create': 'Тестовый платёж 1 ₽',
  'POST /api/payments/admin/reconcile': 'Сверка заказов с банком',
  'PUT /api/payments/admin/credits-settings': 'Обязательная оплата вкл/выкл',
  'PUT /api/payments/admin/tax-settings': 'Настройка НДС',
  'PUT /api/admin/email-templates': 'Изменение шаблонов писем',
  'PUT /api/admin/reminders-settings': 'Настройки рассылки',
  'DELETE /api/admin/audit': 'Очистка журнала',
  'DELETE /api/sample-report/leads': 'Очистка заявок «Сбор адресов»',
}

const SOURCE_LABEL: Record<string, string> = {
  created: 'создан',
  webhook: 'вебхук банка',
  status_poll: 'проверка статуса клиентом',
  reconcile_job: 'ежечасная сверка',
  admin_reconcile: 'сверка из админки',
  admin_refund: 'возврат из админки',
}

const ORDER_STATUS: Record<string, string> = {
  pending: 'Ожидает', paid: 'Оплачен', failed: 'Ошибка', refunded: 'Возврат',
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

function details(e: AuditEventItem): string {
  if (e.kind === 'order') {
    const from = e.before?.status ? `${ORDER_STATUS[String(e.before.status)] ?? e.before.status} → ` : ''
    const to = ORDER_STATUS[String(e.after?.status)] ?? String(e.after?.status ?? '')
    const src = e.note ? ` (${SOURCE_LABEL[e.note] ?? e.note})` : ''
    return `${from}${to}${src}`
  }
  const parts: string[] = []
  const result = e.after?.result as { deleted?: number } | undefined
  if (result && typeof result.deleted === 'number') parts.push(`удалено записей: ${result.deleted}`)
  if (e.after?.query) parts.push(JSON.stringify(e.after.query))
  if (e.after?.body) parts.push(JSON.stringify(e.after.body))
  return parts.join(' ').slice(0, 300)
}

export default function AdminAuditPage() {
  const router = useRouter()
  const [items, setItems] = useState<AuditEventItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [ready, setReady] = useState(false)
  const [kind, setKind] = useState<'' | 'admin' | 'order'>('')
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState('')
  const [purging, setPurging] = useState(false)
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await adminApi.audit({ kind, limit: PAGE_SIZE, offset })
      setItems(data.items)
      setTotal(data.total)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Не удалось загрузить журнал')
    } finally {
      setLoading(false)
    }
  }, [kind, offset])

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

  async function handlePurge() {
    setNotice('')
    setError('')
    try {
      const { count, retention_days } = await adminApi.auditPurgePreview()
      if (count === 0) {
        setNotice(`Записей старше ${retention_days} дней нет. Удалять нечего.`)
        return
      }
      if (!confirm(`Удалить ${count} записей о действиях администратора старше ${retention_days} дней?\n\nИстория статусов заказов останется. Сама очистка будет записана в журнал.`)) return
      setPurging(true)
      const res = await adminApi.auditPurge()
      setNotice(`Удалено записей: ${res.deleted}`)
      setOffset(0)
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Не удалось очистить журнал')
    } finally {
      setPurging(false)
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

  const shown = offset + items.length

  return (
    <>
      <AdminNav current="audit" />
      <div className="admin-shell">
        <AdminSide current="audit" />
        <div className="admin-main">

          <div className="admin-header">
            <div>
              <span className="label-red">Контроль</span>
              <h1>Журнал действий</h1>
            </div>
            <button className="btn btn-danger" style={{ padding: '8px 16px', fontSize: 12 }}
              disabled={purging} onClick={handlePurge}
              title="Удаляются только действия администратора старше 30 дней. История заказов не удаляется.">
              {purging ? 'Удаляем…' : 'Удалить записи старше 30 дней'}
            </button>
          </div>

          {notice && (
            <div style={{ fontFamily: 'sans-serif', fontSize: 13, marginBottom: 16, color: 'var(--green)' }}>{notice}</div>
          )}

          <div className="row" style={{ gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
            {FILTERS.map(f => (
              <button
                key={f.key || 'all'}
                onClick={() => { setOffset(0); setKind(f.key) }}
                className="btn btn-ghost"
                style={{
                  padding: '5px 12px', fontSize: 12,
                  background: kind === f.key ? '#1a2540' : undefined,
                  color: kind === f.key ? '#fff' : undefined,
                  borderColor: kind === f.key ? '#1a2540' : undefined,
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {error && (
            <div style={{
              borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontFamily: 'sans-serif',
              fontSize: 13, background: '#fff5f5', border: '1px solid rgba(192,57,43,0.25)', color: 'var(--red)',
            }}>
              {error}
            </div>
          )}

          <table className="tbl">
            <thead>
              <tr>
                <th>Когда</th>
                <th>Кто</th>
                <th>Действие</th>
                <th>Объект</th>
                <th>Подробности</th>
                <th>Код</th>
              </tr>
            </thead>
            <tbody>
              {items.map(e => (
                <tr key={e.id}>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13, whiteSpace: 'nowrap' }}>{fmtDate(e.created_at)}</td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
                    {e.kind === 'order' ? <span className="faint">система</span> : (e.actor_email ?? '—')}
                    {e.impersonated && <span className="faint" style={{ marginLeft: 6, fontSize: 11 }}>от лица</span>}
                  </td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
                    {e.kind === 'order' ? 'Статус заказа' : (ACTION_LABEL[e.action] ?? e.action)}
                  </td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>
                    {e.order
                      ? <>{e.order.user_email} · {e.order.amount.toLocaleString('ru-RU')} ₽{e.order.is_test && <span className="faint" style={{ marginLeft: 6 }}>тест</span>}</>
                      : e.entity_type
                        ? <span className="faint">{e.entity_type}: {e.entity_id}</span>
                        : '—'}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'rgba(26,37,64,0.7)', maxWidth: 420, wordBreak: 'break-word' }}>
                    {details(e) || '—'}
                  </td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 12, color: e.status_code && e.status_code >= 400 ? 'var(--red)' : undefined }}>
                    {e.status_code ?? ''}
                  </td>
                </tr>
              ))}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={6} className="faint" style={{ padding: '18px 0' }}>
                    Записей пока нет. Журнал ведётся с момента установки (6 октября 2026).
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="row" style={{ justifyContent: 'space-between', marginTop: 18, gap: 12 }}>
            <span className="faint">{loading ? 'Загрузка…' : `Показано ${shown} из ${total}`}</span>
            <span className="row" style={{ gap: 6 }}>
              <button className="btn btn-ghost" style={{ padding: '5px 12px', fontSize: 12 }}
                disabled={offset === 0 || loading}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>← назад</button>
              <button className="btn btn-ghost" style={{ padding: '5px 12px', fontSize: 12 }}
                disabled={shown >= total || loading}
                onClick={() => setOffset(offset + PAGE_SIZE)}>вперёд →</button>
            </span>
          </div>

        </div>
      </div>
    </>
  )
}

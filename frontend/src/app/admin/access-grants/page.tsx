'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe, type AccessGrant } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const STATUS_LABEL: Record<AccessGrant['status'], string> = {
  active:  'Действует',
  pending: 'Ещё не начался',
  used_up: 'Квота исчерпана',
  expired: 'Срок истёк',
  revoked: 'Отозван',
}

const STATUS_COLOR: Record<AccessGrant['status'], string> = {
  active:  '#1a6640',
  pending: '#1e3a8a',
  used_up: '#8a6d00',
  expired: '#7a7a7a',
  revoked: '#c0392b',
}

const fmtDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'

export default function AdminAccessGrantsPage() {
  const router = useRouter()
  const [grants, setGrants] = useState<AccessGrant[]>([])
  const [onlyActive, setOnlyActive] = useState(true)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [msg, setMsg] = useState('')

  async function load(active: boolean) {
    setGrants(await adminApi.accessGrants(active ? 'active' : undefined))
  }

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        await load(true)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  async function switchFilter(next: boolean) {
    setOnlyActive(next)
    setLoading(true)
    try { await load(next) } catch { setMsg('Не удалось загрузить список') } finally { setLoading(false) }
  }

  async function handleRevoke(g: AccessGrant) {
    if (!confirm('Отозвать доступ у ' + (g.user_email ?? '') + '? Уже сформированные отчёты останутся у пользователя.')) return
    setBusyId(g.id); setMsg('')
    try {
      await adminApi.revokeAccessGrant(g.id)
      setMsg('Доступ отозван')
      await load(onlyActive)
    } catch (e: any) {
      setMsg(e?.message ?? 'Не удалось отозвать доступ')
    } finally { setBusyId(null) }
  }

  async function handleNotify(g: AccessGrant) {
    setBusyId(g.id); setMsg('')
    try {
      await adminApi.notifyAccessGrant(g.id)
      setMsg('Письмо отправлено повторно')
      await load(onlyActive)
    } catch (e: any) {
      setMsg(e?.message ?? 'Не удалось отправить письмо')
    } finally { setBusyId(null) }
  }

  const activeRemaining = grants
    .filter(g => g.status === 'active')
    .reduce((sum, g) => sum + g.remaining, 0)

  return (
    <>
      <AdminNav current="access-grants" />
      <div className="admin-shell">
        <AdminSide current="access-grants" />
        <div className="admin-main">
          <div className="admin-header">
            <div>
              <span className="label-red">Доступы</span>
              <h1>Тестовый доступ</h1>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <button
                onClick={() => switchFilter(true)}
                style={{ padding: '8px 14px', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', border: '1px solid var(--line)', background: onlyActive ? '#1a2540' : 'var(--card)', color: onlyActive ? '#fff' : 'inherit' }}
              >Только действующие</button>
              <button
                onClick={() => switchFilter(false)}
                style={{ padding: '8px 14px', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', border: '1px solid var(--line)', background: onlyActive ? 'var(--card)' : '#1a2540', color: onlyActive ? 'inherit' : '#fff' }}
              >Все</button>
            </div>
          </div>

          <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', marginBottom: 14 }}>
            Доступ выдаётся в карточке пользователя (Пользователи → выбрать → «Тестовый доступ»).
            Квота считается по завершённым диагностикам: отозванный или просроченный доступ не мешает
            пользователю открывать уже полученные отчёты.
          </p>

          {msg && (
            <div style={{ fontFamily: 'sans-serif', fontSize: 13, marginBottom: 12, color: '#1a6640' }}>{msg}</div>
          )}

          {loading ? (
            <p style={{ fontFamily: 'sans-serif', fontSize: 13 }}>Загрузка…</p>
          ) : grants.length === 0 ? (
            <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>
              {onlyActive ? 'Действующих доступов нет.' : 'Доступы ещё не выдавались.'}
            </p>
          ) : (
            <>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginBottom: 8 }}>
                Записей: {grants.length}. Нераспределённый остаток по действующим: {activeRemaining}.
              </div>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Пользователь</th>
                    <th>Квота</th>
                    <th>Исп.</th>
                    <th>Остаток</th>
                    <th>Действует до</th>
                    <th>Статус</th>
                    <th>Причина</th>
                    <th>Письмо</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {grants.map(g => (
                    <tr key={g.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{g.user_email ?? '—'}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-mute)' }}>{g.user_name ?? ''}</div>
                      </td>
                      <td>{g.quota}</td>
                      <td>{g.used}</td>
                      <td>{g.remaining}</td>
                      <td>{fmtDate(g.expires_at)}</td>
                      <td style={{ color: STATUS_COLOR[g.status], fontWeight: 600 }}>{STATUS_LABEL[g.status]}</td>
                      <td style={{ fontSize: 12, maxWidth: 220 }}>{g.reason ?? '—'}</td>
                      <td style={{ fontSize: 12 }}>{g.email_sent_at ? fmtDate(g.email_sent_at) : 'не отправлено'}</td>
                      <td>
                        <div className="row" style={{ gap: 6 }}>
                          <button
                            disabled={busyId === g.id || g.status === 'revoked' || g.status === 'expired'}
                            onClick={() => handleNotify(g)}
                            style={{ padding: '5px 10px', fontSize: 12, borderRadius: 4, cursor: 'pointer', border: '1px solid var(--line)', background: 'var(--card)' }}
                          >Письмо</button>
                          <button
                            disabled={busyId === g.id || g.status === 'revoked'}
                            onClick={() => handleRevoke(g)}
                            style={{ padding: '5px 10px', fontSize: 12, borderRadius: 4, cursor: 'pointer', border: '1px solid #c0392b', background: 'var(--card)', color: '#c0392b' }}
                          >Отозвать</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </>
  )
}

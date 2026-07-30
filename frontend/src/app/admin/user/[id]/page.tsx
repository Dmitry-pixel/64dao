'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getMe, adminApi, listAssessments, reportDownloadUrl, type AccessGrant } from '@/lib/api'

const GRANT_STATUS: Record<string, string> = {
  active: 'Действует', pending: 'Ещё не начался', used_up: 'Квота исчерпана',
  expired: 'Срок истёк', revoked: 'Отозван',
}

const GRANT_COLOR: Record<string, string> = {
  active: '#166534', pending: '#1e3a8a', used_up: '#8a6d00',
  expired: '#7a7a7a', revoked: '#c0392b',
}

export default function AdminUserPage() {
  const router = useRouter()
  const params = useParams()
  const userId = params.id as string
  const [userData, setUserData] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState<string | null>(null)
  const [msg, setMsg] = useState('')
  const [grants, setGrants] = useState<AccessGrant[]>([])
  const [grantBusy, setGrantBusy] = useState(false)
  const [quota, setQuota] = useState(2)
  const [preset, setPreset] = useState('14')
  const [customDate, setCustomDate] = useState('')
  const [reason, setReason] = useState('')
  const [notify, setNotify] = useState(true)

  useEffect(() => {
    getMe()
      .then(me => {
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        return Promise.all([
          adminApi.users().then((users: unknown) => { const userList = users as any[];
            const u = userList.find((u: any) => u.id === userId)
            if (u) setUserData(u)
          }),
          adminApi.reports().then((assessments: unknown) => { const assessList = assessments as any[];
            setAssessments(assessList.filter((a: any) => a.user_id === userId))
          }),
        ])
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router, userId])

  async function loadGrants() {
    try { setGrants(await adminApi.userAccessGrants(userId)) } catch { setGrants([]) }
  }

  useEffect(() => { loadGrants() }, [userId])

  async function handleGrant() {
    // Срок: пресет в днях либо своя дата (конец дня, чтобы «до 15.08»
    // означало включительно). Бэкенд не примет дату в прошлом.
    const expires = preset === 'custom'
      ? new Date(customDate + 'T23:59:59').toISOString()
      : new Date(Date.now() + Number(preset) * 86400000).toISOString()
    if (preset === 'custom' && !customDate) { setMsg('Укажите дату окончания доступа'); return }
    setGrantBusy(true); setMsg('')
    try {
      await adminApi.createAccessGrant(userId, {
        quota, expires_at: expires, reason: reason.trim() || null, notify,
      })
      setMsg(notify ? 'Доступ выдан, письмо отправлено' : 'Доступ выдан без письма')
      setReason('')
      await loadGrants()
    } catch (e: any) {
      setMsg(`Не удалось выдать доступ: ${e?.message || 'ошибка'}`)
    } finally {
      setGrantBusy(false)
    }
  }

  async function handleRevokeGrant(id: string) {
    if (!window.confirm('Отозвать доступ? Уже сформированные отчёты останутся у пользователя.')) return
    setGrantBusy(true); setMsg('')
    try {
      await adminApi.revokeAccessGrant(id)
      setMsg('Доступ отозван')
      await loadGrants()
    } catch (e: any) {
      setMsg(`Не удалось отозвать доступ: ${e?.message || 'ошибка'}`)
    } finally {
      setGrantBusy(false)
    }
  }

  async function handleNotifyGrant(id: string) {
    setGrantBusy(true); setMsg('')
    try {
      await adminApi.notifyAccessGrant(id)
      setMsg('Письмо отправлено повторно')
      await loadGrants()
    } catch (e: any) {
      setMsg(`Не удалось отправить письмо: ${e?.message || 'ошибка'}`)
    } finally {
      setGrantBusy(false)
    }
  }

  const CONTOUR_TITLE: Record<string, string> = {
    finance: 'Финансовая функция', product: 'Продукт/Сервис',
    process: 'Операционные процессы', market: 'Рынок и продажи',
  }

  async function resetContour(aid: string, contour: string, title: string) {
    if (!window.confirm(`Сбросить контур «${title}»? Пользователь сможет пройти его заново. Отменить нельзя.`)) return
    setResetting(`${aid}:${contour}`); setMsg('')
    try {
      await adminApi.resetContour(aid, contour)
      setAssessments(prev => prev.map(a => a.id === aid
        ? { ...a, passed_contours: (a.passed_contours || []).filter((c: any) => c.contour !== contour) }
        : a))
      setMsg(`Контур «${title}» сброшен. Отчёт пересоберётся при следующем скачивании.`)
    } catch (e: any) {
      setMsg(`Не удалось сбросить «${title}»: ${e?.message || 'ошибка'}`)
    } finally {
      setResetting(null)
    }
  }

  if (loading) return (
    <div style={S.center}><p style={{ color: '#666', fontFamily: 'sans-serif' }}>Загрузка...</p></div>
  )

  if (!userData) return (
    <div style={S.center}><p style={{ color: '#666', fontFamily: 'sans-serif' }}>Пользователь не найден</p></div>
  )

  return (
    <div style={S.page}>
      <div style={S.container}>

        <div style={S.header}>
          <div>
            <button onClick={() => router.push('/admin')} style={S.backBtn}>← Назад в админку</button>
            <h1 style={S.h1}>{userData.full_name || userData.email}</h1>
            <p style={{ color: '#666', fontFamily: 'sans-serif', fontSize: 14, marginTop: 4 }}>
              {userData.email} · <span style={userData.role === 'admin' ? S.badgeAdmin : S.badgeUser}>{userData.role}</span>
            </p>
          </div>
        </div>

        {/* Информация о пользователе */}
        <div style={S.card}>
          <h2 style={S.h2}>Информация</h2>
          <div className="admin-info-grid" style={S.infoGrid}>
            <div><span style={S.infoLabel}>Email</span><span style={S.infoValue}>{userData.email}</span></div>
            <div><span style={S.infoLabel}>Имя</span><span style={S.infoValue}>{userData.full_name || '—'}</span></div>
            <div><span style={S.infoLabel}>Компания</span><span style={S.infoValue}>{userData.company_name || '—'}</span></div>
            <div><span style={S.infoLabel}>Роль</span><span style={S.infoValue}>{userData.role}</span></div>
            <div><span style={S.infoLabel}>Зарегистрирован</span><span style={S.infoValue}>{new Date(userData.created_at).toLocaleDateString('ru-RU')}</span></div>
          </div>
        </div>

        {msg && (
          <div style={{ background: 'rgba(46,125,50,0.08)', border: '1px solid rgba(46,125,50,0.25)', borderRadius: 8, padding: '10px 14px', fontFamily: 'sans-serif', fontSize: 13, color: '#166534', marginBottom: 16 }}>{msg}</div>
        )}

        {/* Тестовый доступ: квота бесплатных диагностик на срок */}
        <div style={S.card}>
          <h2 style={S.h2}>Тестовый доступ</h2>
          <p style={{ color: '#666', fontFamily: 'sans-serif', fontSize: 13, margin: '0 0 14px' }}>
            Партнёр проходит диагностику без оплаты: указанное число отчётов в течение срока.
            Право на бесплатный повтор такие диагностики не дают — квота равна числу прогонов.
          </p>
          {userData.role === 'admin' && (
            <p style={{ color: '#8a6d00', fontFamily: 'sans-serif', fontSize: 13, margin: '0 0 14px' }}>
              Администратор проходит диагностику без гейта оплаты — грант ему не нужен.
            </p>
          )}
          <div className="row" style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end', marginBottom: 16 }}>
            <label style={{ display: 'block' }}>
              <span style={S.infoLabel}>Диагностик</span>
              <input type="number" min={1} max={50} value={quota}
                onChange={e => setQuota(Math.max(1, Number(e.target.value) || 1))}
                style={{ ...{ padding: '8px 10px', border: '1px solid #e0dcd3', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, background: '#fff' }, width: 80 }} />
            </label>
            <label style={{ display: 'block' }}>
              <span style={S.infoLabel}>Срок</span>
              <select value={preset} onChange={e => setPreset(e.target.value)} style={{ padding: '8px 10px', border: '1px solid #e0dcd3', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, background: '#fff' }}>
                <option value="14">14 дней</option>
                <option value="30">30 дней</option>
                <option value="custom">своя дата</option>
              </select>
            </label>
            {preset === 'custom' && (
              <label style={{ display: 'block' }}>
                <span style={S.infoLabel}>Действует до</span>
                <input type="date" value={customDate} onChange={e => setCustomDate(e.target.value)}
                  style={{ padding: '8px 10px', border: '1px solid #e0dcd3', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, background: '#fff' }} />
              </label>
            )}
            <label style={{ display: 'block', flex: 1, minWidth: 200 }}>
              <span style={S.infoLabel}>Причина (для себя)</span>
              <input value={reason} onChange={e => setReason(e.target.value)}
                placeholder="Пилот, ООО «Партнёр»"
                style={{ ...{ padding: '8px 10px', border: '1px solid #e0dcd3', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, background: '#fff' }, width: '100%' }} />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'sans-serif', fontSize: 13, color: '#333', paddingBottom: 8 }}>
              <input type="checkbox" checked={notify} onChange={e => setNotify(e.target.checked)} />
              письмо
            </label>
            <button onClick={handleGrant} disabled={grantBusy || userData.role === 'admin'}
              style={{ background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 18px', fontFamily: 'sans-serif', fontSize: 13, fontWeight: 600, cursor: grantBusy ? 'default' : 'pointer', opacity: grantBusy ? 0.5 : 1 }}>
              Выдать доступ
            </button>
          </div>
          {grants.length === 0 ? (
            <p style={{ color: '#999', fontFamily: 'sans-serif', fontSize: 13 }}>Доступ не выдавался</p>
          ) : (
            <table style={S.table}>
              <thead>
                <tr>{['Квота', 'Исп.', 'Остаток', 'Действует до', 'Статус', 'Письмо', 'Причина', ''].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {grants.map(g => (
                  <tr key={g.id}>
                    <td style={S.td}>{g.quota}</td>
                    <td style={S.td}>{g.used}</td>
                    <td style={S.td}>{g.remaining}</td>
                    <td style={S.td}>{new Date(g.expires_at).toLocaleDateString('ru-RU')}</td>
                    <td style={{ ...S.td, color: GRANT_COLOR[g.status], fontWeight: 600 }}>{GRANT_STATUS[g.status] || g.status}</td>
                    <td style={S.td}>{g.email_sent_at ? new Date(g.email_sent_at).toLocaleDateString('ru-RU') : 'нет'}</td>
                    <td style={{ ...S.td, fontSize: 12, color: '#666' }}>{g.reason || '—'}</td>
                    <td style={S.td}>
                      <button onClick={() => handleNotifyGrant(g.id)} disabled={grantBusy || g.status === 'revoked' || g.status === 'expired'}
                        style={{ border: 'none', background: 'none', color: '#1e3a8a', cursor: 'pointer', fontSize: 12, padding: 0, marginRight: 10 }}>письмо</button>
                      <button onClick={() => handleRevokeGrant(g.id)} disabled={grantBusy || g.status === 'revoked'}
                        style={{ border: 'none', background: 'none', color: '#c0392b', cursor: 'pointer', fontSize: 12, padding: 0 }}>отозвать</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Диагностики пользователя */}
        <div style={S.card}>
          <h2 style={S.h2}>Диагностики ({assessments.length})</h2>
          {assessments.length === 0 ? (
            <p style={{ color: '#999', fontFamily: 'sans-serif', fontSize: 13 }}>Нет диагностик</p>
          ) : (
            <table style={S.table}>
              <thead>
                <tr>{['Комбинация', 'Статус', 'Отчётов', 'Дата', 'Контуры', ''].map(h => <th key={h} style={S.th}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {assessments.map((a: any) => (
                  <tr key={a.id}>
                    <td style={{ ...S.td, fontFamily: 'monospace', letterSpacing: 2, fontWeight: 700 }}>{a.method1_combination || '—'}</td>
                    <td style={S.td}>{a.status}</td>
                    <td style={S.td}>{a.reports.length}</td>
                    <td style={S.td}>{new Date(a.created_at).toLocaleDateString('ru-RU')}</td>
                    <td style={S.td}>
                      {((a.passed_contours || []).filter((c: any) => c.contour !== 'finance')).length === 0
                        ? <span style={{ color: '#bbb' }}>—</span>
                        : (a.passed_contours || []).filter((c: any) => c.contour !== 'finance').map((c: any) => (
                          <span key={c.contour} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: '#f1f5f9', borderRadius: 12, padding: '2px 8px', marginRight: 6, marginBottom: 4, fontSize: 12, color: '#475569' }}>
                            {CONTOUR_TITLE[c.contour] || c.contour}
                            <button onClick={() => resetContour(a.id, c.contour, CONTOUR_TITLE[c.contour] || c.contour)}
                              disabled={resetting === `${a.id}:${c.contour}`} title="Сбросить контур"
                              style={{ border: 'none', background: 'none', color: '#c0392b', cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: 0, opacity: resetting === `${a.id}:${c.contour}` ? 0.4 : 1 }}>×</button>
                          </span>
                        ))}
                    </td>
                    <td style={S.td}>
                      {a.reports[0] && (
                        <a href={reportDownloadUrl(a.reports[0].id)} target="_blank" rel="noreferrer"
                          style={{ color: '#1a2540', fontWeight: 600, textDecoration: 'none', fontSize: 13 }}>
                          ↓ PDF
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#e8e4db', fontFamily: 'Arial,sans-serif', padding: '32px 16px' },
  center: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#e8e4db' },
  container: { maxWidth: 800, margin: '0 auto' },
  header: { marginBottom: 24 },
  backBtn: { background: 'none', border: 'none', color: '#c0392b', fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif', padding: 0, marginBottom: 12, display: 'block' },
  h1: { color: '#1a2540', margin: 0, fontSize: 24, fontWeight: 700, fontFamily: 'Georgia,serif' },
  h2: { color: '#1a2540', margin: '0 0 16px', fontSize: 16, fontWeight: 600, fontFamily: 'sans-serif' },
  card: { background: '#fff', borderRadius: 10, padding: '20px 24px', marginBottom: 16 },
  infoGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 },
  infoLabel: { display: 'block', fontSize: 11, color: '#999', fontFamily: 'sans-serif', marginBottom: 2 },
  infoValue: { fontSize: 14, color: '#1a2540', fontFamily: 'sans-serif', fontWeight: 500 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'sans-serif' },
  th: { padding: '8px 12px', textAlign: 'left', color: '#999', fontWeight: 500, borderBottom: '1px solid #f0ede8' },
  td: { padding: '10px 12px', borderBottom: '1px solid #f7f5f2', color: '#333' },
  badgeAdmin: { background: '#fef3c7', color: '#92400e', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500, fontFamily: 'sans-serif' },
  badgeUser: { background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500, fontFamily: 'sans-serif' },
}

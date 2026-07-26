'use client'
import { FollowupBadge } from '@/components/FollowupBadge'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getMe, listAssessments, deleteAssessment, listContours, isMethod2, type ContourInfo } from '@/lib/api'
import { AdminNav, AdminSide, hexFor, hexNameFor } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function AdminMyReportsPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [contours, setContours] = useState<ContourInfo[]>([])
  const [query, setQuery] = useState('')

  useEffect(() => {
    listContours().then(r => setContours(r.contours)).catch(() => setContours([]))
  }, [])

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        setUser(me)
        const data = await listAssessments()
        setAssessments(data)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  // Поиск идёт на сервере: клиентская фильтрация развалится, как только
  // выдача станет постраничной. Дебаунс, чтобы не бить по API на каждый символ.
  useEffect(() => {
    if (loading) return
    const t = setTimeout(() => {
      listAssessments(query).then(setAssessments).catch(() => {})
    }, 400)
    return () => clearTimeout(t)
  }, [query])

  const handleDelete = async (id: string) => {
    setDeletingId(id)
    try {
      await deleteAssessment(id)
      setAssessments(prev => prev.filter(a => a.id !== id))
    } catch {
      alert('Не удалось удалить отчёт. Попробуйте ещё раз.')
    } finally {
      setDeletingId(null)
      setConfirmId(null)
    }
  }


  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка…
    </div>
  )

  const completed = assessments.filter(a => a.status === 'completed').length
  const drafts = assessments.filter(a => a.status === 'draft').length

  return (
    <>
      <AdminNav current="my-reports" />
      <div className="admin-shell">
        <AdminSide current="my-reports" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div className="admin-page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <span className="label-red">Диагностики</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>Мои отчёты</h1>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>
                {assessments.length === 0
                  ? 'Начните первую диагностику.'
                  : `${completed} готовых · ${drafts} черновик${drafts === 1 ? '' : 'а'} · всего ${assessments.length}`}
              </p>
            </div>
            <Link href="/assessment" className="btn btn-primary btn-lg">+ Новая диагностика</Link>
          </div>

          <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Название компании"
              style={{ flex: 1, minWidth: 220, padding: '10px 14px', fontFamily: 'sans-serif', fontSize: 14, border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, background: 'rgba(255,255,255,0.8)', color: 'var(--text)' }}
            />
            <button className="btn btn-primary" style={{ padding: '10px 20px', fontSize: 13 }}
              onClick={() => listAssessments(query).then(setAssessments).catch(() => {})}>
              Искать по названию компании
            </button>
            {query.trim() !== "" && (
              <button className="btn btn-ghost" style={{ padding: '10px 16px', fontSize: 13 }}
                onClick={() => setQuery("")}>Сбросить</button>
            )}
          </div>
          {assessments.length === 0 && query.trim() !== "" ? (
            <div className="dash-empty">
              <h3>Ничего не найдено</h3>
              <p>По запросу «{query}» диагностик нет. Проверьте название компании.</p>
            </div>
          ) : assessments.length === 0 ? (
            <div className="dash-empty">
              <span style={{ fontSize: 52, fontFamily: 'Georgia,serif', color: 'var(--blue)', display: 'block', marginBottom: 18 }}>䷀</span>
              <h3>Пока нет диагностик</h3>
              <p>Запустите диагностику — отчёт появится здесь без необходимости оплаты.</p>
              <Link href="/assessment" className="btn btn-primary btn-lg" style={{ marginTop: 16, display: 'inline-block' }}>
                Начать диагностику →
              </Link>
            </div>
          ) : (
            <div className="dash-list">
              {assessments.map((a, i) => (
                <div
                  key={a.id}
                  className="dash-card"
                  onClick={() => a.status === 'completed' ? router.push(`/report/${a.id}`) : undefined}
                  style={{ cursor: a.status === 'completed' ? 'pointer' : 'default' }}
                >
                  <div className="dash-num">{String(i + 1).padStart(2, '0')}</div>
                  <div className="hex-block">
                    {isMethod2(a)
                      ? <span style={{ fontFamily: 'Georgia,serif', fontSize: 40, color: '#1e3a8a', lineHeight: 1 }}>䷿</span>
                      : a.strategy_image_url
                        ? <img src={`${API}${a.strategy_image_url}`} alt="" style={{ width: 48, height: 48, objectFit: 'contain' }} />
                        : <span style={{ fontFamily: 'Georgia,serif', fontSize: 40, color: '#1e3a8a', lineHeight: 1 }}>{hexFor(a.method1_combination ?? '')}</span>}
                  </div>
                  <div>
                    <div className="dash-meta">
                      {isMethod2(a)
                        ? `Метод 2 · Бизнес-модель`
                        : hexNameFor(a.method1_combination ?? '')} · {new Date(a.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div className="dash-title">
                      {a.status === 'completed'
                        ? (isMethod2(a)
                            ? `Бизнес-модель${a.company_name ? ' · ' + a.company_name : ''}`
                            : `Стратегический профиль компании · ${a.company_name || 'Компания'}`)
                        : 'Диагностика в процессе'}
                    </div>
                    <div className="dash-detail">{a.status === 'draft' ? 'Черновик' : 'Завершено'}</div>
                    <FollowupBadge a={a} />
                    {!isMethod2(a) && a.status !== 'draft' && (
                      <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(26,37,64,0.08)' }}>
                        <div style={{ fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)', fontWeight: 700, marginBottom: 6 }}>
                          Состав диагностики
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 8, alignItems: 'center' }}>
                          {contours.filter(c => c.enabled).map(c => {
                            const passed = (a.passed_contours || []).find((p: any) => p.contour === c.contour)
                            if (passed) return (
                              <span key={c.contour} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.65)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 4, padding: '3px 8px' }}>
                                {c.title}
                                <span style={{ fontFamily: 'serif', fontSize: 16, color: '#1e3a8a', lineHeight: 1 }} title={`${hexNameFor(passed.combination)} · ${passed.combination}`}>
                                  {hexFor(passed.combination)}
                                </span>
                              </span>
                            )
                            if (c.contour === 'finance') return null
                            return (
                              <button key={c.contour}
                                style={{ fontFamily: 'sans-serif', fontSize: 11, color: '#1a2540', background: 'none', border: '1px dashed rgba(26,37,64,0.3)', borderRadius: 4, padding: '3px 10px', cursor: 'pointer' }}
                                onClick={e => { e.stopPropagation(); router.push(`/assessment/contour/${c.contour}?assessment=${a.id}`) }}>
                                {c.title} — пройти →
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="dash-actions">
                    <span className={`pill pill-${a.status}`}>
                      {a.status === 'completed' ? 'Готов' : 'Черновик'}
                    </span>
                    {a.status === 'completed' ? (
                      <>
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '7px 14px', fontSize: 12 }}
                          onClick={e => { e.stopPropagation(); router.push(`/report/${a.id}`) }}
                        >
                          Смотреть отчёт
                        </button>
                        <a
                          href={`/api/assessments/${a.id}/pdf`}
                          target="_blank"
                          rel="noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="btn btn-primary"
                          style={{ padding: '7px 14px', fontSize: 12, textDecoration: 'none' }}
                        >
                          Скачать PDF
                        </a>
                      </>
                    ) : (
                      <button
                        className="btn btn-ghost"
                        style={{ padding: '7px 14px', fontSize: 12 }}
                        onClick={e => { e.stopPropagation(); router.push('/assessment') }}
                      >
                        Новая диагностика
                      </button>
                    )}
                    <button
                      className="btn btn-ghost"
                      style={{ padding: '7px 14px', fontSize: 12, color: '#c0392b', borderColor: 'rgba(192,57,43,0.25)' }}
                      onClick={e => { e.stopPropagation(); setConfirmId(a.id) }}
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {confirmId && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setConfirmId(null)}
        >
          <div
            style={{ background: '#fff', borderRadius: 10, padding: '32px 36px', maxWidth: 400, width: '90%', boxShadow: '0 8px 40px rgba(0,0,0,0.18)' }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 20, fontWeight: 400, color: '#1a2540', margin: '0 0 12px' }}>Удалить отчёт?</h3>
            <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.65)', lineHeight: 1.6, margin: '0 0 24px' }}>
              Диагностика и PDF-файл будут удалены безвозвратно.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                style={{ background: 'none', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' }}
                onClick={() => setConfirmId(null)}
              >
                Отмена
              </button>
              <button
                style={{ background: '#c0392b', border: 'none', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#fff', opacity: deletingId === confirmId ? 0.6 : 1 }}
                disabled={deletingId === confirmId}
                onClick={() => handleDelete(confirmId)}
              >
                {deletingId === confirmId ? 'Удаляем…' : 'Да, удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getMe, listAssessments, reportDownloadUrl, deleteAssessment } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

export default function AdminMyReportsPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)

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
    <div className="app-layout">
      <AdminNav current="my-reports" />
      <div className="admin-body">
        <AdminSide current="my-reports" />
        <main className="admin-main" style={{ padding: '32px 40px' }}>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
            <div>
              <span className="label-red">Диагностики</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>Мои отчёты</h1>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>
                {assessments.length === 0
                  ? 'Начните первую диагностику.'
                  : `${completed} готовых · ${drafts} черновик${drafts === 1 ? '' : 'а'} · всего ${assessments.length}`}
              </p>
            </div>
            <Link href="/assessment/start" className="btn btn-primary btn-lg">+ Новая диагностика</Link>
          </div>

          {assessments.length === 0 ? (
            <div className="dash-empty">
              <span style={{ fontSize: 52, fontFamily: 'Georgia,serif', color: 'var(--blue)', display: 'block', marginBottom: 18 }}>䷀</span>
              <h3>Пока нет диагностик</h3>
              <p>Запустите диагностику — отчёт появится здесь без необходимости оплаты.</p>
              <Link href="/assessment/start" className="btn btn-primary btn-lg" style={{ marginTop: 16, display: 'inline-block' }}>
                Начать диагностику →
              </Link>
            </div>
          ) : (
            <div className="dash-list">
              {assessments.map((a, i) => (
                <div
                  key={a.id}
                  className="dash-card"
                  onClick={() => a.status === 'completed' ? router.push(`/report/${a.id}`) : router.push(`/assessment/${a.id}`)}
                >
                  <div className="dash-num">{String(i + 1).padStart(2, '0')}</div>
                  <div className="hex-block">{hexFor(a.method1_combination ?? '')}</div>
                  <div>
                    <div className="dash-meta">
                      {a.method1_combination ?? '—'} · {new Date(a.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div className="dash-title">
                      {a.status === 'completed' ? `Стратегия «${a.method1_combination ?? '—'}»` : 'Диагностика в процессе'}
                    </div>
                    <div className="dash-detail">{a.status === 'draft' ? 'Черновик' : 'Завершено'}</div>
                  </div>
                  <div className="dash-actions">
                    <span className={`pill pill-${a.status}`}>
                      {a.status === 'completed' ? 'Готов' : 'Черновик'}
                    </span>
                    {a.status === 'completed' && a.reports?.length > 0 ? (
                      <a
                        href={reportDownloadUrl(a.reports[0].id)}
                        onClick={e => e.stopPropagation()}
                        className="btn btn-ghost"
                        style={{ padding: '7px 14px', fontSize: 12 }}
                      >
                        Скачать PDF
                      </a>
                    ) : (
                      <button className="btn btn-soft" style={{ padding: '7px 14px', fontSize: 12 }}>
                        Продолжить →
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
        </main>
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
    </div>
  )
}

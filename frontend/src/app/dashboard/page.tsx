'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getMe, listAssessments, reportDownloadUrl } from '@/lib/api'
import { AppNav } from '@/components/AppNav'

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role === 'admin') { router.push('/admin'); return }
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

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>

  const firstName = user?.full_name?.split(' ')[0] ?? 'Пользователь'
  const completed = assessments.filter(a => a.status === 'completed').length
  const drafts = assessments.filter(a => a.status === 'draft').length

  return (
    <>
      <AppNav current="dashboard" />

      <div className="dash-hero">
        <span className="label-red">Личный кабинет</span>
        <div className="between" style={{ marginTop: 8 }}>
          <div>
            <h1 className="h1-serif" style={{ marginBottom: 6 }}>Здравствуйте, {firstName}</h1>
            <p className="muted">
              {assessments.length === 0
                ? 'Начните первую диагностику — это займёт около 15 минут.'
                : `У вас ${completed} готовых отчёт${completed === 1 ? '' : 'а'} и ${drafts} черновик${drafts === 1 ? '' : 'а'}.`
              }
            </p>
          </div>
          <Link href="/assessment/start" className="btn btn-primary btn-lg">+ Новая диагностика</Link>
        </div>
      </div>

      <div className="dash-grid">
        <div>
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 16 }}>
            <span className="label-red">Мои отчёты</span>
            <span className="faint">{assessments.length} записей</span>
          </div>

          {assessments.length === 0 ? (
            <div className="dash-empty">
              <span className="hex-xl hex" style={{ display: 'block', marginBottom: 18 }}>䷀</span>
              <h3>Пока нет диагностик</h3>
              <p>Метод 1 — 6 вопросов о состоянии компании. Метод 2 — оценка 9 блоков бизнес-модели. Результат: PDF-отчёт со стратегией.</p>
              <Link href="/assessment/start" className="btn btn-primary btn-lg">Начать диагностику →</Link>
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
                    <div className="dash-meta">{a.method1_combination ?? '—'} · {new Date(a.created_at).toLocaleDateString('ru')}</div>
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
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <aside className="dash-side">
          <div className="card-flat">
            <span className="label-red" style={{ display: 'block', marginBottom: 10 }}>Поддержка</span>
            <p className="faint" style={{ lineHeight: 1.6, marginBottom: 12 }}>
              Вопрос по отчёту или диагностике? Напишите нам — ответим в течение рабочего дня.
            </p>
            <button className="btn btn-ghost" style={{ padding: '8px 14px', fontSize: 12 }}>Написать в поддержку</button>
          </div>
          <div className="card-flat">
            <span className="label-red" style={{ display: 'block', marginBottom: 10 }}>Статистика</span>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 6 }}>
              <span style={{ color: 'var(--text-mute)' }}>Завершено</span>
              <strong>{completed}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 6 }}>
              <span style={{ color: 'var(--text-mute)' }}>В работе</span>
              <strong>{drafts}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'sans-serif', fontSize: 13 }}>
              <span style={{ color: 'var(--text-mute)' }}>Всего</span>
              <strong>{assessments.length}</strong>
            </div>
          </div>
        </aside>
      </div>
    </>
  )
}

'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getMe, listAssessments, deleteAssessment } from '@/lib/api'
import { AppNav } from '@/components/AppNav'
import { hexNameFor } from '@/components/AdminNav'

// combination → hexagram number (King Wen sequence)
const HEX_NUM: Record<string, number> = {
  'AAAAAA':1,'BBBBBB':2,'ABBBAB':3,'BABBBA':4,'AAABAB':5,'BABAAA':6,
  'BABBBB':7,'BBBBAB':8,'AAABAA':9,'AABAAA':10,'AAABBB':11,'BBBAAA':12,
  'ABAAAA':13,'AAAABA':14,'BBABBB':15,'BBBABB':16,'ABBAAB':17,'BAABBA':18,
  'AABBBB':19,'BBBBAA':20,'ABBABA':21,'ABABBA':22,'BBBBBA':23,'ABBBBB':24,
  'ABBAAA':25,'AAABBA':26,'ABBBBA':27,'BAAAAB':28,'BABBAB':29,'ABAABA':30,
  'BBAAAB':31,'BAAABB':32,'BBAAAA':33,'AAAABB':34,'BBBABA':35,'ABABBB':36,
  'ABABAA':37,'AABABA':38,'BBABAB':39,'BABABB':40,'AABBBA':41,'ABBBAA':42,
  'AAAAAB':43,'BAAAAA':44,'BBBAAB':45,'BAABBB':46,'BABAAB':47,'BAABAB':48,
  'ABAAAB':49,'BAAABA':50,'ABBABB':51,'BBABBA':52,'BBABAA':53,'AABABB':54,
  'ABAABB':55,'BBAABA':56,'BABBAA':57,'AABAAB':58,'BAABAA':59,'AABBAB':60,
  'AABBAA':61,'BBAABB':62,'ABABAB':63,'BABABA':64,
}

function hexFor(combo: string): string {
  const n = HEX_NUM[combo]
  if (!n) return '䷀'
  return String.fromCodePoint(0x4DC0 + n - 1)
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [assessments, setAssessments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [supportOpen, setSupportOpen] = useState(false)
  const [supportText, setSupportText] = useState('')
  const [supportSending, setSupportSending] = useState(false)
  const [supportDone, setSupportDone] = useState(false)

  const handleSupport = async () => {
    if (!supportText.trim()) return
    setSupportSending(true)
    try {
      const res = await fetch('/api/auth/support', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ message: supportText.trim() }),
      })
      if (!res.ok) throw new Error()
      setSupportDone(true)
      setSupportText('')
      setTimeout(() => { setSupportOpen(false); setSupportDone(false) }, 2000)
    } catch {
      alert('Не удалось отправить сообщение. Попробуйте позже.')
    } finally {
      setSupportSending(false)
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role === 'admin') { router.push('/admin/my-reports'); return }
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
                  onClick={() => a.status === 'completed' ? router.push(`/report/${a.id}`) : undefined}
                >
                  <div className="dash-num">{String(i + 1).padStart(2, '0')}</div>
                  <div className="hex-block" style={{ fontFamily: 'Georgia,serif', fontSize: 40, color: '#1e3a8a', lineHeight: 1 }}>
                    {a.method2_data && !a.method1_combination ? '䷿' : hexFor(a.method1_combination ?? '')}
                  </div>
                  <div>
                    <div className="dash-meta">
                      {a.method2_data && !a.method1_combination ? 'Метод 2 · Бизнес-модель' : hexNameFor(a.method1_combination ?? '')} · {new Date(a.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div className="dash-title">
                      {a.status === 'completed'
                        ? (a.method2_data && !a.method1_combination
                            ? `Бизнес-модель · ${a.company_name || user?.company_name || 'Компания'}`
                            : `Стратегический профиль компании · ${a.company_name || user?.company_name || 'Компания'}`)
                        : 'Диагностика в процессе'}
                    </div>
                    <div className="dash-detail">{a.status === 'draft' ? 'Черновик' : 'Завершено'}</div>
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
                          Открыть →
                        </button>
                        <a
                          href={`/api/assessments/${a.id}/pdf`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-ghost"
                          style={{ padding: '7px 14px', fontSize: 12, textDecoration: 'none' }}
                          onClick={e => e.stopPropagation()}
                        >
                          Скачать PDF
                        </a>
                      </>
                    ) : (
                      <button className="btn btn-soft" style={{ padding: '7px 14px', fontSize: 12 }}
                        onClick={e => { e.stopPropagation(); router.push('/assessment/start') }}>
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
        </div>

        <aside className="dash-side">
          <div className="card-flat">
            <span className="label-red" style={{ display: 'block', marginBottom: 10 }}>Поддержка</span>
            <p className="faint" style={{ lineHeight: 1.6, marginBottom: 12 }}>
              Вопрос по отчёту или диагностике? Напишите нам — ответим в течение рабочего дня.
            </p>
            <button className="btn btn-ghost" style={{ padding: '8px 14px', fontSize: 12 }} onClick={() => setSupportOpen(true)}>Написать в поддержку</button>
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
      {/* Диалог подтверждения удаления */}
      {/* Модал поддержки */}
      {supportOpen && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => { setSupportOpen(false); setSupportDone(false) }}
        >
          <div
            style={{ background: '#fff', borderRadius: 10, padding: '32px 36px', maxWidth: 460, width: '90%', boxShadow: '0 8px 40px rgba(0,0,0,0.18)' }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 20, fontWeight: 400, color: '#1a2540', margin: '0 0 8px' }}>Написать в поддержку</h3>
            <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.55)', margin: '0 0 18px', lineHeight: 1.5 }}>
              Опишите ваш вопрос — мы ответим в течение рабочего дня.
            </p>
            {supportDone ? (
              <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: '#1a7a4a', textAlign: 'center', padding: '16px 0' }}>
                ✓ Сообщение отправлено
              </p>
            ) : (
              <>
                <textarea
                  value={supportText}
                  onChange={e => setSupportText(e.target.value)}
                  placeholder="Ваш вопрос или проблема…"
                  rows={5}
                  style={{
                    width: '100%', boxSizing: 'border-box', padding: '10px 14px',
                    fontFamily: 'sans-serif', fontSize: 13, lineHeight: 1.6,
                    border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6,
                    resize: 'vertical', outline: 'none', color: '#1a2540',
                    marginBottom: 16,
                  }}
                />
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                  <button
                    style={{ background: 'none', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#1a2540' }}
                    onClick={() => setSupportOpen(false)}
                  >
                    Отмена
                  </button>
                  <button
                    style={{ background: '#1a2540', border: 'none', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#fff', opacity: supportSending || !supportText.trim() ? 0.5 : 1 }}
                    disabled={supportSending || !supportText.trim()}
                    onClick={handleSupport}
                  >
                    {supportSending ? 'Отправляем…' : 'Отправить'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

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
              Вы действительно хотите удалить этот отчёт? Диагностика и PDF-файл будут удалены безвозвратно.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button
                style={{ background: 'none', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#1a2540' }}
                onClick={() => setConfirmId(null)}
              >
                Отмена
              </button>
              <button
                style={{ background: '#c0392b', border: 'none', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#fff', fontWeight: 500, opacity: deletingId === confirmId ? 0.6 : 1 }}
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

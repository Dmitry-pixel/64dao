'use client'
import { NestedFollowups } from '@/components/NestedFollowups'
import { FollowupBadge } from '@/components/FollowupBadge'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, listAssessments, deleteAssessment, logout, listContours, isMethod2, getSiteMode, type AuthUser, type Assessment, type ContourInfo } from '@/lib/api'
import { listPortfolios, type M3Portfolio } from '@/lib/m3'
import M3ReportCard, { m3RowDate } from '@/components/M3ReportCard'
import BuyDiagnostics from '@/components/BuyDiagnostics'
import { HEXAGRAM_MAP } from '@/lib/hexagrams'

const finChar = (c?: string | null) =>
  c && HEXAGRAM_MAP[c] ? String.fromCodePoint(0x4DC0 + HEXAGRAM_MAP[c].n - 1) : ''
import React from 'react'

function SupportForm() {
  const [open, setOpen] = React.useState(false)
  const [name, setName] = React.useState('')
  const [message, setMessage] = React.useState('')
  const [sent, setSent] = React.useState(false)
  const [sending, setSending] = React.useState(false)

  async function handleSend() {
    if (!message.trim()) return
    setSending(true)
    try {
      const res = await fetch('/api/support/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          subject: name.trim() ? `Сообщение от ${name.trim()}` : 'Сообщение из личного кабинета',
          message,
        }),
      })
      if (res.ok) {
        setSent(true)
      } else {
        const errText = await res.text().catch(() => '')
        alert(`Не удалось отправить сообщение (${res.status}). ${errText}`)
      }
    } catch {
      alert('Не удалось отправить сообщение. Проверьте соединение и попробуйте снова.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={S.sideCard}>
      <span style={{ ...S.labelRed, display: 'block', marginBottom: 10 }}>Поддержка</span>
      {!open && !sent && (
        <>
          <p style={S.sideText}>Вопрос по отчёту или диагностике? Напишите нам — ответим в течение рабочего дня.</p>
          <button style={S.btnGhost} onClick={() => setOpen(true)}>Написать в поддержку</button>
        </>
      )}
      {open && !sent && (
        <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 10 }}>
          <input style={S.supportInput} placeholder="Ваше имя" value={name} onChange={e => setName(e.target.value)} />
          <textarea style={{ ...S.supportInput, minHeight: 80, resize: 'vertical' as const, lineHeight: 1.5 }}
            placeholder="Опишите ваш вопрос..." value={message} onChange={e => setMessage(e.target.value)} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={S.btnPrimary} onClick={handleSend} disabled={sending || !message.trim()}>
              {sending ? 'Отправка...' : 'Отправить'}
            </button>
            <button style={S.btnGhost} onClick={() => setOpen(false)}>Отмена</button>
          </div>
        </div>
      )}
      {sent && (
        <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#166534', lineHeight: 1.6 }}>
          ✓ Сообщение отправлено. Ответим в течение рабочего дня.
        </p>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [loading, setLoading] = useState(true)
  const [credits, setCredits] = useState<number>(0)
  const [grantCredits, setGrantCredits] = useState<number>(0)
  const [grantExpires, setGrantExpires] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [contours, setContours] = useState<ContourInfo[]>([])
  const [m3, setM3] = useState<M3Portfolio[]>([])
  const [m3Enabled, setM3Enabled] = useState(false)
  const [query, setQuery] = useState("")

  useEffect(() => {
    listContours().then(r => setContours(r.contours)).catch(() => setContours([]))
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
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getMe(), listAssessments()])
      .then(([u, a]) => { setUser(u); setAssessments(a) })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
    // Портфели Метода 3 запрашиваются только при включённом разделе:
    // выключенный отдаёт 404 на всё, и кабинет ловил бы его на каждом заходе.
    getSiteMode()
      .then(d => {
        const on = Boolean(d?.m3_enabled)
        setM3Enabled(on)
        return on ? listPortfolios() : []
      })
      .then(setM3)
      .catch(() => setM3([]))
    fetch('/api/payments/credits', { credentials: 'include' })
      .then(r => r.ok ? r.json() : { credits: 0 })
      .then(d => {
        // credits — сумма оплаченных и грантовых: показываем общий остаток,
        // а грантовую часть отдельной строкой (она сгорает по сроку).
        setCredits(d.credits ?? 0)
        setGrantCredits(d.grant_credits ?? 0)
        setGrantExpires(d.grant_expires_at ?? null)
      })
      .catch(() => setCredits(0))
  }, [router])

  async function handleDelete(id: string) {
    setDeletingId(id)
    try {
      await deleteAssessment(id)
      setAssessments(prev => prev.filter(a => a.id !== id))
    } catch {
      alert('Не удалось удалить. Попробуйте ещё раз.')
    } finally {
      setDeletingId(null)
      setConfirmId(null)
    }
  }

  async function handleLogout() {
    await logout()
    router.push('/login')
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка...</p>
    </div>
  )

  const completed = assessments.filter(a => a.status === 'completed' || a.status === 'paid')
  const drafts = assessments.filter(a => a.status === 'draft')

  // Повтор это продолжение основного отчёта, а не отдельная строка списка.
  // Осиротевший повтор (первичную удалили в админке) остаётся верхним
  // уровнем, иначе он просто исчез бы из кабинета.
  const byParent = new Map<string, any[]>()
  assessments.forEach((a: any) => {
    if (a.is_followup && a.parent_assessment_id) {
      const k = a.parent_assessment_id
      byParent.set(k, [...(byParent.get(k) ?? []), a])
    }
  })
  const ids = new Set(assessments.map((a: any) => a.id))
  const visible = assessments.filter((a: any) =>
    !a.is_followup || !a.parent_assessment_id || !ids.has(a.parent_assessment_id))

  // Единый список: Методы 1–3 в одном порядке по дате. Поиск по названию
  // компании для ассессментов делает сервер, портфели фильтруем здесь —
  // отдельного серверного поиска у Метода 3 нет.
  const q = query.trim().toLowerCase()
  const m3Visible = q
    ? m3.filter(p => `${p.company_name ?? ''} ${p.title ?? ''}`.toLowerCase().includes(q))
    : m3
  // Тип строки Методов 1 и 2 — Assessment, а не any: внутри карточки есть
  // обращения вида passed_contours.find(...), и на any они теряют вывод
  // типа параметра (TS7006).
  type Row =
    | { kind: 'a'; at: string; a: Assessment }
    | { kind: 'm3'; at: string; p: M3Portfolio }
  const rows: Row[] = [
    ...visible.map((a: Assessment) => ({ kind: 'a' as const, at: a.created_at, a })),
    ...m3Visible.map(p => ({ kind: 'm3' as const, at: m3RowDate(p), p })),
  ].sort((x, y) => new Date(y.at).getTime() - new Date(x.at).getTime())

  return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      {/* Навигация */}
      <nav style={S.nav}>
        <div style={S.navInner}>
          <div style={S.navLogo} onClick={() => router.push('/dashboard')}>
            <span style={S.logo64}>64</span><span style={S.logoDao}> ДАО</span>
          </div>
          <div style={S.navLinks}>
            <button style={{ ...S.navLink, ...S.navLinkOn }} onClick={() => router.push('/admin')}>Личный кабинет</button>
            {user?.role === 'admin' && (
              <button style={S.navLink} onClick={() => router.push('/admin/my-reports')}>Мои отчёты</button>
            )}
            <button style={S.navLink} onClick={() => router.push('/companies')}>Мои компании</button>
            <button style={S.navLink} onClick={() => router.push('/purchases')}>Мои покупки</button>
            <button style={S.navLink} onClick={() => router.push('/profile')}>Профиль</button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={S.navEmail}>{user?.email}</span>
            <div style={S.avatar}>{(user?.full_name || user?.email || 'U')[0].toUpperCase()}</div>
            <button style={S.navLogout} onClick={handleLogout}>Выйти</button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div style={S.hero}>
        <span style={S.labelRed}>Личный кабинет</span>
        <div style={S.heroBetween}>
          <div>
            <h1 style={S.heroH1}>Здравствуйте, {user?.full_name?.split(' ')[0] || user?.email}</h1>
            <p style={S.heroSub}>
              {completed.length > 0 || drafts.length > 0
                ? `У вас ${completed.length > 0 ? `${completed.length} готов${completed.length === 1 ? 'ый отчёт' : 'ых отчёта'}` : ''}${completed.length > 0 && drafts.length > 0 ? ' и ' : ''}${drafts.length > 0 ? `${drafts.length} черновик${drafts.length === 1 ? '' : 'а'}` : ''}. Завершите диагностику или начните новую.`
                : 'Начните первую диагностику, чтобы получить стратегию.'}
            </p>
          </div>
          <button style={S.btnPrimary} onClick={() => router.push('/assessment')}>
            + Новая диагностика
          </button>
        </div>
      </div>

      {/* Сетка */}
      <div className="dashboard-main-grid" style={S.grid}>
        <div>
          <div style={S.listHeader}>
            <span style={S.labelRed}>Мои отчёты</span>
            <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}>{rows.length} записей</span>
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
          {rows.length === 0 && query.trim() !== "" ? (
            <div className="dash-empty">
              <h3>Ничего не найдено</h3>
              <p>По запросу «{query}» диагностик нет. Проверьте название компании.</p>
            </div>
          ) : rows.length === 0 ? (
            <div style={S.emptyCard}>
              <div style={S.emptyHex}>䷿</div>
              <h3 style={S.emptyH3}>Пока нет диагностик</h3>
              <p style={S.emptyText}>Метод 1 — 6 вопросов о состоянии компании. Метод 2 — оценка 9 блоков бизнес-модели. Метод 3 — распределение ресурса между направлениями. Результат: PDF-отчёт.</p>
              {/* Список методов живёт на одном экране — /assessment.
                  Копия карточек здесь расходилась бы с ним при каждом
                  добавлении метода (это уже случилось с Методом 3). */}
              <button style={{ ...S.btnPrimary, marginTop: 6 }} onClick={() => router.push('/assessment')}>
                Выбрать метод диагностики →
              </button>
            </div>
          ) : (
            <div style={S.list}>
              {rows.map((row, i) => {
                if (row.kind === 'm3') {
                  return <M3ReportCard key={`m3-${row.p.id}`} p={row.p} n={i + 1} />
                }
                const a = row.a
                return (
                <div key={a.id} className="dash-card-mobile" style={{ ...S.card, cursor: (a.status === 'completed' || a.status === 'paid') ? 'pointer' : 'default' }}
                  onClick={() => (a.status === 'completed' || a.status === 'paid') && router.push(`/report/${a.id}`)}>
                  <div style={S.cardNum}>{String(i + 1).padStart(2, '0')}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={S.cardMeta}>
                      {new Date(a.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div style={S.cardTitle}>
                      {a.status === 'completed' || a.status === 'paid'
                        ? (isMethod2(a)
                            ? `Бизнес-модель · ${a.company_name || user?.company_name || '—'}`
                            : `Стратегическая диагностика · ${a.company_name || user?.company_name || '—'}`)
                        : 'Незавершённая диагностика'}
                    </div>
                    <div style={S.cardDetail}>
                      {a.reports.length > 0 ? `${a.reports.length} отчёт сформирован` : 'Отчёт формируется'}
                    </div>
                    <FollowupBadge a={a} />
                    <NestedFollowups items={byParent.get(a.id) ?? []} />
                    {a.finance_combination && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                        <span style={{ fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase' as const, fontWeight: 700, color: '#c0392b', background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.2)', borderRadius: 4, padding: '2px 8px' }}>
                          Финансовая функция
                        </span>
                        <span style={{ fontFamily: 'serif', fontSize: 20, color: '#1e3a8a', lineHeight: 1 }} title={`Текущая · ${a.finance_combination}`}>
                          {finChar(a.finance_combination)}
                        </span>
                        {typeof a.finance_result?.combination_resulting === 'string' && (
                          <>
                            <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)' }}>→</span>
                            <span style={{ fontFamily: 'serif', fontSize: 20, color: '#2d6a2d', lineHeight: 1 }} title={`Целевая · ${a.finance_result.combination_resulting}`}>
                              {finChar(a.finance_result.combination_resulting as string)}
                            </span>
                          </>
                        )}
                      </div>
                    )}
                    {(a.status === 'completed' || a.status === 'paid') && !isMethod2(a) && contours.some(c => c.enabled && c.contour !== 'finance') && (
                      <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(26,37,64,0.08)' }}>
                        <div style={{ fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)', fontWeight: 700, marginBottom: 6 }}>
                          Контуры диагностики
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 8, alignItems: 'center' }}>
                          {contours.filter(c => c.enabled && c.contour !== 'finance').map(c => {
                            const passed = (a.passed_contours || []).find(p => p.contour === c.contour)
                            return passed ? (
                              <span key={c.contour} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.6)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 4, padding: '3px 8px' }}>
                                {c.title}
                                <span style={{ fontFamily: 'serif', fontSize: 16, color: '#1e3a8a', lineHeight: 1 }} title={`Текущая · ${passed.combination}`}>
                                  {finChar(passed.combination)}
                                </span>
                              </span>
                            ) : (
                              <button key={c.contour} style={S.btnSoft}
                                onClick={e => { e.stopPropagation(); router.push(`/assessment/contour/${c.contour}?assessment=${a.id}`) }}>
                                {c.title} — пройти →
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="dash-card-actions-mobile" style={S.cardActions}>
                    <span style={a.status === 'completed' || a.status === 'paid' ? S.pillDone : S.pillDraft}>
                      {a.status === 'completed' || a.status === 'paid' ? 'Готов' : 'Черновик'}
                    </span>
                    {a.reports.length > 0 ? (
                      <a href={`/api/reports/${a.reports[0].id}/download`} target="_blank" rel="noreferrer"
                        style={S.btnGhost} onClick={e => e.stopPropagation()}>
                        Скачать PDF
                      </a>
                    ) : a.status === 'draft' ? (
                      <button style={S.btnSoft} onClick={e => { e.stopPropagation(); router.push('/assessment') }}>Продолжить →</button>
                    ) : (
                      <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)' }}>Генерация...</span>
                    )}
                    <button
                      style={{ ...S.btnGhost, color: '#c0392b', borderColor: 'rgba(192,57,43,0.25)' }}
                      onClick={e => { e.stopPropagation(); setConfirmId(a.id) }}
                    >Удалить</button>
                  </div>
                </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Сайдбар */}
        <aside style={S.side}>

          {/* Баннер доступных диагностик */}
          {credits > 0 ? (
            <div style={{
              background: 'linear-gradient(135deg, #1a4a3a 0%, #1e6347 100%)',
              border: '1px solid rgba(52,199,89,0.35)',
              borderRadius: 10, padding: '20px 22px', marginBottom: 16,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                <span style={{ fontSize: 18, color: 'rgba(52,199,89,0.9)' }}>✦</span>
                <span style={{ fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: 'rgba(52,199,89,0.9)', fontWeight: 700 }}>Доступно</span>
              </div>
              <div style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: '#fff', lineHeight: 1.1, marginBottom: 6 }}>
                {credits} {credits === 1 ? 'диагностика' : credits < 5 ? 'диагностики' : 'диагностик'}
              </div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(255,255,255,0.65)', lineHeight: 1.5, marginBottom: 16 }}>
                {grantCredits > 0
                  ? 'Доступ открыт без оплаты — тестовый период.'
                  : credits === 1 ? 'Одна оплаченная диагностика ожидает запуска.' : `${credits} оплаченных диагностики ожидают запуска.`}
              </div>
              {grantCredits > 0 && (
                <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(52,199,89,0.95)', lineHeight: 1.5, marginBottom: 16 }}>
                  Тестовый доступ: {grantCredits} из них{grantExpires ? `, действует до ${new Date(grantExpires).toLocaleDateString('ru-RU')}` : ''}.
                </div>
              )}
              <button
                style={{ background: 'rgba(52,199,89,0.15)', border: '1px solid rgba(52,199,89,0.5)', color: '#7fff9a', fontWeight: 600, width: '100%', padding: '10px 16px', borderRadius: 6, fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif' }}
                onClick={() => router.push('/assessment')}
              >
                Начать диагностику →
              </button>
            </div>
          ) : (
            <div style={{ background: 'rgba(26,37,64,0.04)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 10, padding: '16px 18px', marginBottom: 16 }}>
              <div style={{ fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)', fontWeight: 700, marginBottom: 6 }}>Доступно диагностик</div>
              <div style={{ fontFamily: 'Georgia,serif', fontSize: 24, color: 'rgba(26,37,64,0.35)', marginBottom: 4 }}>0</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)', lineHeight: 1.5 }}>Оплатите новую диагностику, чтобы получить доступ.</div>
            </div>
          )}

          <BuyDiagnostics m3Enabled={m3Enabled} />

          <SupportForm />
          <div style={S.sideCard}>
            <span style={{ ...S.labelRed, display: 'block', marginBottom: 10 }}>Статистика</span>
            <div style={S.statRow}><span style={S.statLabel}>Завершено</span><strong style={S.statVal}>{completed.length}</strong></div>
            <div style={S.statRow}><span style={S.statLabel}>В работе</span><strong style={S.statVal}>{drafts.length}</strong></div>
            <div style={S.statRow}><span style={S.statLabel}>Всего</span><strong style={S.statVal}>{assessments.length}</strong></div>
            <div style={{ ...S.statRow, marginBottom: 0, paddingTop: 8, borderTop: '1px solid rgba(26,37,64,0.08)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#1a6640', fontWeight: 700 }}>Доступно диагностик</span>
                <span
                  title="Здесь отображается количество оплаченных, но не использованных диагностик"
                  style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 14, height: 14, borderRadius: '50%', border: '1px solid rgba(26,37,64,0.25)', fontSize: 9, color: 'rgba(26,37,64,0.4)', cursor: 'help', flexShrink: 0, userSelect: 'none' as const }}
                >?</span>
              </span>
              <strong style={{ ...S.statVal, color: '#1a6640' }}>{credits}</strong>
            </div>
          </div>
          {user && (
            <div style={S.sideCard}>
              <span style={{ ...S.labelRed, display: 'block', marginBottom: 10 }}>Профиль</span>
              <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', marginBottom: 4, fontWeight: 500 }}>{user.full_name || '—'}</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginBottom: 8 }}>{user.company_name || 'Компания не указана'}</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}>{user.email}</div>
            </div>
          )}
        </aside>
      </div>
      {/* Диалог подтверждения удаления */}
      {confirmId && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setConfirmId(null)}>
          <div style={{ background: '#fff', borderRadius: 10, padding: '32px 36px', maxWidth: 400, width: '90%', boxShadow: '0 8px 40px rgba(0,0,0,0.18)' }}
            onClick={e => e.stopPropagation()}>
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 20, fontWeight: 400, color: '#1a2540', margin: '0 0 12px' }}>Удалить отчёт?</h3>
            <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.65)', lineHeight: 1.6, margin: '0 0 24px' }}>
              Диагностика и PDF-файл будут удалены безвозвратно.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button style={{ background: 'none', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#1a2540' }}
                onClick={() => setConfirmId(null)}>Отмена</button>
              <button style={{ background: '#c0392b', border: 'none', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#fff', fontWeight: 500, opacity: deletingId === confirmId ? 0.6 : 1 }}
                disabled={deletingId === confirmId}
                onClick={() => handleDelete(confirmId)}>
                {deletingId === confirmId ? 'Удаляем…' : 'Да, удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  nav: { background: '#cde3e3', borderBottom: '1px solid rgba(26,37,64,0.08)' },
  navInner: { maxWidth: 1200, margin: '0 auto', padding: '0 60px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 },
  navLogo: { display: 'flex', alignItems: 'baseline', cursor: 'pointer', flexShrink: 0 },
  logo64: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#c0392b' },
  logoDao: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#1a2540' },
  navLinks: { display: 'flex', gap: 4, flex: 1, justifyContent: 'center' },
  navLink: { background: 'none', border: 'none', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', cursor: 'pointer', padding: '6px 12px', borderRadius: 5 },
  navLinkOn: { background: 'rgba(26,37,64,0.08)', color: '#1a2540' },
  navEmail: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.55)' },
  navLogout: { background: 'none', border: 'none', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', cursor: 'pointer', padding: 0 },
  avatar: { width: 32, height: 32, borderRadius: '50%', background: '#1a2540', color: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Georgia,serif', fontSize: 14, flexShrink: 0 },
  hero: { padding: '48px 60px 24px', maxWidth: 1200, margin: '0 auto' },
  heroBetween: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 8, gap: 24, flexWrap: 'wrap' as const },
  heroH1: { fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', margin: '0 0 6px' },
  heroSub: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', lineHeight: 1.6, margin: 0 },
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 },
  grid: { maxWidth: 1200, margin: '0 auto', padding: '0 60px 60px', display: 'grid', gridTemplateColumns: '1fr 320px', gap: 32 },
  listHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  list: { display: 'flex', flexDirection: 'column', gap: 14 },
  card: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '22px 26px', display: 'grid', gridTemplateColumns: '34px 90px 1fr auto', gap: 18, alignItems: 'center' },
  cardNum: { fontFamily: 'Georgia,serif', fontSize: 22, color: '#c0392b', textAlign: 'center' as const, lineHeight: '1' },
  cardHex: { fontFamily: 'monospace', fontSize: 13, color: '#1e3a8a', textAlign: 'center' as const, letterSpacing: 2, fontWeight: 700 },
  cardMeta: { fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', letterSpacing: 1, textTransform: 'uppercase' as const, marginBottom: 6 },
  cardTitle: { fontFamily: 'Georgia,serif', fontSize: 17, color: '#1a2540', marginBottom: 4, fontWeight: 400 },
  cardDetail: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.5 },
  cardActions: { display: 'flex', flexDirection: 'column' as const, alignItems: 'flex-end', gap: 8 },
  pillDone: { fontFamily: 'sans-serif', fontSize: 11, padding: '3px 10px', borderRadius: 20, background: '#dcfce7', color: '#166534', fontWeight: 500 },
  pillDraft: { fontFamily: 'sans-serif', fontSize: 11, padding: '3px 10px', borderRadius: 20, background: '#f1f5f9', color: '#475569', fontWeight: 500 },
  emptyCard: { background: 'rgba(255,255,255,0.65)', border: '1px dashed rgba(26,37,64,0.2)', borderRadius: 10, padding: '60px 40px', textAlign: 'center' as const },
  emptyHex: { fontSize: 52, color: '#1e3a8a', marginBottom: 18, display: 'block', fontFamily: 'serif' },
  emptyH3: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, marginBottom: 8, color: '#1a2540' },
  emptyText: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', maxWidth: 360, margin: '0 auto 22px', lineHeight: 1.6 },
  methodCard: { background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '20px 22px', cursor: 'pointer' as const },
  methodH3: { fontFamily: 'Georgia,serif', fontSize: 17, fontWeight: 400, color: '#1a2540', margin: '0 0 8px' },
  methodDesc: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)', lineHeight: 1.6, margin: '0 0 14px' },
  methodFoot: { display: 'flex', justifyContent: 'space-between', paddingTop: 12, borderTop: '1px solid rgba(26,37,64,0.06)' },
  methodTime: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' },
  methodGo: { fontFamily: 'sans-serif', fontSize: 13, color: '#1e3a8a', fontWeight: 500 },
  side: { display: 'flex', flexDirection: 'column' as const, gap: 18 },
  sideCard: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: 22 },
  sideText: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.6, margin: '0 0 12px' },
  statRow: { display: 'flex', justifyContent: 'space-between', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 8 },
  statLabel: { color: 'rgba(26,37,64,0.6)' },
  statVal: { color: '#1a2540', fontFamily: 'Georgia,serif', fontSize: 15 },
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '11px 22px', fontFamily: 'sans-serif', fontSize: 14, fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap' as const },
  btnGhost: { background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '7px 14px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer', textDecoration: 'none', display: 'inline-block' },
  btnSoft: { background: 'rgba(26,37,64,0.06)', color: '#1a2540', border: 'none', borderRadius: 6, padding: '7px 14px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' },
  supportInput: { width: '100%', padding: '8px 12px', background: 'rgba(255,255,255,0.9)', border: '1px solid rgba(26,37,64,0.15)', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, outline: 'none', color: '#1a2540', boxSizing: 'border-box' as const },
}

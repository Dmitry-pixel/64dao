'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getMe, getAssessment, getBaseQuestions, reportDownloadUrl, listContours, getCompanies, isMethod2, type AuthUser, type Assessment, type ContourInfo, type Company } from '@/lib/api'
import { HEXAGRAM_MAP } from '@/lib/hexagrams'
import { TargetHexagramBlock } from '@/components/TargetHexagramBlock'
import HexDiagram, { HexLines, StratagemaTable } from '@/components/HexDiagram'
import ContourReportSection from '@/components/ContourReportSection'
import ContourSummaryCard from '@/components/ContourSummaryCard'
import CompanyLifecycleSection from '@/components/CompanyLifecycleSection'

const API = process.env.NEXT_PUBLIC_API_URL || ''


// combo → unicode hexagram character (U+4DC0 + n - 1)
function comboToChar(combo: string): string {
  const entry = HEXAGRAM_MAP[combo]
  if (!entry) return ''
  return String.fromCodePoint(0x4DC0 + entry.n - 1)
}

// Returns target hexagram info or null
// Русские метки для сценария стратагемы
const SCENARIO_LABELS: [string, string][] = [
  ['innovation_strategy',   'Стратегия изменений'],
  ['innovation_type',       'Тип изменений'],
  ['value_discipline',      'Ценностная дисциплина'],
  ['leadership_principles', 'Принципы лидерства'],
  ['growth_strategy',       'Стратегия роста'],
  ['focus',                 'Фокус'],
]

// Тексты вопросов приходят с сервера (/api/method1/base-questions) — правятся в админке.

const FIN_STATE_RU: Record<string, string> = {
  young_yang: 'Ян — устойчивая сильная позиция',
  old_yang: 'Ян, подвижная — сила на пике',
  young_yin: 'Инь — устойчивая слабая позиция',
  old_yin: 'Инь, подвижная — изменение назрело',
}

const FIN_LINE_TITLES: Record<number, string> = {
  1: 'Текущие финансовые процессы', 2: 'Технологии и системы', 3: 'Навыки и возможности команды',
  4: 'Поддержка руководства', 5: 'Внешние и смежные факторы', 6: 'Видение и стратегия трансформации',
}

// ─────────────────────────────────────────────────────────────────────────────

export default function ReportPage() {
  const router = useRouter()
  const params = useParams()
  const assessmentId = params.id as string
  const [user, setUser] = useState<AuthUser | null>(null)
  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [contours, setContours] = useState<ContourInfo[]>([])

  useEffect(() => {
    listContours().then(r => setContours(r.contours)).catch(() => setContours([]))
  }, [])
  const [strategy, setStrategy] = useState<any>(null)
  const [finReport, setFinReport] = useState<any>(null)
  const [finStrategy, setFinStrategy] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState(0)
  const [dynCompany, setDynCompany] = useState<Company | null>(null)
  const [baseQ, setBaseQ] = useState<{ q: string; a: string; b: string }[]>([])

  // Вопросы редактируются в админке — тянем актуальные, а не вшитые в сборку.
  useEffect(() => {
    let cancelled = false
    getBaseQuestions()
      .then(d => { if (!cancelled) setBaseQ(d.questions.map(x => ({ q: x.q, a: x.a, b: x.b }))) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    Promise.all([getMe(), getAssessment(assessmentId)])
      .then(([u, a]) => {
        setUser(u)
        setAssessment(a)
        const isMethod2Only = isMethod2(a)
        if (!isMethod2Only && a.company_name) {
          getCompanies()
            .then(cs => {
              const c = cs.find(x => x.name === a.company_name)
              if (c && c.assessment_count >= 2) setDynCompany(c)
            })
            .catch(() => {})
        }
        if (a.method1_combination && !isMethod2Only) {
          fetch(`${API}/api/strategies/${a.method1_combination}`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(s => setStrategy(s))
            .catch(() => {})
        }
        if (a.finance_combination) {
          fetch(`${API}/api/assessments/${assessmentId}/finance-interpretation`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(fr => {
              if (fr && fr.has_finance) {
                setFinReport(fr)
                fetch(`${API}/api/strategies/${fr.finance_combination}`, { credentials: 'include' })
                  .then(r => r.ok ? r.json() : null).then(fs => setFinStrategy(fs)).catch(() => {})
              }
            })
            .catch(() => {})
        }
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router, assessmentId])

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка...</p>
    </div>
  )

  if (!assessment) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Отчёт не найден</p>
    </div>
  )

  const combo = assessment.method1_combination || '??????'
  const hasReport = assessment.reports.length > 0
  const method2 = assessment.method2_data
  const isMethod2Only = isMethod2(assessment)
  const companyName = assessment.company_name || user?.company_name || 'Компания'

  const hexChar = comboToChar(combo)
  const hexInfo = HEXAGRAM_MAP[combo]

  const BMC_NAMES = [
    'Ценностное предложение', 'Отношения с клиентами', 'Ключевые ресурсы',
    'Потоки доходов', 'Ключевые партнёры', 'Сегменты клиентов',
    'Ключевые активности', 'Каналы', 'Структура издержек',
  ]

  const BMC_HELP: Record<string, string> = {
    'Ценностное предложение': 'Какую конкретную пользу клиент получает? Чем вы отличаетесь от альтернатив?',
    'Отношения с клиентами': 'Какие связи компания выстраивает: персональные, самообслуживание, сообщество?',
    'Ключевые ресурсы': 'Какие активы, люди, технологии и капитал необходимы для работы?',
    'Потоки доходов': 'Как компания зарабатывает: продажи, подписка, лицензии, комиссии?',
    'Ключевые партнёры': 'Кто помогает компании создавать и доставлять ценность? Какие альянсы и поставщики критичны?',
    'Сегменты клиентов': 'Кто ваш клиент? Существует ли несколько сегментов с разными потребностями?',
    'Ключевые активности': 'Что компания делает каждый день, чтобы создавать ценность для клиента?',
    'Каналы': 'Через какие каналы клиенты узнают о продукте и получают его?',
    'Структура издержек': 'Какие затраты ключевые? Постоянные или переменные? На чём фокус?',
  }



  const lc = finReport?.summary?.company_lifecycle
  const hasLc = !!lc
  const finNo = hasLc ? '04' : '03'
  const sumNo = hasLc ? '05' : '04'

  const sections = isMethod2Only
    ? ['01 — Бизнес-модель (9 блоков)']
    : [
        '01 — Текущее состояние',
        '02 — Сценарий стратагемы',
        ...(hasLc ? ['03 — Жизненный цикл компании'] : []),
        ...(finReport?.has_finance ? [`${finNo} — Финансовая функция`] : []),
        ...(finReport?.summary ? [`${sumNo} — Сводная карта контуров`] : []),
        ...((finReport?.contours || []).map((c: any, ci: number) => `${String((hasLc ? 6 : 5) + ci).padStart(2, '0')} — ${c.title}`)),
      ]

  // Дата с временем
  const createdAt = new Date(assessment.created_at).toLocaleString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })

  return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      {/* Навигация */}
      <nav style={S.nav}>
        <div style={S.navInner}>
          <div style={S.navLogo} onClick={() => router.push(user?.role === 'admin' ? '/admin' : '/dashboard')}>
            <span style={S.logo64}>64</span><span style={S.logoDao}> ДАО</span>
          </div>
          <div style={S.navLinks}>
            {user?.role === 'admin' ? (
              <button style={{ ...S.navLink, ...S.navLinkOn }} onClick={() => router.push('/admin')}>Админ-панель</button>
            ) : (
              <button style={{ ...S.navLink, ...S.navLinkOn }} onClick={() => router.push('/dashboard')}>Мои отчёты</button>
            )}
            <button style={S.navLink} onClick={() => router.push('/assessment')}>Новая диагностика</button>
            <button style={S.navLink} onClick={() => router.push('/profile')}>Профиль</button>
          </div>
          <div style={S.navUser}>
            <span style={S.navEmail}>{user?.email}</span>
            <div style={S.avatar}>{(user?.full_name || user?.email || 'U')[0].toUpperCase()}</div>
          </div>
        </div>
      </nav>

      {/* Панель действий */}
      <div style={S.actions}>
        <button style={S.backBtn} onClick={() => router.push(user?.role === 'admin' ? '/admin/my-reports' : '/dashboard')}>← Все отчёты</button>
        <div style={{ flex: 1 }} />
        <button style={{ ...S.btnPrimary, background: 'transparent', color: '#1a2540', border: '1px solid rgba(26,37,64,0.25)', marginRight: 10 }} onClick={() => router.push(`/report/${assessmentId}/checklist`)}>
          Чек-лист действий
        </button>
        {hasReport && (
          <a href={reportDownloadUrl(assessment.reports[0].id)} target="_blank" rel="noreferrer" style={S.btnPrimary}>
            ↓ Скачать PDF
          </a>
        )}
      </div>

      {/* Апсейл: динамика компании (≥2 диагностик) */}
      {dynCompany && (
        <div style={S.dynUpsell}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <span style={S.labelRed}>Динамика</span>
            <div style={S.dynUpsellTitle}>По компании «{dynCompany.name}» накоплено {dynCompany.assessment_count} диагностик</div>
            <div style={S.dynUpsellText}>
              Сравните контуры во времени: что усилилось, где просадка, куда смещается фокус.
            </div>
          </div>
          <button style={S.dynUpsellBtn} onClick={() => router.push(`/companies/${dynCompany.id}/dynamics`)}>
            Открыть «Динамику» →
          </button>
        </div>
      )}

      {/* Основная сетка */}
      <div style={S.reportShell}>
        {/* Оглавление */}
        <aside style={S.toc}>
          <h4 style={S.tocTitle}>Содержание</h4>
          {sections.map((s, i) => (
            <a key={i} style={{ ...S.tocLink, ...(i === activeSection ? S.tocLinkOn : {}) }} onClick={() => setActiveSection(i)}>{s}</a>
          ))}
        </aside>

        {/* Тело отчёта */}
        <div style={S.reportBody}>
          {/* Обложка */}
          <div style={S.cover}>
            <div>
              <span style={S.labelRed}>{isMethod2Only ? 'Бизнес-модель 64 ДАО' : 'Стратегический отчёт 64 ДАО'}</span>
              {/* Заголовок совпадает с PDF (app/pdf.py, cover_title): в вебе
                  в h1 попадало strategy.title, то есть название стратегии, и
                  «Стратегический профиль компании» не выводилось никогда —
                  у опубликованной комбинации title заполнен всегда.
                  Название стратегии не теряем: оно уходит подзаголовком. */}
              <h1 style={S.coverH1}>
                {isMethod2Only
                  ? `Бизнес-модель · ${companyName}`
                  : 'Стратегический профиль компании'}
              </h1>
              {!isMethod2Only && strategy?.title && (
                <div style={S.coverSub}>{strategy.title}</div>
              )}
              <div style={S.coverMeta}>
                {companyName}<br />
                Подготовлен {createdAt}
              </div>
              {!isMethod2Only && hexInfo && (
                <div style={{ marginTop: 8 }}>
                  <span style={{ ...S.labelRed, marginRight: 8 }}>Гексаграмма {hexInfo.n}</span>
                  <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)' }}>{hexInfo.name}</span>
                </div>
              )}
            </div>
            <div style={{ textAlign: 'center' as const }}>
              <div style={S.hexXl}>{isMethod2Only ? '䷿' : (hexChar || '?')}</div>
              {!isMethod2Only && <div style={S.combBadge}>{combo}</div>}
            </div>
          </div>

          {/* ── МЕТОД 2: только бизнес-модель ── */}
          {isMethod2Only && method2 && (
            <div style={S.section} id="s0">
              <h2 style={S.sectionH2}><span style={S.num}>01</span>Бизнес-модель (9 блоков)</h2>
              <p style={S.muted}>Сводка по 9 блокам с вашими оценками и комментариями.</p>
              <div>
                {BMC_NAMES.map((name, i) => {
                  const data = method2[name] as any
                  if (!data) return null
                  return (
                    <div key={name} style={S.bmcRow}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 16, alignItems: 'flex-start' }}>
                        <div style={S.bmcRowTitle}>{i + 1}. {name}</div>
                        <div style={{ display: 'flex', gap: 3, justifyContent: 'flex-end', alignItems: 'center' }}>
                          {data.score ? (
                            Array.from({ length: 5 }, (_, j) => (
                              <div key={j} style={{ width: 14, height: 6, borderRadius: 99, background: j < data.score ? '#1e3a8a' : 'rgba(26,37,64,0.08)' }} />
                            ))
                          ) : (
                            <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', fontStyle: 'italic' as const }}>Не оценено</span>
                          )}
                        </div>
                      </div>
                      {BMC_HELP[name] && (
                        <div style={{ fontFamily: 'sans-serif', fontSize: 12.5, color: 'rgba(26,37,64,0.55)', lineHeight: 1.5, marginTop: 6 }}>
                          {BMC_HELP[name]}
                        </div>
                      )}
                      {data.text && (
                        <div style={S.bmcComment}>
                          <span style={{ ...S.labelRed, display: 'block', marginBottom: 8, fontSize: 10 }}>Комментарий</span>
                          <span style={{ fontFamily: 'Georgia,serif', fontSize: 15, color: '#1a2540', fontStyle: 'italic', lineHeight: 1.7, display: 'block' }}>{data.text}</span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* ── МЕТОД 1: стратегия ── */}
          {!isMethod2Only && (<>

            {/* Секция 01 — Текущее состояние */}
            <div style={S.section} id="s0">
              <h2 style={S.sectionH2}><span style={S.num}>01</span>Текущее состояние</h2>
              <p style={S.muted}>Параметры, которые система определила по вашим ответам.</p>
              <div style={{ background: 'rgba(26,37,64,0.03)', borderRadius: 6, padding: '14px 18px' }}>
                <span style={S.labelRed}>Стратагема</span>
                <div style={S.stateVal}>{strategy?.stratagema_title || <em style={{ opacity: 0.4, fontSize: 14 }}>Не заполнено</em>}</div>
              </div>

              <HexDiagram
                combo={combo}
                questions={baseQ}
                labels={SCENARIO_LABELS}
                scenario={strategy?.scenario}
              />

              <StratagemaTable labels={SCENARIO_LABELS} scenario={strategy?.scenario} />
            </div>


            {/* Секция 02 — Сценарий стратагемы */}
            <div style={S.section} id="s4">
              <h2 style={S.sectionH2}><span style={S.num}>02</span>Сценарий стратагемы</h2>
              <TargetHexagramBlock strategy={strategy} labelStyle={S.labelRed} />

              {/* Описание перехода */}
              <div style={{ marginBottom: 20 }}>
                <span style={S.labelRed}>Описание перехода</span>
                <div style={{ ...S.reportText, marginTop: 8 }}>
                  {strategy?.transition_description
                    ? strategy.transition_description.split('\n').map((p: string, i: number) => <p key={i} style={{ marginBottom: 14 }}>{p}</p>)
                    : <p style={S.muted}>Описание перехода будет добавлено при публикации стратегии.</p>}
                </div>
              </div>

            </div>

            {/* ── Жизненный цикл компании (раздел 03, перед финансами) ── */}
            {hasLc && (
              <CompanyLifecycleSection sectionNo="03" lc={lc} summary={finReport.summary} styles={S} />
            )}

            {/* ── Финансовая функция, сводная карта, контуры ── */}
            {finReport?.has_finance && (
              <ContourReportSection
                sectionNo={finNo}
                title="Финансовая функция"
                anchorId="sf"
                result={finReport.finance_result}
                interp={finReport.interpretation}
                lineTitles={finReport.line_titles}
                styles={S}
              >
                {finStrategy && (<>
                  {finStrategy.stratagema_title && (
                    <div style={{ marginTop: 12, padding: '12px 16px', borderRadius: 6, background: 'rgba(30,58,138,0.08)', border: '1px solid rgba(30,58,138,0.2)', color: '#1e3a8a', fontFamily: 'sans-serif', fontSize: 13, lineHeight: 1.6 }}>{finStrategy.stratagema_title}</div>
                  )}
                  <div style={{ marginTop: 16 }}>
                    <div style={{ fontSize: 10, color: '#c0392b', letterSpacing: 2, textTransform: 'uppercase' as const, fontFamily: 'sans-serif', fontWeight: 700, marginBottom: 8 }}>Сценарий развития</div>
                    <div style={S.reportText}>{finStrategy.scenario_text ? finStrategy.scenario_text.split('\n').map((pp: string, i: number) => <p key={i} style={{ marginBottom: 14 }}>{pp}</p>) : <em style={{ opacity: 0.4 }}>Не заполнено</em>}</div>
                  </div>
                </>)}
              </ContourReportSection>
            )}

            {finReport?.summary && (
              <ContourSummaryCard sectionNo={sumNo} summary={finReport.summary} styles={S} />
            )}

            {(finReport?.contours || []).map((c: any, ci: number) => (
              <ContourReportSection
                key={c.contour}
                sectionNo={String((hasLc ? 6 : 5) + ci).padStart(2, '0')}
                title={c.title}
                anchorId={`s-${c.contour}`}
                result={c.result}
                interp={c.interp}
                lineTitles={c.line_titles}
                styles={S}
              />
            ))}

            {/* Дополнение диагностики контурами */}
            {!isMethod2Only && (() => {
              const passed = new Set((assessment.passed_contours || []).map(p => p.contour))
              const avail = contours.filter(c => c.enabled && c.contour !== 'finance' && !passed.has(c.contour))
              if (avail.length === 0) return null
              const passedExtra = contours.filter(c => c.contour !== 'finance' && passed.has(c.contour)).length
              return (
                <div style={S.section}>
                  <span style={S.labelRed}>Дополнение диагностики</span>
                  <h2 style={{ fontFamily: 'Georgia,serif', fontSize: 24, fontWeight: 400, color: '#1a2540', margin: '10px 0 12px' }}>
                    Диагностика может быть дополнена
                  </h2>
                  <p style={{ ...S.reportText, marginBottom: 12 }}>
                    Этот отчёт описывает зрелость финансовой функции. Остальные контуры не повторяют
                    её, а достраивают картину: каждый оценивает свою функцию по той же шкале и даёт
                    собственную гексаграмму с приоритетами.
                  </p>
                  <p style={{ ...S.reportText, marginBottom: 16 }}>
                    {passedExtra === 0
                      ? 'Со второго пройденного контура в отчёте появится сводная карта — сравнение зрелости функций между собой и указание на то, какая из них сдерживает остальные.'
                      : 'Каждый следующий контур уточняет сводную карту и делает вывод о системном ограничении устойчивее.'}
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 10 }}>
                    {avail.map(c => (
                      <button key={c.contour}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px', background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' }}
                        onClick={() => router.push(`/assessment/contour/${c.contour}?assessment=${assessment.id}`)}>
                        {c.title} →
                      </button>
                    ))}
                  </div>
                  <p style={{ ...S.faint, marginTop: 12 }}>
                    24 утверждения, около 10 минут на контур. Дополнительная оплата не требуется.
                  </p>
                </div>
              )
            })()}


          </>)}
        </div>
      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  nav: { background: '#cde3e3', borderBottom: '1px solid rgba(26,37,64,0.08)' },
  navInner: { maxWidth: 1200, margin: '0 auto', padding: '0 60px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 },
  navLogo: { display: 'flex', alignItems: 'baseline', cursor: 'pointer', flexShrink: 0 },
  logo64: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#c0392b' },
  logoDao: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#1a2540' },
  navLinks: { display: 'flex', gap: 4 },
  navLink: { background: 'none', border: 'none', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', cursor: 'pointer', padding: '6px 12px', borderRadius: 5 },
  navLinkOn: { background: 'rgba(26,37,64,0.08)', color: '#1a2540' },
  navUser: { display: 'flex', alignItems: 'center', gap: 10 },
  navEmail: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.55)' },
  avatar: { width: 32, height: 32, borderRadius: '50%', background: '#1a2540', color: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Georgia,serif', fontSize: 14 },
  actions: { maxWidth: 1200, margin: '0 auto', padding: '16px 60px', display: 'flex', alignItems: 'center', gap: 12 },
  dynUpsell: { maxWidth: 1200, margin: '0 auto 8px', padding: '18px 28px', display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' as const, background: 'linear-gradient(135deg, #1a4a3a 0%, #1e6347 100%)', border: '1px solid rgba(52,199,89,0.35)', borderRadius: 10 },
  dynUpsellTitle: { fontFamily: 'Georgia,serif', fontSize: 19, fontWeight: 400, color: '#fff', margin: '6px 0 6px', lineHeight: 1.25 },
  dynUpsellText: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(255,255,255,0.75)', lineHeight: 1.55, margin: 0, maxWidth: 620 },
  dynUpsellBtn: { background: 'rgba(52,199,89,0.15)', border: '1px solid rgba(52,199,89,0.5)', color: '#7fff9a', fontWeight: 600, padding: '11px 20px', borderRadius: 6, fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif', whiteSpace: 'nowrap' as const },
  backBtn: { background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(26,37,64,0.6)', fontFamily: 'sans-serif', fontSize: 12 },
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', textDecoration: 'none', display: 'inline-block' },
  reportShell: { maxWidth: 1200, margin: '0 auto', padding: '0 60px 60px', display: 'grid', gridTemplateColumns: '200px 1fr', gap: 32 },
  toc: { position: 'sticky' as const, top: 24, alignSelf: 'flex-start' as const },
  tocTitle: { fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 1, color: 'rgba(26,37,64,0.4)', textTransform: 'uppercase' as const, marginBottom: 12, fontWeight: 600 },
  tocLink: { display: 'block', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.5)', padding: '6px 10px', borderRadius: 4, cursor: 'pointer', marginBottom: 2, textDecoration: 'none' },
  tocLinkOn: { background: 'rgba(26,37,64,0.06)', color: '#1a2540' },
  reportBody: { display: 'flex', flexDirection: 'column' as const, gap: 0 },
  cover: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '36px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 },
  coverH1: { fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', margin: '8px 0 12px' },
  coverSub: { fontFamily: 'Georgia,serif', fontSize: 19, fontWeight: 400, color: 'rgba(26,37,64,0.7)', margin: '-4px 0 12px' },
  coverMeta: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.7 },
  hexXl: { fontFamily: 'serif', fontSize: 64, color: '#1e3a8a', lineHeight: 1 },
  combBadge: { fontFamily: 'monospace', fontSize: 13, color: 'rgba(26,37,64,0.5)', letterSpacing: 3, marginTop: 8 },
  section: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '28px 32px', marginBottom: 16 },
  sectionH2: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, color: '#1a2540', margin: '0 0 16px', display: 'flex', alignItems: 'baseline', gap: 12 },
  // Номер раздела — плашка: верхнеуровневые разделы должны читаться как
  // оглавление на просмотре по диагонали. alignSelf перекрывает baseline
  // родителя, иначе подложка съезжает вниз относительно заголовка.
  num: { fontFamily: 'sans-serif', fontSize: 13, fontWeight: 500, color: '#fff',
         background: '#c0392b', borderRadius: 4, padding: '5px 9px',
         letterSpacing: 1, flexShrink: 0, alignSelf: 'center' },
  muted: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.5)', lineHeight: 1.6, marginBottom: 16 },
  faint: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' },
  stateGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 },
  stateCell: { background: 'rgba(26,37,64,0.03)', borderRadius: 6, padding: '14px 18px' },
  stateVal: { fontFamily: 'Georgia,serif', fontSize: 17, color: '#1a2540', marginTop: 6 },
  scenarioTable: { marginTop: 16 },
  scenarioHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 },
  th: { padding: '10px 14px', textAlign: 'left' as const, fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', borderBottom: '1px solid rgba(26,37,64,0.08)', fontWeight: 500 },
  td: { padding: '12px 14px', fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', borderBottom: '1px solid rgba(26,37,64,0.06)' },
  reportText: { fontFamily: 'Georgia,serif', fontSize: 16, lineHeight: 1.8, color: '#1a2540' },
  bmcRow: { padding: '18px 0', borderBottom: '1px solid rgba(26,37,64,0.06)' },
  bmcRowTitle: { fontFamily: 'Georgia,serif', fontSize: 15, color: '#1a2540' },
  bmcComment: { marginTop: 14, padding: '18px 22px', background: 'rgba(30,58,138,0.05)', border: '1px solid rgba(30,58,138,0.12)', borderRadius: 6 },
  transitionCard: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '20px 28px', marginTop: 18, display: 'flex', alignItems: 'center', gap: 24 },
  hexLg: { fontFamily: 'serif', fontSize: 40, color: '#1e3a8a', lineHeight: 1 },
  transitionLabel: { position: 'absolute' as const, top: -10, left: '50%', transform: 'translateX(-50%)', background: '#e8e4db', padding: '0 10px', fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', letterSpacing: 2, textTransform: 'uppercase' as const, whiteSpace: 'nowrap' as const },
}

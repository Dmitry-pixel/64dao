'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getMe, getAssessment, reportDownloadUrl, type AuthUser, type Assessment } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function ReportPage() {
  const router = useRouter()
  const params = useParams()
  const assessmentId = params.id as string
  const [user, setUser] = useState<AuthUser | null>(null)
  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [strategy, setStrategy] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState(0)

  useEffect(() => {
    Promise.all([getMe(), getAssessment(assessmentId)])
      .then(([u, a]) => {
        setUser(u)
        setAssessment(a)
        if (a.method1_combination) {
          fetch(`${API}/api/strategies/${a.method1_combination}`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(s => setStrategy(s))
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

  const BMC_NAMES = [
    'Ключевые партнёры', 'Ключевые активности', 'Ключевые ресурсы',
    'Ценностное предложение', 'Отношения с клиентами', 'Каналы',
    'Сегменты клиентов', 'Структура издержек', 'Потоки доходов',
  ]

  const sections = [
    '01 — Текущее состояние',
    '02 — Стадия жизненного цикла',
    '03 — Сценарий развития',
    '04 — Предположения',
    ...(method2 ? ['05 — Бизнес-модель'] : []),
    '06 — Целевой сценарий',
  ]

  return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      {/* Навигация */}
      <nav style={S.nav}>
        <div style={S.navInner}>
          <div style={S.navLogo} onClick={() => router.push('/dashboard')}>
            <span style={S.logo64}>64</span><span style={S.logoDao}> ДАО</span>
          </div>
          <div style={S.navLinks}>
            <button style={{ ...S.navLink, ...S.navLinkOn }} onClick={() => router.push('/dashboard')}>Мои отчёты</button>
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
        <button style={S.backBtn} onClick={() => router.push('/dashboard')}>← Все отчёты</button>
        <div style={{ flex: 1 }} />
        {hasReport && (
          <a href={reportDownloadUrl(assessment.reports[0].id)} target="_blank" rel="noreferrer" style={S.btnPrimary}>
            ↓ Скачать PDF
          </a>
        )}
      </div>

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
              <span style={S.labelRed}>Стратегический отчёт 64 ДАО</span>
              <h1 style={S.coverH1}>{strategy?.title || `Стратегия ${combo}`}</h1>
              <div style={S.coverMeta}>
                {user?.company_name && <>{user.company_name} · </>}{user?.full_name}<br />
                Подготовлен {new Date(assessment.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}
              </div>
            </div>
            <div style={{ textAlign: 'center' as const }}>
              <div style={S.hexXl}>䷖</div>
              <div style={S.combBadge}>{combo}</div>
            </div>
          </div>

          {/* Секция 01 — Текущее состояние */}
          <div style={S.section} id="s0">
            <h2 style={S.sectionH2}><span style={S.num}>01</span>Текущее состояние</h2>
            <p style={S.muted}>Три параметра, которые система определила по вашим ответам.</p>
            <div style={S.stateGrid}>
              <div style={S.stateCell}>
                <span style={S.labelRed}>Стратагема</span>
                <div style={S.stateVal}>{strategy?.stratagema_title || '—'}</div>
              </div>
              <div style={S.stateCell}>
                <span style={S.labelRed}>Стадия</span>
                <div style={S.stateVal}>{strategy?.lifecycle_stage || '—'}</div>
              </div>
              <div style={S.stateCell}>
                <span style={S.labelRed}>Комбинация</span>
                <div style={{ ...S.stateVal, fontFamily: 'monospace', letterSpacing: 3 }}>{combo}</div>
              </div>
            </div>
            {strategy?.scenario && (
              <div style={S.scenarioTable}>
                <div style={S.scenarioHead}>
                  <span style={S.labelRed}>Сценарий стратагемы</span>
                  <span style={S.faint}>Правая колонка зависит от вашей текущей гексаграммы ({combo})</span>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 14 }}>
                  <thead>
                    <tr>
                      <th style={S.th}>Описание</th>
                      <th style={S.th}>Действие</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(strategy.scenario).map(([key, val]: [string, any]) => (
                      <tr key={key}>
                        <td style={S.td}>{key}</td>
                        <td style={S.td}>{val}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Секция 02 — Жизненный цикл */}
          <div style={S.section} id="s1">
            <h2 style={S.sectionH2}><span style={S.num}>02</span>Жизненный цикл</h2>
            <div style={S.reportText}>
              {strategy?.lifecycle_description
                ? <p>{strategy.lifecycle_description}</p>
                : <p style={S.muted}>Описание стадии жизненного цикла будет добавлено при публикации стратегии.</p>
              }
            </div>
          </div>

          {/* Секция 03 — Сценарий развития */}
          <div style={S.section} id="s2">
            <h2 style={S.sectionH2}><span style={S.num}>03</span>Сценарий развития</h2>
            <div style={S.reportText}>
              {strategy?.scenario_text
                ? strategy.scenario_text.split('\n').map((p: string, i: number) => <p key={i} style={{ marginBottom: 14 }}>{p}</p>)
                : <p style={S.muted}>Текст сценария будет добавлен при публикации стратегии.</p>
              }
            </div>
          </div>

          {/* Секция 04 — Предположения */}
          <div style={S.section} id="s3">
            <h2 style={S.sectionH2}><span style={S.num}>04</span>Предположения. Связи с будущим</h2>
            <p style={S.muted}>Рекомендации по ключевым блокам для данного сценария.</p>
            {strategy?.current_state ? (
              <div style={S.assumptionsGrid}>
                {Object.entries(strategy.current_state).map(([cat, text]: [string, any], i) => (
                  <div key={cat} style={S.assumption}>
                    <div style={S.assumptionHead}>
                      <span style={S.numMini}>{String(i + 1).padStart(2, '0')}</span>
                      <h3 style={S.assumptionH3}>{cat}</h3>
                    </div>
                    <p style={S.assumptionBody}>{text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p style={S.muted}>Предположения будут добавлены при публикации стратегии.</p>
            )}
          </div>

          {/* Секция 05 — Бизнес-модель (если есть) */}
          {method2 && (
            <div style={S.section} id="s4">
              <h2 style={S.sectionH2}><span style={S.num}>05</span>Бизнес-модель (Метод 2)</h2>
              <p style={S.muted}>Сводка по 9 блокам с вашими оценками и комментариями.</p>
              <div>
                {BMC_NAMES.map((name, i) => {
                  const data = method2[name] as any
                  if (!data) return null
                  return (
                    <div key={name} style={S.bmcRow}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 16, alignItems: 'flex-start' }}>
                        <div>
                          <div style={S.bmcRowTitle}>{i + 1}. {name}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 3, justifyContent: 'flex-end', alignItems: 'center' }}>
                          {Array.from({ length: 5 }, (_, j) => (
                            <div key={j} style={{ width: 14, height: 6, borderRadius: 99, background: j < data.score ? '#1e3a8a' : 'rgba(26,37,64,0.08)' }} />
                          ))}
                        </div>
                      </div>
                      {data.text && (
                        <div style={S.bmcComment}>
                          <span style={{ ...S.labelRed, display: 'block', marginBottom: 8, fontSize: 10 }}>Комментарий из диагностики</span>
                          <span style={{ fontFamily: 'Georgia,serif', fontSize: 15, color: '#1a2540', fontStyle: 'italic', lineHeight: 1.7, display: 'block' }}>{data.text}</span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Секция 06 — Целевой сценарий */}
          <div style={S.section} id="s5">
            <h2 style={S.sectionH2}><span style={S.num}>06</span>Целевой сценарий</h2>
            <div style={S.reportText}>
              {strategy?.transition_description ? (
                <p>Через 12–18 месяцев компания должна перейти к гексаграмме <strong>{strategy.transition_description}</strong>{strategy.transition_title ? ` «${strategy.transition_title}»` : ''}.</p>
              ) : (
                <p style={S.muted}>Целевой сценарий будет добавлен при публикации стратегии.</p>
              )}
            </div>
            {strategy?.transition_description && (
              <div style={S.transitionCard}>
                <div style={{ textAlign: 'center' as const }}>
                  <div style={S.hexLg}>䷖</div>
                  <div style={S.faint}>сейчас</div>
                </div>
                <div style={{ flex: 1, borderTop: '1px dashed rgba(26,37,64,0.2)', position: 'relative' as const }}>
                  <span style={S.transitionLabel}>12–18 месяцев</span>
                </div>
                <div style={{ textAlign: 'center' as const }}>
                  <div style={{ ...S.hexLg, color: '#2d6a2d' }}>䷪</div>
                  <div style={S.faint}>цель</div>
                </div>
              </div>
            )}
          </div>
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
  coverMeta: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.7 },
  hexXl: { fontFamily: 'serif', fontSize: 64, color: '#1e3a8a', lineHeight: 1 },
  combBadge: { fontFamily: 'monospace', fontSize: 13, color: 'rgba(26,37,64,0.5)', letterSpacing: 3, marginTop: 8 },
  section: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '28px 32px', marginBottom: 16 },
  sectionH2: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, color: '#1a2540', margin: '0 0 16px', display: 'flex', alignItems: 'baseline', gap: 12 },
  num: { fontFamily: 'sans-serif', fontSize: 11, color: '#c0392b', letterSpacing: 1, flexShrink: 0 },
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
  assumptionsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 },
  assumption: { background: 'rgba(26,37,64,0.03)', borderRadius: 6, padding: '16px 18px' },
  assumptionHead: { display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 },
  numMini: { fontFamily: 'Georgia,serif', fontSize: 13, color: '#c0392b', letterSpacing: 1, flexShrink: 0 },
  assumptionH3: { fontFamily: 'Georgia,serif', fontSize: 15, fontWeight: 600, color: '#1a2540', margin: 0 },
  assumptionBody: { fontFamily: 'Georgia,serif', fontSize: 14, lineHeight: 1.7, color: '#1a2540', margin: 0 },
  bmcRow: { padding: '18px 0', borderBottom: '1px solid rgba(26,37,64,0.06)' },
  bmcRowTitle: { fontFamily: 'Georgia,serif', fontSize: 15, color: '#1a2540' },
  bmcComment: { marginTop: 14, padding: '18px 22px', background: 'rgba(30,58,138,0.05)', border: '1px solid rgba(30,58,138,0.12)', borderRadius: 6 },
  transitionCard: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '20px 28px', marginTop: 18, display: 'flex', alignItems: 'center', gap: 24 },
  hexLg: { fontFamily: 'serif', fontSize: 40, color: '#1e3a8a', lineHeight: 1 },
  transitionLabel: { position: 'absolute' as const, top: -10, left: '50%', transform: 'translateX(-50%)', background: '#e8e4db', padding: '0 10px', fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', letterSpacing: 2, textTransform: 'uppercase' as const, whiteSpace: 'nowrap' as const },
}

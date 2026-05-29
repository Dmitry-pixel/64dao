'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getMe, getAssessment, reportDownloadUrl, type AuthUser, type Assessment } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || ''

// ── Таблица гексаграмм ────────────────────────────────────────────────────────
const HEXAGRAM_MAP: Record<string, { n: number; name: string }> = {
  'AAAAAA': { n:  1, name: 'Действие' },
  'BBBBBB': { n:  2, name: 'Реакция' },
  'ABBBAB': { n:  3, name: 'Появление' },
  'BABBBA': { n:  4, name: 'Формализация' },
  'AAABAB': { n:  5, name: 'Бдительность' },
  'BABAAA': { n:  6, name: 'Раздор' },
  'BABBBB': { n:  7, name: 'Управление' },
  'BBBBAB': { n:  8, name: 'Объединение' },
  'AAABAA': { n:  9, name: 'Развитие' },
  'AABAAA': { n: 10, name: 'Последовательность' },
  'AAABBB': { n: 11, name: 'Достижение' },
  'BBBAAA': { n: 12, name: 'Препятствие' },
  'ABAAAA': { n: 13, name: 'Осознанность' },
  'AAAABA': { n: 14, name: 'Процветание' },
  'BBABBB': { n: 15, name: 'Смирение' },
  'BBBABB': { n: 16, name: 'Радость' },
  'ABBAAB': { n: 17, name: 'Соответствие' },
  'BAABBA': { n: 18, name: 'Диссонанс' },
  'AABBBB': { n: 19, name: 'Подход' },
  'BBBBAA': { n: 20, name: 'Наблюдать' },
  'ABBABA': { n: 21, name: 'Устранять' },
  'ABABBA': { n: 22, name: 'Изящество' },
  'BBBBBA': { n: 23, name: 'Разрушение' },
  'ABBBBB': { n: 24, name: 'Возрождение' },
  'ABBAAA': { n: 25, name: 'Естественность' },
  'AAABBA': { n: 26, name: 'Изобилие' },
  'ABBBBA': { n: 27, name: 'Умеренность' },
  'BAAAAB': { n: 28, name: 'Избыток' },
  'BABBAB': { n: 29, name: 'Решимость' },
  'ABAABA': { n: 30, name: 'Великолепие' },
  'BBAAAB': { n: 31, name: 'Влияние' },
  'BAAABB': { n: 32, name: 'Выносливость' },
  'BBAAAA': { n: 33, name: 'Благоразумие' },
  'AAAABB': { n: 34, name: 'Сила' },
  'BBBABA': { n: 35, name: 'Благоприятный' },
  'ABABBB': { n: 36, name: 'Неблагоприятный' },
  'ABABAA': { n: 37, name: 'Гармония' },
  'AABABA': { n: 38, name: 'Полярность' },
  'BBABAB': { n: 39, name: 'Трудность' },
  'BABABB': { n: 40, name: 'Избавление' },
  'AABBBA': { n: 41, name: 'Убыток' },
  'ABBBAA': { n: 42, name: 'Прибыль' },
  'AAAAAB': { n: 43, name: 'Прорыв' },
  'BAAAAA': { n: 44, name: 'Встреча' },
  'BBBAAB': { n: 45, name: 'Объединение' },
  'BAABBB': { n: 46, name: 'Самоотдача' },
  'BABAAB': { n: 47, name: 'Понимание' },
  'BAABAB': { n: 48, name: 'Глубина' },
  'ABAAAB': { n: 49, name: 'Реформа' },
  'BAAABA': { n: 50, name: 'Ценности' },
  'ABBABB': { n: 51, name: 'Смелость' },
  'BBABBA': { n: 52, name: 'Сосредоточенность' },
  'BBABAA': { n: 53, name: 'Готовность' },
  'AABABB': { n: 54, name: 'Амбиции' },
  'ABAABB': { n: 55, name: 'Изобилие' },
  'BBAABA': { n: 56, name: 'Стимулирование' },
  'BABBAA': { n: 57, name: 'Интуиция' },
  'AABAAB': { n: 58, name: 'Бодрость' },
  'BAABAA': { n: 59, name: 'Установление связей' },
  'AABBAB': { n: 60, name: 'Реализм' },
  'AABBAA': { n: 61, name: 'Внутренняя правда' },
  'BBAABB': { n: 62, name: 'Точность' },
  'ABABAB': { n: 63, name: 'Завершение' },
  'BABABA': { n: 64, name: 'Незавершённость' },
}

const TARGET_HEX: Record<number, number> = {
   1:  9,  2: 62,  3: 49,  4:  7,  5: 63,  6:  6,  7: 62,  8: 23,
   9: 37, 10: 25, 11: 36, 12:  9, 13: 37, 14: 26, 15: 11, 16: 54,
  17: 63, 18: 64, 19: 34, 20: 33, 21: 64, 22: 18, 23: 56, 24: 19,
  25: 37, 26: 22, 27:  4, 28: 44, 29:  3, 30: 22, 31: 43, 32: 44,
  33:  1, 34:  1, 35: 64, 36: 37, 37: 63, 38: 21, 39:  5, 40: 46,
  41: 27, 42:  3, 43:  5, 44: 33, 45: 58, 46: 57, 47: 44, 48: 47,
  49: 63, 50: 18, 51: 25, 52: 18, 53: 39, 54: 11, 55: 36, 56: 14,
  57: 44, 58:  5, 59: 44, 60: 43, 61: 42, 62: 33, 63: 17, 64: 40,
}

// combo → unicode hexagram character (U+4DC0 + n - 1)
function comboToChar(combo: string): string {
  const entry = HEXAGRAM_MAP[combo]
  if (!entry) return ''
  return String.fromCodePoint(0x4DC0 + entry.n - 1)
}

// Returns target hexagram info or null
function getTargetHex(combo: string): { char: string; n: number; name: string } | null {
  const entry = HEXAGRAM_MAP[combo]
  if (!entry) return null
  const targetN = TARGET_HEX[entry.n]
  if (!targetN) return null
  // find target by number
  const found = Object.entries(HEXAGRAM_MAP).find(([, v]) => v.n === targetN)
  if (!found) return null
  return {
    char: String.fromCodePoint(0x4DC0 + targetN - 1),
    n: targetN,
    name: found[1].name,
  }
}

// Русские метки для сценария стратагемы
const SCENARIO_LABELS: [string, string][] = [
  ['innovation_strategy',   'Стратегия изменений'],
  ['innovation_type',       'Тип изменений'],
  ['value_discipline',      'Ценностная дисциплина'],
  ['leadership_principles', 'Принципы лидерства'],
  ['growth_strategy',       'Стратегия роста'],
  ['focus',                 'Фокус'],
]

// ─────────────────────────────────────────────────────────────────────────────

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
        const isMethod2Only = a.method2_data && Object.keys(a.method2_data).length > 0 && a.method1_combination === 'AAAAAA'
        if (a.method1_combination && !isMethod2Only) {
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
  const isMethod2Only = !!(method2 && Object.keys(method2).length > 0 && combo === 'AAAAAA')
  const companyName = assessment.company_name || user?.company_name || 'Компания'

  const hexChar = comboToChar(combo)
  const hexInfo = HEXAGRAM_MAP[combo]
  const targetHex = getTargetHex(combo)

  const BMC_NAMES = [
    'Ключевые партнёры', 'Ключевые активности', 'Ключевые ресурсы',
    'Ценностное предложение', 'Отношения с клиентами', 'Каналы',
    'Сегменты клиентов', 'Структура издержек', 'Потоки доходов',
  ]

  const LC_LABELS: [string, string][] = [
    ['lc_profit',    'Формирование прибыли'],
    ['lc_strategy',  'Рыночная стратегия'],
    ['lc_decisions', 'Принятие решений'],
    ['lc_consumer',  'Тип потребителя'],
    ['lc_market',    'Статус рынка'],
    ['lc_value',     'Тип ценности'],
  ]

  const ASSM_LABELS: [string, string][] = [
    ['assm_planning',     'Планирование'],
    ['assm_growth',       'Рост и производительность'],
    ['assm_advertising',  'Реклама'],
    ['assm_feedback',     'Обратная связь'],
    ['assm_risk',         'Риск'],
    ['assm_product',      'Выбор продукта'],
    ['assm_service',      'Сервис'],
    ['assm_startup',      'Стартап'],
    ['assm_investment',   'Инвестиции и финансы'],
    ['assm_contracts',    'Договора и соглашения'],
    ['assm_sync',         'Синхронизация'],
    ['assm_creative',     'Творческий вклад'],
    ['assm_interaction',  'Взаимодействие'],
    ['assm_resources',    'Достаточность ресурсов'],
    ['assm_research',     'Исследование и разработка'],
    ['assm_trade',        'Международная торговля'],
    ['assm_failures',     'Источники неудач'],
    ['assm_success',      'Источники удачи'],
  ]

  const sections = isMethod2Only
    ? ['01 — Бизнес-модель (9 блоков)']
    : [
        '01 — Текущее состояние',
        '02 — Стадия жизненного цикла',
        '03 — Сценарий развития',
        '04 — Предположения',
        '05 — Целевой сценарий',
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
              <span style={S.labelRed}>{isMethod2Only ? 'Бизнес-модель 64 ДАО' : 'Стратегический отчёт 64 ДАО'}</span>
              <h1 style={S.coverH1}>
                {isMethod2Only
                  ? `Бизнес-модель · ${companyName}`
                  : (strategy?.title || `Стратегическая диагностика · ${companyName}`)}
              </h1>
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
                          {Array.from({ length: 5 }, (_, j) => (
                            <div key={j} style={{ width: 14, height: 6, borderRadius: 99, background: j < data.score ? '#1e3a8a' : 'rgba(26,37,64,0.08)' }} />
                          ))}
                        </div>
                      </div>
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
              <div style={S.stateGrid}>
                <div style={S.stateCell}>
                  <span style={S.labelRed}>Стратагема</span>
                  <div style={S.stateVal}>{strategy?.stratagema_title || <em style={{ opacity: 0.4, fontSize: 14 }}>Не заполнено</em>}</div>
                </div>
                <div style={S.stateCell}>
                  <span style={S.labelRed}>Стадия жизненного цикла</span>
                  <div style={S.stateVal}>{strategy?.lifecycle_stage || <em style={{ opacity: 0.4, fontSize: 14 }}>Не заполнено</em>}</div>
                </div>
                <div style={S.stateCell}>
                  <span style={S.labelRed}>Комбинация</span>
                  <div style={{ ...S.stateVal, fontFamily: 'monospace', letterSpacing: 3 }}>{combo}</div>
                </div>
              </div>

              {/* Таблица стратагемы — всегда отображаем все 6 строк */}
              <div style={S.scenarioTable}>
                <div style={S.scenarioHead}>
                  <span style={S.labelRed}>Таблица стратагемы</span>
                  <span style={S.faint}>Гексаграмма {combo}</span>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 14 }}>
                  <thead>
                    <tr>
                      <th style={S.th}>Параметр</th>
                      <th style={S.th}>Значение</th>
                    </tr>
                  </thead>
                  <tbody>
                    {SCENARIO_LABELS.map(([key, label]) => {
                      const val = strategy?.scenario?.[key]
                      return (
                        <tr key={key}>
                          <td style={S.td}>{label}</td>
                          <td style={S.td}>{val || <em style={{ opacity: 0.4 }}>Не заполнено</em>}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Секция 02 — Жизненный цикл */}
            <div style={S.section} id="s1">
              <h2 style={S.sectionH2}><span style={S.num}>02</span>Стадия жизненного цикла</h2>
              <div style={S.reportText}>
                {strategy?.lifecycle_description
                  ? strategy.lifecycle_description.split('\n').map((p: string, i: number) => <p key={i} style={{ marginBottom: 14 }}>{p}</p>)
                  : <p style={S.muted}>Описание стадии будет добавлено при публикации стратегии.</p>}
              </div>
              {/* 6 блоков жизненного цикла */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 16 }}>
                {LC_LABELS.map(([field, label]) => (
                  <div key={field} style={{ background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '12px 14px' }}>
                    <div style={{ fontSize: 9, fontFamily: 'sans-serif', letterSpacing: 1, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.45)', fontWeight: 600, marginBottom: 6 }}>{label}</div>
                    <p style={{ fontSize: 13, color: '#1a2540', lineHeight: 1.6, margin: 0, fontFamily: 'sans-serif' }}>
                      {strategy?.[field] || <em style={{ opacity: 0.35 }}>Не заполнено</em>}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Секция 03 — Сценарий развития */}
            <div style={S.section} id="s2">
              <h2 style={S.sectionH2}><span style={S.num}>03</span>Сценарий развития</h2>
              <div style={S.reportText}>
                {strategy?.scenario_text
                  ? strategy.scenario_text.split('\n').map((p: string, i: number) => <p key={i} style={{ marginBottom: 14 }}>{p}</p>)
                  : <p style={S.muted}>Текст сценария будет добавлен при публикации стратегии.</p>}
              </div>
              {/* Маркетинг */}
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 10, color: '#c0392b', letterSpacing: 2, textTransform: 'uppercase' as const, fontFamily: 'sans-serif', fontWeight: 700, marginBottom: 8 }}>Маркетинг</div>
                <div style={{ border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '14px 16px', background: 'rgba(255,255,255,0.5)', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.7)', lineHeight: 1.7 }}>
                  {strategy?.marketing_text || <em style={{ opacity: 0.4 }}>Не заполнено</em>}
                </div>
              </div>
              {/* Управление */}
              <div style={{ marginTop: 14 }}>
                <div style={{ fontSize: 10, color: '#c0392b', letterSpacing: 2, textTransform: 'uppercase' as const, fontFamily: 'sans-serif', fontWeight: 700, marginBottom: 8 }}>Управление</div>
                <div style={{ border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '14px 16px', background: 'rgba(255,255,255,0.5)', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.7)', lineHeight: 1.7 }}>
                  {strategy?.management_text || <em style={{ opacity: 0.4 }}>Не заполнено</em>}
                </div>
              </div>
            </div>

            {/* Секция 04 — Предположения (assm_*) */}
            <div style={S.section} id="s3">
              <h2 style={S.sectionH2}><span style={S.num}>04</span>Предположения. Связи с будущим</h2>
              <p style={S.muted}>Предположения, лежащие в основе принятия решений.</p>
              <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 12, marginTop: 12 }}>
                {ASSM_LABELS.map(([field, label]) => (
                  <div key={field} style={{ marginBottom: 4 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: '#c0392b', fontFamily: 'sans-serif', marginBottom: 4 }}>{label}</div>
                    <p style={{ fontSize: 13, color: 'rgba(26,37,64,0.7)', lineHeight: 1.7, margin: 0, fontFamily: 'sans-serif' }}>
                      {strategy?.[field] || <em style={{ opacity: 0.4 }}>Не заполнено</em>}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Секция 05 — Целевой сценарий */}
            <div style={S.section} id="s4">
              <h2 style={S.sectionH2}><span style={S.num}>05</span>Целевой сценарий</h2>

              {/* Название перехода */}
              <div style={{ marginBottom: 12 }}>
                <span style={S.labelRed}>Название перехода</span>
                <div style={{ ...S.stateVal, marginTop: 4 }}>
                  {strategy?.transition_title || <em style={{ opacity: 0.4, fontSize: 14 }}>Не заполнено</em>}
                </div>
              </div>

              {/* Стадия целевого состояния */}
              <div style={{ marginBottom: 12 }}>
                <span style={S.labelRed}>Стадия целевого состояния</span>
                <div style={{ ...S.stateVal, marginTop: 4 }}>
                  {strategy?.transition_lifecycle_stage || <em style={{ opacity: 0.4, fontSize: 14 }}>Не заполнено</em>}
                </div>
              </div>

              {/* Описание перехода */}
              <div style={{ marginBottom: 20 }}>
                <span style={S.labelRed}>Описание перехода</span>
                <div style={{ ...S.reportText, marginTop: 8 }}>
                  {strategy?.transition_description
                    ? strategy.transition_description.split('\n').map((p: string, i: number) => <p key={i} style={{ marginBottom: 14 }}>{p}</p>)
                    : <p style={S.muted}>Описание перехода будет добавлено при публикации стратегии.</p>}
                </div>
              </div>

              {/* Визуализация перехода: текущая → целевая гексаграмма */}
              <div style={S.transitionCard}>
                <div style={{ textAlign: 'center' as const }}>
                  <div style={S.hexLg}>{hexChar || '?'}</div>
                  <div style={S.faint}>сейчас</div>
                  {hexInfo && (
                    <div style={{ fontFamily: 'sans-serif', fontSize: 10, color: 'rgba(26,37,64,0.4)', marginTop: 2 }}>
                      №{hexInfo.n} · {hexInfo.name}
                    </div>
                  )}
                </div>
                <div style={{ flex: 1, borderTop: '1px dashed rgba(26,37,64,0.2)', position: 'relative' as const }}>
                  <span style={S.transitionLabel}>12–18 месяцев</span>
                </div>
                <div style={{ textAlign: 'center' as const }}>
                  {targetHex ? (
                    <>
                      <div style={{ ...S.hexLg, color: '#2d6a2d' }}>{targetHex.char}</div>
                      <div style={S.faint}>цель</div>
                      <div style={{ fontFamily: 'sans-serif', fontSize: 10, color: 'rgba(26,37,64,0.4)', marginTop: 2 }}>
                        №{targetHex.n} · {targetHex.name}
                      </div>
                    </>
                  ) : (
                    <>
                      <div style={{ ...S.hexLg, color: '#2d6a2d' }}>?</div>
                      <div style={S.faint}>цель</div>
                    </>
                  )}
                </div>
              </div>
            </div>
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
  bmcRow: { padding: '18px 0', borderBottom: '1px solid rgba(26,37,64,0.06)' },
  bmcRowTitle: { fontFamily: 'Georgia,serif', fontSize: 15, color: '#1a2540' },
  bmcComment: { marginTop: 14, padding: '18px 22px', background: 'rgba(30,58,138,0.05)', border: '1px solid rgba(30,58,138,0.12)', borderRadius: 6 },
  transitionCard: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '20px 28px', marginTop: 18, display: 'flex', alignItems: 'center', gap: 24 },
  hexLg: { fontFamily: 'serif', fontSize: 40, color: '#1e3a8a', lineHeight: 1 },
  transitionLabel: { position: 'absolute' as const, top: -10, left: '50%', transform: 'translateX(-50%)', background: '#e8e4db', padding: '0 10px', fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', letterSpacing: 2, textTransform: 'uppercase' as const, whiteSpace: 'nowrap' as const },
}

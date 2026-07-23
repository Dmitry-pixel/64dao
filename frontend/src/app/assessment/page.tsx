'use client'
export const dynamic = 'force-dynamic'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { getMe, getFinanceItems, type AuthUser, type FinanceBlock } from '@/lib/api'
import ContourSurvey from '@/components/ContourSurvey'

const QUESTIONS = [
  {
    eyebrow: 'Вопрос 01 / 06',
    question: 'Где сейчас фокус усилий компании?',
    help: 'За счёт чего формируется прибыль? Подумайте, какой тип задач занимает больше времени у руководства последние 3–6 месяцев.',
    a: 'Рост выручки и объёма продаж',
    b: 'Повышение эффективности, сокращение расходов и потерь',
  },
  {
    eyebrow: 'Вопрос 02 / 06',
    question: 'Как компания реагирует на изменения рынка?',
    help: 'Какую рыночную стратегию преимущественно использует компания? Вы копируете или создаёте?',
    a: 'Быстрый последователь — адаптация уже подтверждённых решений. Быстро адаптирует и улучшает существующие решения',
    b: 'Первопроходец — создание новых решений и рынков. Создаёт новые категории, продукты или подходы',
  },
  {
    eyebrow: 'Вопрос 03 / 06',
    question: 'Как принимаются стратегические решения?',
    help: 'Как организовано управление? Как принимаются ключевые решения?',
    a: 'Преимущественно централизованно',
    b: 'Преимущественно распределённо',
  },
  {
    eyebrow: 'Вопрос 04 / 06',
    question: 'Кто является основным клиентом компании?',
    help: 'Оцените, какой сегмент приносит основную часть выручки.',
    a: 'Корпоративные клиенты (B2B)',
    b: 'Частные потребители (B2C)',
  },
  {
    eyebrow: 'Вопрос 05 / 06',
    question: 'Как можно описать рынок компании?',
    help: 'Оцените зрелость и конкурентную среду вашего рынка.',
    a: 'Зрелый рынок с высокой конкуренцией',
    b: 'Развивающийся рынок с формирующимся спросом',
  },
  {
    eyebrow: 'Вопрос 06 / 06',
    question: 'На чём преимущественно основана ценность продукта или сервиса?',
    help: 'Что является главным источником ценности для ваших клиентов?',
    a: 'Технологические инновации',
    b: 'Улучшение существующих решений',
  },
]

const BMC_BLOCKS = [
  { num: '01', title: 'Ценностное предложение', help: 'Какую конкретную пользу клиент получает? Чем вы отличаетесь от альтернатив?' },
  { num: '02', title: 'Отношения с клиентами', help: 'Какие связи компания выстраивает: персональные, самообслуживание, сообщество?' },
  { num: '03', title: 'Ключевые ресурсы', help: 'Какие активы, люди, технологии и капитал необходимы для работы?' },
  { num: '04', title: 'Потоки доходов', help: 'Как компания зарабатывает: продажи, подписка, лицензии, комиссии?' },
  { num: '05', title: 'Ключевые партнёры', help: 'Кто помогает компании создавать и доставлять ценность? Какие альянсы и поставщики критичны?' },
  { num: '06', title: 'Сегменты клиентов', help: 'Кто ваш клиент? Существует ли несколько сегментов с разными потребностями?' },
  { num: '07', title: 'Ключевые активности', help: 'Что компания делает каждый день, чтобы создавать ценность для клиента?' },
  { num: '08', title: 'Каналы', help: 'Через какие каналы клиенты узнают о продукте и получают его?' },
  { num: '09', title: 'Структура издержек', help: 'Какие затраты ключевые? Постоянные или переменные? На чём фокус?' },
]

function AssessmentInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const methodParam = searchParams.get('method')
  const companyIdParam = searchParams.get('company')
  const companyNameParam = searchParams.get('company_name')

  const [user, setUser] = useState<AuthUser | null>(null)
  const [mode, setMode] = useState<'choose' | 'company' | 'method1' | 'method2' | 'finance_intro' | 'finance' | 'waiting'>(
    companyIdParam && methodParam === '2' ? 'method2'
    : companyIdParam && methodParam ? 'method1'
    : methodParam === '1' ? 'company' : methodParam === '2' ? 'company' : 'choose'
  )
  const [pendingMethod, setPendingMethod] = useState<'method1' | 'method2'>(
    methodParam === '2' ? 'method2' : 'method1'
  )
  const [companyName, setCompanyName] = useState(companyNameParam || '')
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<number, 'A' | 'B'>>({})
  const [selected, setSelected] = useState<'A' | 'B' | null>(null)
  const [bmcScores, setBmcScores] = useState<Record<number, number>>({})
  const [bmcTexts, setBmcTexts] = useState<Record<number, string>>({})
  const [activeBlock, setActiveBlock] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [finItems, setFinItems] = useState<FinanceBlock[] | null>(null)
  const [finScale, setFinScale] = useState<Record<string, string>>({})
  const [finMaxUnknowns, setFinMaxUnknowns] = useState(3)
  const [finLoading, setFinLoading] = useState(false)

  useEffect(() => {
    getMe().catch(() => router.push('/login'))
      .then(u => { if (u) setUser(u) })
  }, [router])

  useEffect(() => {
    setSelected(answers[step] || null)
  }, [step, answers])

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      const inFlow = mode === 'method1' || mode === 'finance_intro' || mode === 'finance'
      if (inFlow && Object.keys(answers).length > 0) { e.preventDefault(); e.returnValue = '' }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [mode, answers])

  function handleAnswer(v: 'A' | 'B') {
    setSelected(v)
    setAnswers(prev => ({ ...prev, [step]: v }))
  }

  function nextStep() {
    if (!selected) return
    if (step < 5) { setStep(s => s + 1) } else { goToFinance() }
  }

  async function goToFinance() {
    setMode('finance_intro')
    if (!finItems) {
      setFinLoading(true)
      try {
        const data = await getFinanceItems()
        setFinItems(data.blocks); setFinScale(data.scale_labels)
        setFinMaxUnknowns(data.max_unknowns ?? 3)
      } catch { alert('Не удалось загрузить вопросы финансового блока. Попробуйте ещё раз.') }
      finally { setFinLoading(false) }
    }
  }

  function prevStep() {
    if (step > 0) setStep(s => s - 1)
  }

  async function submitMethod1(financeAnswers: Record<string, number | null>) {
    setSubmitting(true)
    const answersMap: Record<string, string> = {}
    const combo = Object.values(answers).map(v => v).join('')
    for (let i = 0; i < 6; i++) answersMap[`q${i + 1}`] = answers[i] || 'A'
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || ''
      const res = await fetch(`${API}/api/assessments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          method1_answers: answersMap,
          method1_combination: combo,
          finance_answers: financeAnswers,
          company_name: companyName.trim() || undefined,
          company_id: companyIdParam || undefined,
          status: 'completed',
        }),
      })
      if (res.ok) {
        const assessment = await res.json()
        fetch(`${API}/api/assessments/${assessment.id}/generate-report`, {
          method: 'POST',
          credentials: 'include',
        }).catch(() => {})
        // Цепочка контуров: после финблока предлагаем продолжить, а не уводим
        // в кабинет. Развилка сама решит, что показать (Метод 2 не затрагивается).
        router.push(`/assessment/continue?assessment=${assessment.id}`)
        return
      } else {
        const errText = await res.text().catch(() => '')
        alert(`Save failed (${res.status}). ${errText}`)
      }
    } catch {
      alert('Save failed. Check connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function submitMethod2() {
    setSubmitting(true)
    const method2_data: Record<string, { score: number; text: string }> = {}
    BMC_BLOCKS.forEach((b, i) => {
      method2_data[b.title] = { score: bmcScores[i] || 0, text: bmcTexts[i] || '' }
    })
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || ''
      const res = await fetch(`${API}/api/assessments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          method1_answers: { q1: 'A', q2: 'A', q3: 'A', q4: 'A', q5: 'A', q6: 'A' },
          method1_combination: 'AAAAAA',
          method2_data,
          company_name: companyName.trim() || undefined,
          company_id: companyIdParam || undefined,
          status: 'completed',
        }),
      })
      if (res.ok) {
        const assessment = await res.json()
        fetch(`${API}/api/assessments/${assessment.id}/generate-report`, {
          method: 'POST',
          credentials: 'include',
        }).catch(() => {})
        setMode('waiting')
      } else {
        const errText = await res.text().catch(() => '')
        alert(`Не удалось сохранить диагностику (${res.status}). ${errText}`)
      }
    } catch {
      alert('Не удалось сохранить диагностику. Проверьте соединение и попробуйте снова.')
    } finally {
      setSubmitting(false)
    }
  }

  // Строим гексаграмму
  const hexLines = Array.from({ length: 6 }, (_, i) => {
    if (i >= step + 1) return 'empty'
    return answers[i] === 'A' ? 'solid' : 'broken'
  })

  const NavBar = () => (
    <nav style={S.nav}>
      <div style={S.navInner}>
        <div style={S.navLogo} onClick={() => router.push('/dashboard')}>
          <span style={S.logo64}>64</span><span style={S.logoDao}> ДАО</span>
        </div>
        <div style={S.navLinks}>
          <button style={S.navLink} onClick={() => router.push(user?.role === 'admin' ? '/admin/my-reports' : '/dashboard')}>Мои отчёты</button>
          <button style={{ ...S.navLink, ...S.navLinkOn }}>Новая диагностика</button>
          <button style={S.navLink} onClick={() => router.push('/profile')}>Профиль</button>
        </div>
        <div style={S.navUser}>
          <span style={S.navEmail}>{user?.email}</span>
          <div style={S.avatar}>{(user?.full_name || user?.email || 'U')[0].toUpperCase()}</div>
        </div>
      </div>
    </nav>
  )

  // ── Ожидание отчёта ────────────────────────────────────────────────────────
  if (mode === 'waiting') return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      <NavBar />
      <div style={S.waitStage}>
        <div style={S.waitHex}>䷖</div>
        <span style={{ ...S.labelRed, marginTop: 14 }}>Анализ сценария</span>
        <h2 style={S.waitH2}>Формируем отчёт</h2>
        <p style={S.waitText}>Отчёт сформирован. Сделан анализ и получена текущая стратегия из 64 возможных. Перейдите в личный кабинет.</p>
        <div style={{ display: 'flex', gap: 10, marginTop: 32 }}>
          <button style={S.btnPrimary} onClick={() => router.push('/dashboard')}>Перейти в личный кабинет</button>
        </div>
      </div>
    </div>
  )

  // ── Выбор метода ──────────────────────────────────────────────────────────
  if (mode === 'choose') return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      <NavBar />
      <div style={S.choosePad}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginBottom: 14 }}>
          <span style={S.labelRed}>Новая диагностика</span>
        </div>
        <h1 style={S.chooseH1}>Выберите, с чего начать</h1>
        <div className="choose-grid" style={S.chooseGrid}>
          <div style={S.methodCard} onClick={() => { setPendingMethod('method1'); setMode('company') }}>
            <div style={S.methodCardTop}>
              <span style={S.labelRed}>Метод 01 · Стратегия</span>
              <span style={S.hexFaint}>䷀</span>
            </div>
            <h3 style={S.methodH3}>6 вопросов о состоянии компании</h3>
            <p style={S.methodDesc}>На каждом шаге выбираете A или B. На выходе — комбинация из 64 (например, ABABBA), стадия жизненного цикла и ключевой сценарий.</p>
            <div style={S.methodFoot}>
              <span style={S.methodTime}>≈ 5 минут</span>
              <span style={S.methodGo}>Начать →</span>
            </div>
          </div>
          <div style={S.methodCard} onClick={() => { setPendingMethod('method2'); setMode('company') }}>
            <div style={S.methodCardTop}>
              <span style={S.labelRed}>Метод 02 · Бизнес-модель</span>
              <span style={S.hexFaint}>䷷</span>
            </div>
            <h3 style={S.methodH3}>9 блоков по шкале 1–5</h3>
            <p style={S.methodDesc}>Оцените каждый блок Business Model Canvas: клиенты, ценность, каналы, ресурсы, доходы. Можно дополнять текстом.</p>
            <div style={S.methodFoot}>
              <span style={S.methodTime}>≈ 10 минут</span>
              <span style={S.methodGo}>Начать →</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  // ── Ввод названия компании ───────────────────────────────────────────────
  if (mode === 'company') return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      <NavBar />
      <div style={{ maxWidth: 560, margin: '0 auto', padding: '80px 40px' }}>
        <span style={S.labelRed}>
          {pendingMethod === 'method1' ? 'Метод 01 · Стратегия' : 'Метод 02 · Бизнес-модель'}
        </span>
        <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', margin: '10px 0 8px' }}>
          Название компании
        </h1>
        <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', marginBottom: 32, lineHeight: 1.6 }}>
          Введите название вашей компании — оно будет отображаться в отчёте.
        </p>
        <input
          autoFocus
          type="text"
          placeholder="Например: ООО Ромашка"
          value={companyName}
          onChange={e => setCompanyName(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && companyName.trim()) setMode(pendingMethod) }}
          style={{
            width: '100%', boxSizing: 'border-box' as const,
            padding: '14px 18px', fontFamily: 'sans-serif', fontSize: 15,
            border: '1px solid rgba(26,37,64,0.2)', borderRadius: 8,
            outline: 'none', color: '#1a2540', background: '#fff',
            marginBottom: 20,
          }}
        />
        <div style={{ display: 'flex', gap: 12 }}>
          <button style={S.btnGhost} onClick={() => setMode('choose')}>← Назад</button>
          <button
            style={{ ...S.btnPrimary, opacity: companyName.trim() ? 1 : 0.45 }}
            disabled={!companyName.trim()}
            onClick={() => setMode(pendingMethod)}
          >
            Продолжить →
          </button>
        </div>
      </div>
    </div>
  )

  // ── Метод 1 — вопросы ────────────────────────────────────────────────────
  if (mode === 'method1') {
    const q = QUESTIONS[step]
    const progress = ((step) / 6) * 100
    return (
      <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
        <NavBar />
        <div style={S.qStage}>
          {/* Прогресс */}
          <div style={S.qProgress}>
            <span style={{ fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)' }}>Метод 01 · Стратегия</span>
            <div style={S.qProgressBar}>
              <div style={{ ...S.qProgressFill, width: `${(step / 6) * 100}%` }} />
            </div>
            <div style={S.qProgressDots}>
              {Array.from({ length: 6 }, (_, i) => (
                <span key={i} style={{
                  ...S.qDot,
                  ...(i < step ? S.qDotDone : {}),
                  ...(i === step ? S.qDotNow : {}),
                }} />
              ))}
            </div>
            <span style={{ fontFamily: 'Georgia,serif', fontSize: 14, color: '#1a2540' }}>{step + 1} / 6</span>
          </div>

          {/* Тело вопроса */}
          <div style={S.qBody}>
            <div>
              <div style={S.qEyebrow}>{q.eyebrow}</div>
              <h2 style={S.qQuestion}>{q.question}</h2>
              <p style={S.qHelp}>{q.help}</p>
              <div style={S.qOptions}>
                <button style={{ ...S.qOption, ...(selected === 'A' ? S.qOptionOn : {}) }} onClick={() => handleAnswer('A')}>
                  <span style={{ ...S.qLetter, ...(selected === 'A' ? S.qLetterOn : {}) }}>A</span>
                  <span style={S.qText}>{q.a}</span>
                </button>
                <button style={{ ...S.qOption, ...(selected === 'B' ? S.qOptionOn : {}) }} onClick={() => handleAnswer('B')}>
                  <span style={{ ...S.qLetter, ...(selected === 'B' ? S.qLetterOn : {}) }}>B</span>
                  <span style={S.qText}>{q.b}</span>
                </button>
              </div>
            </div>

            {/* Визуализация гексаграммы */}
            <div style={S.qVisual}>
              <div style={S.hexStack}>
                {hexLines.slice().reverse().map((type, i) => (
                  <div key={i} style={{ width: 120, height: 14, display: 'flex', justifyContent: 'space-between', opacity: type === 'empty' ? 0.15 : 1 }}>
                    {type === 'solid' ? (
                      <div style={{ width: '100%', height: '100%', background: '#1e3a8a', borderRadius: 1 }} />
                    ) : type === 'broken' ? (
                      <>
                        <div style={{ width: '48%', height: '100%', background: '#1e3a8a', borderRadius: 1 }} />
                        <div style={{ width: '48%', height: '100%', background: '#1e3a8a', borderRadius: 1 }} />
                      </>
                    ) : (
                      <div style={{ width: '100%', height: '100%', background: 'rgba(26,37,64,0.15)', borderRadius: 1 }} />
                    )}
                  </div>
                ))}
              </div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2, color: 'rgba(26,37,64,0.4)', textTransform: 'uppercase' as const, marginTop: 18 }}>
                {step === 0 ? 'гексаграмма формируется' : Object.values(answers).join('')}
              </div>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.4)', marginTop: 14, maxWidth: 240, lineHeight: 1.6, textAlign: 'center' as const }}>
                Каждый ответ добавляет одну линию. Шесть линий складываются в один из 64 сценариев.
              </p>
            </div>
          </div>

          {/* Кнопки под вариантами */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 24, maxWidth: 540 }}>
            <button style={{ ...S.btnGhost, opacity: step === 0 ? 0.4 : 1 }} onClick={prevStep} disabled={step === 0}>← Назад</button>
            <button style={{ ...S.btnPrimary, opacity: !selected ? 0.4 : 1, minWidth: 140, justifyContent: 'center' }} onClick={nextStep} disabled={!selected || submitting}>
              {step === 5 ? (submitting ? 'Отправка...' : 'Завершить →') : 'Далее →'}
            </button>
          </div>
          <div style={S.qFoot}>
            <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}>Прогресс сохраняется автоматически</span>
          </div>
        </div>
      </div>
    )
  }

  // ── Финансовый блок — интерстициал ───────────────────────────────────────
  if (mode === 'finance_intro') return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      <NavBar />
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '64px 40px' }}>
        <span style={S.labelRed}>Метод 01 · Часть 2 из 2</span>
        <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 34, fontWeight: 400, color: '#1a2540', margin: '10px 0 12px' }}>
          Финансовая функция
        </h1>
        <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.65)', lineHeight: 1.7, marginBottom: 28, maxWidth: 560 }}>
          Вторая часть диагностики — 24 утверждения в 6 блоках, около 10 минут. Оцените каждое по шкале 1–4
          по фактическому состоянию компании, а не по планам. Если данных нет — «Не знаю» (не более одного на блок).
        </p>
        <div style={{ display: 'flex', gap: 12 }}>
          <button style={S.btnGhost} onClick={() => { setMode('method1'); setStep(5) }}>← Назад</button>
          <button style={{ ...S.btnPrimary, opacity: (finLoading || !finItems) ? 0.5 : 1 }} disabled={finLoading || !finItems} onClick={() => setMode('finance')}>
            {finLoading ? 'Загрузка…' : 'Продолжить →'}
          </button>
        </div>
      </div>
    </div>
  )

  // ── Финансовый блок — степпер 6 блоков × 4 утверждения ────────────────────
  if (mode === 'finance') {
    if (!finItems) return (
      <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
        <NavBar />
        <div style={S.qStage}>
          <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.6)' }}>Загрузка…</p>
        </div>
      </div>
    )
    return (
      <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
        <NavBar />
        <ContourSurvey
          title="Метод 01 · Часть 2 · Финансовая функция"
          blocks={finItems}
          scaleLabels={finScale}
          maxUnknowns={finMaxUnknowns}
          submitting={submitting}
          onSubmit={(a) => submitMethod1(a)}
          onCancel={() => setMode('finance_intro')}
        />
      </div>
    )
  }


  if (mode === 'method2') {
    const block = BMC_BLOCKS[activeBlock]
    const score = bmcScores[activeBlock] || 0
    return (
      <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
        <NavBar />
        <div style={S.bmcPad}>
          <span style={S.labelRed}>Метод 02 · Бизнес-модель</span>
          <h1 style={S.bmcH1}>9 блоков бизнес-модели</h1>

          {/* Мини-сетка блоков */}
          <div style={S.bmcGrid}>
            {BMC_BLOCKS.map((b, i) => (
              <div key={i} style={{ ...S.bmcCell, ...(i === activeBlock ? S.bmcCellActive : {}) }} onClick={() => setActiveBlock(i)}>
                <div style={S.bmcNum}>{b.num}</div>
                <div style={S.bmcTitle}>{b.title}</div>
                <div style={S.bmcScore}>
                  {Array.from({ length: 5 }, (_, j) => (
                    <div key={j} style={{ flex: 1, height: 5, borderRadius: 99, background: j < (bmcScores[i] || 0) ? '#1e3a8a' : 'rgba(26,37,64,0.08)' }} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Редактор активного блока */}
          <div style={S.bmcEditor}>
            <div style={S.bmcEditNum}>{block.num}</div>
            <h3 style={S.bmcEditH3}>{block.title}</h3>
            <p style={S.bmcEditHelp}>{block.help}</p>
            <div style={S.bmcScale}>
              <span>Оценка:</span>
              <div style={{ display: 'flex', gap: 6, marginLeft: 'auto' }}>
                {[1, 2, 3, 4, 5].map(n => (
                  <button key={n} style={{ ...S.scaleBtn, ...(score === n ? S.scaleBtnOn : {}) }} onClick={() => setBmcScores(p => ({ ...p, [activeBlock]: n }))}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <textarea
              style={S.bmcTextarea}
              rows={4}
              placeholder="Добавьте комментарий (необязательно)..."
              value={bmcTexts[activeBlock] || ''}
              onChange={e => setBmcTexts(p => ({ ...p, [activeBlock]: e.target.value }))}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 24 }}>
            <button style={S.btnGhost} onClick={() => router.push('/dashboard')}>← Отмена</button>
            <div style={{ display: 'flex', gap: 10 }}>
              {activeBlock > 0 && <button style={S.btnGhost} onClick={() => setActiveBlock(a => a - 1)}>← Предыдущий</button>}
              {activeBlock < 8
                ? <button style={S.btnPrimary} onClick={() => setActiveBlock(a => a + 1)}>Следующий →</button>
                : <button style={S.btnPrimary} onClick={submitMethod2} disabled={submitting}>{submitting ? 'Отправка...' : 'Завершить →'}</button>
              }
            </div>
          </div>
        </div>
      </div>
    )
  }

  return null
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
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 },
  // Choose
  choosePad: { maxWidth: 980, margin: '0 auto', padding: '48px 60px 60px' },
  chooseH1: { fontFamily: 'Georgia,serif', fontSize: 36, fontWeight: 400, color: '#1a2540', margin: '0 0 10px' },
  chooseSub: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', maxWidth: 640, marginBottom: 34, lineHeight: 1.7 },
  chooseGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 18 },
  methodCard: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '22px 26px', cursor: 'pointer' },
  methodCardTop: { display: 'flex', justifyContent: 'space-between', marginBottom: 18 },
  hexFaint: { fontFamily: 'serif', fontSize: 32, color: '#1e3a8a', opacity: 0.2 },
  hexSm: { fontFamily: 'serif', fontSize: 28, color: '#1e3a8a', flexShrink: 0 },
  methodH3: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, color: '#1a2540', margin: '0 0 8px' },
  methodDesc: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.6, margin: '0 0 18px' },
  methodFoot: { display: 'flex', justifyContent: 'space-between', paddingTop: 14, borderTop: '1px solid rgba(26,37,64,0.06)' },
  methodTime: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.4)' },
  methodGo: { fontFamily: 'sans-serif', fontSize: 13, color: '#1e3a8a', fontWeight: 500 },
  fullCard: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '18px 24px', display: 'flex', alignItems: 'center', gap: 18 },
  // Method 1
  qStage: { maxWidth: 1200, margin: '0 auto', padding: '32px 60px 48px', minHeight: 'calc(100vh - 56px)', display: 'flex', flexDirection: 'column' as const },
  qProgress: { display: 'flex', alignItems: 'center', gap: 16, marginBottom: 42, fontFamily: 'sans-serif', fontSize: 11 },
  qProgressBar: { flex: 1, height: 2, background: 'rgba(26,37,64,0.1)', borderRadius: 99, overflow: 'hidden' },
  qProgressFill: { height: '100%', background: '#c0392b', transition: 'width 0.4s', borderRadius: 99 },
  qProgressDots: { display: 'flex', gap: 6 },
  qDot: { width: 7, height: 7, borderRadius: '50%', background: 'rgba(26,37,64,0.1)', display: 'inline-block' },
  qDotDone: { background: '#c0392b' },
  qDotNow: { background: '#c0392b', outline: '2px solid rgba(192,57,43,0.18)', outlineOffset: 2 },
  qBody: { display: 'grid', gridTemplateColumns: '1fr 320px', gap: 48, flex: 1, alignItems: 'center' },
  qEyebrow: { fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 3, color: '#c0392b', textTransform: 'uppercase' as const, marginBottom: 14 },
  qQuestion: { fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', lineHeight: 1.3, margin: '0 0 14px' },
  qHelp: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', lineHeight: 1.7, maxWidth: 480 },
  qOptions: { display: 'flex', flexDirection: 'column' as const, gap: 14, marginTop: 24, maxWidth: 540 },
  qOption: { display: 'grid', gridTemplateColumns: '36px 1fr', gap: 18, alignItems: 'center', padding: '22px 26px', background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, cursor: 'pointer', textAlign: 'left' as const, fontFamily: 'sans-serif', transition: 'all 0.15s' },
  qOptionOn: { borderColor: '#1e3a8a', background: 'rgba(30,58,138,0.04)', boxShadow: 'inset 0 0 0 1px #1e3a8a' },
  qLetter: { width: 36, height: 36, borderRadius: '50%', border: '1.5px solid #c0392b', color: '#c0392b', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Georgia,serif', fontSize: 16, fontWeight: 600 },
  qLetterOn: { background: '#1e3a8a', borderColor: '#1e3a8a', color: '#fff' },
  qText: { fontSize: 14, color: '#1a2540', lineHeight: 1.5 },
  qVisual: { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', textAlign: 'center' as const, padding: 24 },
  hexStack: { display: 'flex', flexDirection: 'column' as const, gap: 6 },
  qFoot: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 36, paddingTop: 24, borderTop: '1px solid rgba(26,37,64,0.1)' },
  // Method 2
  bmcPad: { maxWidth: 1100, margin: '0 auto', padding: '40px 60px 60px' },
  bmcH1: { fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', margin: '8px 0 20px' },
  bmcGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 24 },
  bmcCell: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 6, padding: '14px 16px', display: 'flex', flexDirection: 'column' as const, cursor: 'pointer', gap: 6 },
  bmcCellActive: { borderColor: '#1e3a8a', background: '#fff', boxShadow: 'inset 0 0 0 1px #1e3a8a' },
  bmcNum: { fontFamily: 'Georgia,serif', fontSize: 13, color: '#c0392b', letterSpacing: 1 },
  bmcTitle: { fontFamily: 'sans-serif', fontSize: 12, color: '#1a2540', fontWeight: 600, lineHeight: 1.35 },
  bmcScore: { display: 'flex', gap: 3, marginTop: 'auto' as const },
  bmcEditor: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: 24 },
  bmcEditNum: { fontFamily: 'Georgia,serif', fontSize: 12, color: '#c0392b', letterSpacing: 1 },
  bmcEditH3: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, color: '#1a2540', margin: '4px 0 8px' },
  bmcEditHelp: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', marginBottom: 20, lineHeight: 1.6 },
  bmcScale: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18, fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)' },
  scaleBtn: { width: 36, height: 36, border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, background: 'none', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#1a2540' },
  scaleBtnOn: { background: '#1e3a8a', color: '#fff', borderColor: '#1e3a8a' },
  bmcTextarea: { width: '100%', padding: '12px 16px', background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(26,37,64,0.15)', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', outline: 'none', resize: 'vertical' as const, lineHeight: 1.6, boxSizing: 'border-box' as const },
  // Waiting
  waitStage: { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', minHeight: 'calc(100vh - 56px)', textAlign: 'center' as const, padding: '48px 24px' },
  waitHex: { fontFamily: 'serif', fontSize: 96, color: '#1e3a8a', lineHeight: 1 },
  waitH2: { fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: '#1a2540', margin: '14px 0 12px' },
  waitText: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)', maxWidth: 480, lineHeight: 1.7, margin: '0 0 24px' },
  waitBar: { width: 320, height: 3, background: 'rgba(26,37,64,0.1)', borderRadius: 99, overflow: 'hidden', margin: '0 auto' },
  waitBarFill: { width: '60%', height: '100%', background: '#c0392b', borderRadius: 99, animation: 'none' },
  // Method 1 — финансовый блок
  finHead: { marginBottom: 20 },
  finLegend: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginTop: 10, lineHeight: 1.6 },
  finItem: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '16px 20px', marginBottom: 12 },
  finItemText: { fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', lineHeight: 1.55, marginBottom: 12 },
  finScaleRow: { display: 'flex', gap: 8, flexWrap: 'wrap' as const },
  finScaleBtn: { minWidth: 40, padding: '8px 14px', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, background: 'none', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', color: '#1a2540' },
  finScaleBtnOn: { background: '#1e3a8a', color: '#fff', borderColor: '#1e3a8a' },
  finUnknownOn: { background: 'rgba(26,37,64,0.55)', color: '#fff', borderColor: 'rgba(26,37,64,0.55)' },
  // Common
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 22px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', fontWeight: 500 },
  btnGhost: { background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '10px 22px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
}

export default function AssessmentPage() {
  return (
    <Suspense fallback={<div style={{minHeight:'100vh',background:'#e8e4db'}}><p>Загрузка...</p></div>}>
      <AssessmentInner />
    </Suspense>
  )
}

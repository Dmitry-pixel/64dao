import type { Metadata } from 'next'
import Link from 'next/link'
import './landing-b.css'
import SiteNav from '@/components/SiteNav'
import SiteFooter from '@/components/SiteFooter'
import ContactSection from '@/components/ContactSection'
import CookieBanner from '@/components/CookieBanner'
import LandingFonts from '@/components/LandingFonts'
import JsonLd from '@/components/JsonLd'
import SampleReportButton from '@/components/SampleReportButton'
import { buildFaqData, buildFaqSchema } from '@/lib/faqData'
import { getPricing, getPricingM3, formatPrice } from '@/lib/landingPricing'

const PAGE_TITLE = 'Стратегическая диагностика компании по 64 фазам «И-цзин» | 64 ДАО'
const PAGE_DESCRIPTION =
  'Стратегическая диагностика на основе «И-цзин»: определяет фазу компании, уместные управленческие решения, служит опорой для стратегических сессий.'

export const metadata: Metadata = {
  title: PAGE_TITLE,
  description: PAGE_DESCRIPTION,
}

const LAST_UPDATED = '2026-09-30'

const landingSchema = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      '@id': 'https://64dao.ru/#organization',
      name: '64 ДАО',
      url: 'https://64dao.ru',
      logo: 'https://64dao.ru/assets/logo.svg',
      description:
        'Стратегическая диагностика бизнеса на основе «И-цзин»: определяет фазу компании, уместные управленческие решения, служит опорой для стратегических сессий.',
    },
    {
      '@type': 'SoftwareApplication',
      '@id': 'https://64dao.ru/#software',
      name: '64 ДАО',
      url: 'https://64dao.ru',
      applicationCategory: 'BusinessApplication',
      operatingSystem: 'Web',
      description:
        'Онлайн-диагностика бизнеса на основе «И-цзин»: два метода оценки (6 бинарных вопросов и Business Model Canvas), результат — стратегический отчёт в PDF.',
    },
  ],
}

// ─── Метод 2: пример оценки 9 блоков ─────────────────────────────────────────

type DotTone = 'alert' | 'warn' | 'ok'
const DOT_COLOR: Record<DotTone, string> = { ok: '#1F8A5B', warn: '#E0A21B', alert: '#C0392B' }

function Dots({ value, tone }: { value: number; tone: DotTone }) {
  return (
    <div className="lb-dots" aria-label={`Оценка ${value} из 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} style={i <= value ? { background: DOT_COLOR[tone] } : undefined} />
      ))}
    </div>
  )
}

const canvasBlocks: { n: string; t: string; v: number; tone: DotTone }[] = [
  { n: '01', t: 'Ключевые партнёры', v: 4, tone: 'ok' },
  { n: '02', t: 'Ключевые активности', v: 3, tone: 'ok' },
  { n: '03', t: 'Ключевые ресурсы', v: 4, tone: 'ok' },
  { n: '04', t: 'Ценностное предложение', v: 5, tone: 'ok' },
  { n: '05', t: 'Отношения с клиентами', v: 3, tone: 'warn' },
  { n: '06', t: 'Каналы', v: 2, tone: 'alert' },
  { n: '07', t: 'Сегменты клиентов', v: 4, tone: 'ok' },
  { n: '08', t: 'Структура издержек', v: 3, tone: 'warn' },
  { n: '09', t: 'Потоки доходов', v: 4, tone: 'ok' },
]

// Гексаграмма 11 «Расцвет»: снизу три сплошные, сверху три прерывистые.
// Рисуем сверху вниз.
const HERO_HEX: ('yin' | 'yang')[] = ['yin', 'yin', 'yin', 'yang', 'yang', 'yang']

function HeroMap() {
  return (
    <div className="lb-map" aria-hidden="true">
      <svg viewBox="0 0 600 460" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="lbCurve" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#5B9EA6" stopOpacity="0.25" />
            <stop offset="0.3" stopColor="#5B9EA6" stopOpacity="1" />
            <stop offset="1" stopColor="#5B9EA6" stopOpacity="0.35" />
          </linearGradient>
        </defs>
        <path
          d="M40 360 C 110 358, 150 280, 190 230 S 250 130, 290 130 S 370 180, 410 240 S 470 310, 500 305 S 550 230, 565 190"
          fill="none"
          stroke="url(#lbCurve)"
          strokeWidth={4}
          strokeLinecap="round"
        />
        <path d="M40 395 H 565" stroke="rgba(248,244,236,0.12)" strokeDasharray="4 6" />
        {[[40, 360], [290, 130], [410, 240], [500, 305], [565, 190]].map(([cx, cy]) => (
          <circle key={cx} cx={cx} cy={cy} r={6} fill="#1E2A44" stroke="#5B9EA6" strokeWidth={2} />
        ))}
        <circle cx={190} cy={230} r={22} fill="none" stroke="#C0392B" strokeOpacity={0.35} strokeWidth={2} />
        <circle cx={190} cy={230} r={9} fill="#C0392B" />
        <g fontFamily="'Golos Text', sans-serif" fontSize={13} fill="#B9C2CE">
          <text x={14} y={420} textAnchor="start">Зарождение</text>
          <text x={190} y={420} textAnchor="middle" fill="#F8F4EC" fontWeight={600}>Рост</text>
          <text x={290} y={420} textAnchor="middle">Зрелость</text>
          <text x={410} y={420} textAnchor="middle">Спад</text>
          <text x={500} y={420} textAnchor="middle">Обновление</text>
          <text x={588} y={440} textAnchor="end">Новый цикл</text>
        </g>
      </svg>
      <div className="lb-map__card">
        <div className="lb-hex">
          {HERO_HEX.map((l, i) =>
            l === 'yang' ? (
              <div key={i} className="lb-hex__yang" />
            ) : (
              <div key={i} className="lb-hex__yin"><span /><span /></div>
            ),
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 12, color: '#5A6A7A' }}>Вы здесь · пример</span>
          <span className="lb-display" style={{ fontSize: 18, fontWeight: 800 }}>Фаза роста</span>
          <span style={{ fontSize: 13, color: '#C0392B', fontWeight: 600 }}>11 / 64 · ваша фаза</span>
        </div>
      </div>
    </div>
  )
}

function WheelMini() {
  const nodes = Array.from({ length: 10 }, (_, j) => {
    const a = -Math.PI / 2 + (j * 2 * Math.PI) / 10
    return {
      n: j + 1,
      left: Math.round((85 + 65 * Math.cos(a) - 13) * 10) / 10,
      top: Math.round((85 + 65 * Math.sin(a) - 13) * 10) / 10,
      key: j === 3,
      last: j === 9,
    }
  })
  return (
    <div className="lb-wheel" aria-hidden="true">
      <div className="lb-wheel__ring" />
      {nodes.map((w) => (
        <span
          key={w.n}
          className="lb-wheel__node"
          style={{
            left: w.left,
            top: w.top,
            ...(w.key ? { background: '#C0392B', color: '#FFFFFF' } : {}),
            ...(w.last ? { background: '#1E2A44', color: '#FFFFFF' } : {}),
          }}
        >
          {w.n}
        </span>
      ))}
    </div>
  )
}

function MatrixMini() {
  const fills = [0.2, 0.32, 0.5, 0.12, 0.2, 0.32, 0.06, 0.12, 0.2]
  return (
    <div className="lb-matrix" aria-hidden="true">
      {fills.map((f, i) => (
        <div key={i} style={{ background: `rgba(91,158,166,${f})` }}>
          {i === 4 && <span style={{ width: 14, height: 14, borderRadius: '50%', background: '#1E2A44' }} />}
          {i === 5 && (
            <span style={{ width: 14, height: 14, borderRadius: '50%', background: '#C0392B', boxShadow: '0 0 0 5px rgba(192,57,43,0.18)' }} />
          )}
        </div>
      ))}
    </div>
  )
}

const ICON = { fill: 'none', strokeWidth: 1.8, width: 20, height: 20, viewBox: '0 0 24 24', 'aria-hidden': true } as const

export default async function HomePage() {
  const year = new Date().getFullYear()
  const pricing = await getPricing()
  const pricingM3 = await getPricingM3()
  const priceFormatted = formatPrice(pricing)
  const priceLabel = `${priceFormatted} ${pricing.currency}`
  const priceM3Formatted = formatPrice(pricingM3)
  const faq = buildFaqData(priceLabel)

  const pageSchema = {
    ...landingSchema,
    '@graph': [
      ...landingSchema['@graph'],
      {
        '@type': 'WebPage',
        '@id': 'https://64dao.ru/#webpage',
        url: 'https://64dao.ru/',
        name: PAGE_TITLE,
        inLanguage: 'ru-RU',
        about: { '@id': 'https://64dao.ru/#software' },
        publisher: { '@id': 'https://64dao.ru/#organization' },
        dateModified: LAST_UPDATED,
      },
      {
        '@type': 'Service',
        '@id': 'https://64dao.ru/#service',
        name: 'Стратегическая диагностика 64 ДАО',
        serviceType: 'Стратегическая диагностика компании',
        provider: { '@id': 'https://64dao.ru/#organization' },
        areaServed: { '@type': 'Country', name: 'Россия' },
        audience: {
          '@type': 'BusinessAudience',
          audienceType:
            'Собственники бизнеса, CEO, топ-менеджеры, бизнес-консультанты и фасилитаторы стратегических сессий',
        },
        offers: {
          '@type': 'Offer',
          price: String(pricing.price),
          priceCurrency: 'RUB',
          availability: 'https://schema.org/InStock',
          url: 'https://64dao.ru/login',
        },
      },
      // FAQPage собирается из того же faqData, что и видимый блок ниже:
      // разметка и текст на странице совпадают дословно.
      buildFaqSchema(priceLabel),
    ],
  }

  return (
    <div id="top" className="landing-scope lb">
      <JsonLd data={pageSchema} />
      <LandingFonts />
      <SiteNav />

      <main>
        {/* ── HERO ── */}
        <section className="lb-hero">
          <div className="lb-wrap lb-hero__grid">
            <div className="lb-hero__text">
              <span className="lb-chip">Стратегическая диагностика · 64 фазы</span>
              <h1>Стратегическая диагностика компании по 64 фазам «И-цзин»</h1>
              <p className="lb-hero__sub">
                Где компания находится в цикле, что уместно сейчас и что преждевременно. На управленческом языке — готовая основа для стратегической сессии.
              </p>
              <div className="lb-hero__cta">
                <a href="/login" className="lb-btn lb-btn--red">Пройти диагностику <span aria-hidden="true">→</span></a>
                <SampleReportButton method="1" className="lb-btn lb-btn--ghost-light" style={{ background: 'transparent', border: '1px solid rgba(248,244,236,0.4)', fontFamily: 'inherit', fontSize: 17, fontWeight: 600 }}>
                  Образец отчёта
                </SampleReportButton>
              </div>
              <div className="lb-hero__meta">
                <span>{priceLabel}</span><span aria-hidden="true">·</span>
                <span>отчёт до 30 минут</span><span aria-hidden="true">·</span>
                <span>без знания «И-цзин»</span>
              </div>
            </div>
            <HeroMap />
          </div>
        </section>

        {/* ── ПОЛОСА ФАКТОВ ── */}
        <div className="lb-facts">
          <div className="lb-wrap">
            <div className="lb-facts__card">
              {[
                ['64', 'фазы цикла'],
                ['12', 'направлений разбора'],
                ['9', 'блоков бизнес-модели'],
                ['≤ 30 мин', 'готовность отчёта'],
                ['7 дней', 'обязательство по ясности'],
              ].map(([n, l]) => (
                <div key={l} className="lb-facts__item">
                  <span className="lb-facts__num">{n}</span>
                  <span className="lb-facts__label">{l}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── ЗНАКОМО? ── */}
        <section className="lb-sec lb-sec--cream" style={{ paddingTop: 56 }}>
          <div className="lb-wrap lb-symptoms">
            <div>
              <span className="lb-eyebrow">Знакомо?</span>
              <h2 className="lb-h2">Признаки того, что стратегии не хватает общей картины</h2>
              <p className="lb-lead">Стратегия живёт в одной голове. Решения — в режиме тушения пожаров.</p>
            </div>
            <div className="lb-grid2">
              <div className="lb-card">
                <span className="lb-icon"><svg {...ICON} stroke="#1E2A44"><path d="M4 6h16M4 12h10M4 18h6" /></svg></span>
                <h3>Сессии без выводов</h3>
                <p>Собрались, поспорили о прошлом квартале, разошлись. Решения — на следующий раз.</p>
              </div>
              <div className="lb-card">
                <span className="lb-icon lb-icon--red"><svg {...ICON} stroke="#C0392B"><path d="M4 7l6 6 4-4 6 6" /><path d="M14 15h6V9" /></svg></span>
                <h3>Слитые бюджеты</h3>
                <p>Запустили рекламу, вышли на рынок, масштабировались — а момент был не тот.</p>
              </div>
              <div className="lb-card">
                <span className="lb-icon"><svg {...ICON} stroke="#1E2A44"><path d="M12 12L5 5M12 12l7-7M12 12v8" /></svg></span>
                <h3>Команда тянет в разные стороны</h3>
                <p>У каждого своя картина, потому что общей точки сверки нет.</p>
              </div>
              <div className="lb-card">
                <span className="lb-icon"><svg {...ICON} stroke="#1E2A44"><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></svg></span>
                <h3>Стратегия — в одной голове</h3>
                <p>Компания едет без навигатора: а туда ли вообще едем?</p>
              </div>
            </div>
          </div>
        </section>

        {/* ── ЧТО ЭТО ── */}
        <section id="method" className="lb-sec lb-sec--white">
          <div className="lb-wrap">
            <div className="lb-center" style={{ maxWidth: 820, textAlign: 'center' }}>
              <span className="lb-eyebrow">Что это</span>
              <h2 className="lb-h2" style={{ fontSize: 'clamp(32px,3.8vw,46px)' }}>Это не гадание. Это диагностика фазы.</h2>
              <p className="lb-lead">
                64 ДАО использует структуру «И-цзин» — 64 состояния из шести линий — как карту циклов изменений. Инструмент не предсказывает будущее: он определяет фазу компании и переводит её в управленческие решения.
              </p>
            </div>
            <div className="lb-grid3" style={{ marginTop: 48 }}>
              {[
                ['01', 'Определяем фазу', 'Одна из 64 позиций на кривой развития компании.'],
                ['02', 'Что уместно сейчас', 'Какие действия поддерживают фазу, а какие преждевременны.'],
                ['03', 'Управленческий язык', 'Без иероглифов и мистики. Документ для стратегической сессии.'],
              ].map(([n, t, d]) => (
                <div key={n} className="lb-card lb-card--cream">
                  <span className="lb-num">{n}</span>
                  <h3>{t}</h3>
                  <p>{d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── КАК ПРОХОДИТ ДИАГНОСТИКА ── */}
        <section id="how" className="lb-sec lb-sec--cream">
          <div className="lb-wrap">
            <span className="lb-eyebrow">Как проходит диагностика</span>
            <h2 className="lb-h2">Три шага до точки сверки</h2>
            <div className="lb-steps">
              <svg className="lb-steps__path" viewBox="0 0 1200 40" preserveAspectRatio="none" aria-hidden="true">
                <path d="M30 20 C 200 -6, 260 46, 430 20 S 660 -6, 830 20 S 1060 46, 1180 20" fill="none" stroke="#5B9EA6" strokeWidth={2} strokeDasharray="2 8" strokeLinecap="round" />
              </svg>
              <div className="lb-step">
                <span className="lb-step__dot">01</span>
                <h3>6 вопросов — общая картина</h3>
                <p>Выбор из двух вариантов: растущий рынок или устоявшийся, рост или сокращение затрат. Никаких «опишите стратегию на 5 лет».</p>
              </div>
              <div className="lb-step">
                <span className="lb-step__dot">02</span>
                <h3>4 блока уточнений</h3>
                <p>Раскрывают детали и находят узкое место, которое задаёт скорость всей системы. Раздел о жизненном цикле открывается после всех четырёх.</p>
                <div className="lb-tags">
                  <span className="lb-tag">Финансы</span>
                  <span className="lb-tag">Продукт</span>
                  <span className="lb-tag">Процессы</span>
                  <span className="lb-tag">Рынок</span>
                </div>
              </div>
              <div className="lb-step">
                <span className="lb-step__dot lb-step__dot--red">03</span>
                <h3>Фаза и стратегический отчёт</h3>
                <p>Одна из 64 фаз, разбор по 12 направлениям и карта бизнес-модели. Готовый предмет для сессии, а не пустой лист.</p>
              </div>
            </div>
          </div>
        </section>

        {/* ── ЧТО ВХОДИТ В ОТЧЁТ ── */}
        <section id="report" className="lb-sec lb-sec--navy">
          <div className="lb-wrap lb-report">
            <div>
              <span className="lb-eyebrow">Что входит в отчёт</span>
              <h2 className="lb-h2">Не таблица слов. Карта вашего положения в цикле.</h2>
              <ul className="lb-report__list">
                <li><span className="lb-bullet" />Фаза и номер из 64, кривая цикла с меткой «Вы здесь»</li>
                <li><span className="lb-bullet" />Разбор по 12 направлениям</li>
                <li><span className="lb-bullet" />Блок «Инвестировать или подождать»</li>
                <li><span className="lb-bullet lb-bullet--red" />Бонус: бизнес-модель по 9 блокам (Метод 2)</li>
              </ul>
              <p className="lb-lead" style={{ margin: '0 0 20px', fontSize: 16 }}>Обезличенный образец отчёта доступен до оплаты.</p>
              <SampleReportButton method="1" className="lb-btn lb-btn--cream" style={{ background: '#F8F4EC', fontFamily: 'inherit', fontSize: 17, fontWeight: 600 }}>
                Скачать образец отчёта
              </SampleReportButton>
            </div>
            <div className="lb-sheet">
              <div className="lb-sheet__head"><span>Стратегический отчёт</span><span>стр. 04 / 28</span></div>
              <h3>Фаза 17. Удержание ядра в зреющем рынке</h3>
              <svg width="100%" height="90" viewBox="0 0 560 90" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <linearGradient id="lbSheet" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0" stopColor="#5B9EA6" stopOpacity="0.3" />
                    <stop offset="0.5" stopColor="#5B9EA6" />
                    <stop offset="1" stopColor="#5B9EA6" stopOpacity="0.3" />
                  </linearGradient>
                </defs>
                <path d="M0 80 C 90 78, 150 20, 250 16 S 420 60, 560 70" fill="none" stroke="url(#lbSheet)" strokeWidth={3} />
                <circle cx={300} cy={22} r={14} fill="none" stroke="#C0392B" strokeOpacity={0.35} strokeWidth={2} />
                <circle cx={300} cy={22} r={6} fill="#C0392B" />
              </svg>
              <div className="lb-sheet__cells">
                <div className="lb-sheet__cell"><b style={{ color: '#3E7F87' }}>УМЕСТНО</b>Фокус на ядре клиентов и удержании маржи</div>
                <div className="lb-sheet__cell"><b style={{ color: '#C0392B' }}>ПРЕЖДЕВРЕМЕННО</b>Смежные рынки и масштабная реклама</div>
                <div className="lb-sheet__cell"><b>ТОЧКА СВЕРКИ</b>Обсуждаем удержание, а не рост</div>
              </div>
            </div>
          </div>
        </section>

        {/* ── МЕТОД 2: БИЗНЕС-МОДЕЛЬ ПО 9 БЛОКАМ ── */}
        <section id="canvas" className="lb-sec lb-sec--cream">
          <div className="lb-wrap">
            <div className="lb-canvas__head">
              <div>
                <span className="lb-eyebrow">Метод 2 · в отчёте</span>
                <h2 className="lb-h2">Метод 2 — бизнес-модель по 9 блокам</h2>
              </div>
              <span className="lb-canvas__note">Бонус · в подарок · оценка 1–5</span>
            </div>
            <div className="lb-canvas">
              {canvasBlocks.map((b) => (
                <div key={b.n} className="lb-canvas__item">
                  <div>
                    <div className="lb-canvas__n">{b.n}</div>
                    <div className="lb-canvas__t">{b.t}</div>
                  </div>
                  <Dots value={b.v} tone={b.tone} />
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── СЛЕДУЮЩИЙ УРОВЕНЬ ── */}
        <section className="lb-sec lb-sec--white">
          <div className="lb-wrap">
            <div className="lb-head-row">
              <div style={{ maxWidth: 720 }}>
                <span className="lb-eyebrow">Следующий уровень</span>
                <h2 className="lb-h2">Матрица GE/McKinsey и Алмазное колесо: куда вкладывать и что мешает</h2>
              </div>
              <Link href="/methods" className="lb-btn lb-btn--soft">Подробнее о методах <span aria-hidden="true">→</span></Link>
            </div>
            <div className="lb-grid2" style={{ marginTop: 44 }}>
              <div className="lb-method">
                <div className="lb-method__vis"><MatrixMini /></div>
                <div className="lb-method__text">
                  <span className="lb-method__kicker">Метод 3</span>
                  <h3>Матрица силы</h3>
                  <p>Позиция бизнеса в логике GE/McKinsey плюс 64 состояния: где вы сегодня и куда сдвинется позиция при каких условиях.</p>
                </div>
              </div>
              <div className="lb-method">
                <div className="lb-method__vis"><WheelMini /></div>
                <div className="lb-method__text">
                  <span className="lb-method__kicker">Метод 4</span>
                  <h3>Алмазное колесо</h3>
                  <p>10 управленческих модулей: узел, который держит остальные, и пары решений, тянущие компанию в разные стороны.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── ДЛЯ КОГО И КАК ПРИМЕНЯЮТ ── */}
        <section id="audience" className="lb-sec lb-sec--cream">
          <div className="lb-wrap">
            <span className="lb-eyebrow">Для кого и как применяют</span>
            <h2 className="lb-h2">Как 64 ДАО используют на стратегических сессиях</h2>
            <div className="lb-grid2" style={{ marginTop: 44, alignItems: 'start' }}>
              <div className="lb-audience">
                <span className="lb-audience__tag">Собственникам и CEO</span>
                <h3>Это для вас, если</h3>
                <ul className="lb-checks">
                  <li>Вы собственник или CEO с реальным стратегическим запросом: рост, новый рынок, масштабирование, инвестиции, смена курса</li>
                  <li>Впереди стратегическая сессия или крупное решение, а общей картины «где мы сейчас» нет</li>
                  <li>Команда спорит о направлении, и каждый тянет в свою сторону</li>
                  <li>Вы цените внешнюю оптику, а не только собственную интуицию</li>
                </ul>
                <div className="lb-divider" />
                <div className="lb-case">
                  <h4>«Масштабироваться или укрепить ядро»</h4>
                  <p>Команда проходит диагностику до сессии. Спор «кто прав» сменяется вопросом «что уместно в этой фазе».</p>
                </div>
                <div className="lb-divider" />
                <div className="lb-case">
                  <h4>«Почему снова не сработал запуск»</h4>
                  <p>Запуски разбираются через «Инвестировать или подождать». Фокус смещается с исполнения на тайминг решений.</p>
                </div>
              </div>
              <div className="lb-audience">
                <span className="lb-audience__tag lb-audience__tag--teal">Для консультантов и фасилитаторов</span>
                <h3>Начинайте сессию не с хаоса мнений, а с готовой диагностики</h3>
                <ul className="lb-checks">
                  <li>Вы подаёте не гадание, а входную диагностику фазы компании — деловой инструмент.</li>
                  <li>Отчёт — не конец, а дверь: к сессии, сопровождению, регулярной работе с собственником.</li>
                  <li>В комплекте — скрипт подачи клиенту: как представить отчёт деловым языком и в какой момент сессии его подать.</li>
                </ul>
                <div className="lb-divider" />
                <div className="lb-case">
                  <h4>Вход в проект</h4>
                  <p>Клиент проходит диагностику до первой встречи. Разговор начинается со сверки по фазе, а не с «расскажите о бизнесе».</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── СТОИМОСТЬ ── */}
        <section id="price" className="lb-sec lb-sec--white">
          <div className="lb-wrap">
            <div className="lb-center" style={{ maxWidth: 760, textAlign: 'center' }}>
              <span className="lb-eyebrow">Стоимость</span>
              <h2 className="lb-h2" style={{ fontSize: 'clamp(30px,3.6vw,44px)' }}>Стоимость стратегической диагностики</h2>
              <p className="lb-lead">
                Стратегическая консультация в России — от 300 000 ₽. Один день сессии «ни о чём» или один слитый рекламный бюджет стоят кратно дороже.
              </p>
            </div>
            <div className="lb-grid2 lb-prices" style={{ marginTop: 44, gap: 24 }}>
              <div className="lb-price lb-price--dark">
                <div className="lb-price__top">
                  <span className="lb-price__kicker">Оплата диагностики</span>
                  <span className="lb-price__badge">Начать с этого</span>
                </div>
                <h3>{pricing.title}</h3>
                <div className="lb-price__amount"><b>{priceFormatted} {pricing.currency}</b><span>{pricing.description}</span></div>
                <div className="lb-price__rows">
                  {pricing.features.map((row) => (
                    <div key={row.label} className="lb-price__row"><span>{row.label}</span><span>{row.value}</span></div>
                  ))}
                </div>
                <a href="/login" className="lb-btn lb-btn--red lb-btn--block">Перейти к оплате <span aria-hidden="true">→</span></a>
              </div>
              <div className="lb-price lb-price--light">
                <div className="lb-price__top">
                  <span className="lb-price__kicker">Оплата диагностики</span>
                </div>
                <h3>{pricingM3.title}</h3>
                <div className="lb-price__amount"><b>{priceM3Formatted} {pricingM3.currency}</b><span>{pricingM3.description}</span></div>
                <div className="lb-price__rows">
                  {pricingM3.features.map((row) => (
                    <div key={row.label} className="lb-price__row"><span>{row.label}</span><span>{row.value}</span></div>
                  ))}
                </div>
                <a href="/login?next=/m3" className="lb-btn lb-btn--ghost-dark lb-btn--block">Перейти к оплате <span aria-hidden="true">→</span></a>
                <p className="lb-price__foot">Оплата оформляется в личном кабинете: заказ привязывается к вашей учётной записи.</p>
              </div>
            </div>
            <p className="lb-promise">
              <b>Обязательство по ясности.</b> Мы не обещаем рост выручки и не принимаем за вас стратегические решения — это зона вашей ответственности. Но мы отвечаем за то, что отчёт будет понятным и пригодным как рамка для разговора о стратегии. Если он окажется неясным — напишите в течение 7 дней, и мы бесплатно дадим короткий разбор-комментарий по вашему отчёту.
            </p>
          </div>
        </section>

        {/* ── КОНТАКТЫ (форма, как в исходном дизайне) ── */}
        <ContactSection />

        {/* ── ПОЧЕМУ ДИАГНОСТИКА ИДЁТ ПЕРВОЙ ── */}
        <section className="lb-sec lb-sec--navy">
          <div className="lb-wrap">
            <div className="lb-quote">
              <span className="lb-eyebrow">Почему диагностика идёт первой</span>
              <div className="lb-quote__mark" aria-hidden="true" style={{ marginTop: 36 }}>“</div>
              <p>
                Стратегия, выстроенная без понимания текущей фазы, — это аккуратно оформленные предположения. Сверку имеет смысл проходить до решения, а не объяснять задним числом, почему прошлый шаг не сработал.
              </p>
              <div className="lb-quote__sign">Принцип 64 ДАО</div>
            </div>
          </div>
        </section>

        {/* ── FAQ (ответы всегда в HTML: details/summary без состояния) ── */}
        <section id="faq" className="lb-sec lb-sec--cream">
          <div className="lb-wrap">
            <div className="lb-head-row">
              <div>
                <span className="lb-eyebrow">Честные ответы</span>
                <h2 className="lb-h2">Частые вопросы о диагностике 64 ДАО</h2>
              </div>
              <Link href="/method" className="lb-btn lb-btn--soft" style={{ background: '#FFFFFF' }}>Методика 64 ДАО <span aria-hidden="true">→</span></Link>
            </div>
            <div className="lb-faq">
              {faq.map((item, i) => (
                <details key={i} open={i === 0}>
                  <summary>
                    <h3>{item.q}</h3>
                    <span className="lb-faq__sign" aria-hidden="true" />
                  </summary>
                  <p>{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* ── ПАРТНЁРСКИЙ ПРОЕКТ ── */}
        <section className="lb-sec lb-sec--white" style={{ paddingTop: 88, paddingBottom: 88 }}>
          <div className="lb-wrap">
            <div className="lb-partner">
              <div className="lb-partner__text">
                <span className="lb-partner__kicker">Партнёрский проект</span>
                <h3>taoteam.ru — функциональная диагностика команд</h3>
                <p>
                  Если 64 ДАО показывает фазу компании, то taoteam.ru разбирает команду: роли, дефициты и зоны напряжения. Два инструмента работают вместе — стратегия и команда в одной рамке.
                </p>
              </div>
              <a href="https://taoteam.ru" target="_blank" rel="noreferrer" className="lb-btn lb-btn--navy">
                Перейти на taoteam.ru <span aria-hidden="true">→</span>
              </a>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter year={year} />
      <CookieBanner />
    </div>
  )
}

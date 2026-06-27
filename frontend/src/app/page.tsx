import type { Metadata } from 'next'
import Link from 'next/link'
import SiteNav from '@/components/SiteNav'
import SiteFooter from '@/components/SiteFooter'
import HeroSection from '@/components/HeroSection'
import FaqSection from '@/components/FaqSection'
import ContactSection from '@/components/ContactSection'
import CookieBanner from '@/components/CookieBanner'
import LandingFonts from '@/components/LandingFonts'

export const metadata: Metadata = {
  title: '64 ДАО — «И-цзин» для стратегии компании',
  description:
    'Стратегическая диагностика на основе «И-цзин»: определяет фазу компании, уместные управленческие решения, служит опорой для стратегических сессий.',
}

// ─── Server-side helpers для секции «Что в отчёте» ───────────────────────────

type DotTone = 'alert' | 'warn' | 'ok'

function Dots({ value, tone }: { value: number; tone: DotTone }) {
  const color =
    tone === 'alert'
      ? 'var(--accent)'
      : tone === 'warn'
      ? 'oklch(0.78 0.16 75)'
      : 'oklch(0.55 0.13 160)'
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          style={{
            height: 8,
            width: 8,
            borderRadius: '9999px',
            background: i <= value ? color : 'var(--muted)',
          }}
        />
      ))}
    </div>
  )
}

function CycleCurve() {
  const labels: { x: number; l: string; bold?: boolean }[] = [
    { x: 70, l: 'ЗАРОЖДЕНИЕ' },
    { x: 220, l: 'РОСТ', bold: true },
    { x: 380, l: 'ЗРЕЛОСТЬ' },
    { x: 530, l: 'СПАД' },
  ]
  return (
    <svg viewBox="0 0 600 220" style={{ height: 'auto', width: '100%' }}>
      <path
        d="M10 180 C 80 180, 130 60, 220 60 C 310 60, 340 200, 430 200 C 500 200, 540 100, 590 80"
        fill="none"
        stroke="oklch(0.28 0.08 260)"
        strokeWidth={2.2}
        strokeLinecap="round"
      />
      <path
        d="M590 80 L 596 78"
        fill="none"
        stroke="oklch(0.28 0.08 260)"
        strokeWidth={2}
        strokeDasharray="3 4"
      />
      <circle cx={220} cy={60} r={18} fill="oklch(0.28 0.08 260)" opacity={0.08} />
      <circle cx={220} cy={60} r={6} fill="var(--accent)" />
      <text
        x={220}
        y={36}
        textAnchor="middle"
        fontSize={11}
        fill="var(--accent)"
        style={{ letterSpacing: '0.18em' }}
      >
        ВЫ ЗДЕСЬ
      </text>
      <line x1={10} y1={200} x2={590} y2={200} stroke="oklch(0.86 0.02 92)" />
      {labels.map((t) => (
        <text
          key={t.l}
          x={t.x}
          y={216}
          textAnchor="middle"
          fontSize={10}
          fill={t.bold ? 'oklch(0.16 0.03 260)' : 'oklch(0.45 0.03 260)'}
          fontWeight={t.bold ? 600 : 400}
          style={{ letterSpacing: '0.18em' }}
        >
          {t.l}
        </text>
      ))}
    </svg>
  )
}

function GaugeSvg() {
  // cx=100 cy=100 r=78 — фиксированные значения
  return (
    <svg viewBox="0 0 200 130" style={{ height: 'auto', width: '100%', maxWidth: 220 }}>
      {/* левый сектор — «Рискованно» */}
      <path d="M 22 100 A 78 78 0 0 1 75.82 25.9" fill="none" stroke="oklch(0.6 0.22 27)" strokeWidth={14} />
      {/* центральный сектор — «Взвешенно» */}
      <path d="M 75.82 25.9 A 78 78 0 0 1 124.18 25.9" fill="none" stroke="oklch(0.78 0.16 75)" strokeWidth={14} />
      {/* правый сектор — «Инвестировать» */}
      <path d="M 124.18 25.9 A 78 78 0 0 1 178 100" fill="none" stroke="oklch(0.55 0.13 160)" strokeWidth={14} />
      {/* стрелка */}
      <g transform="rotate(40 100 100)">
        <line x1={100} y1={100} x2={170} y2={100} stroke="oklch(0.16 0.03 260)" strokeWidth={3} strokeLinecap="round" />
      </g>
      <circle cx={100} cy={100} r={6} fill="oklch(0.16 0.03 260)" />
    </svg>
  )
}

const reportBlocks: { n: string; t: string; v: number; tone: DotTone }[] = [
  { n: '01', t: 'Ключевые партнёры',      v: 4, tone: 'ok'    },
  { n: '02', t: 'Ключевые активности',    v: 3, tone: 'ok'    },
  { n: '03', t: 'Ключевые ресурсы',       v: 4, tone: 'ok'    },
  { n: '04', t: 'Ценностное предложение', v: 5, tone: 'ok'    },
  { n: '05', t: 'Отношения с клиентами',  v: 3, tone: 'warn'  },
  { n: '06', t: 'Каналы',                 v: 2, tone: 'alert' },
  { n: '07', t: 'Сегменты клиентов',      v: 4, tone: 'ok'    },
  { n: '08', t: 'Структура издержек',     v: 3, tone: 'warn'  },
  { n: '09', t: 'Потоки доходов',         v: 4, tone: 'ok'    },
]

// ─── Компонент страницы ───────────────────────────────────────────────────────

// ─── Тип и дефолт для блока цены (GET /api/pricing) ──────────────────────────

interface PricingData {
  title: string
  price: number
  currency: string
  description: string
  features: { label: string; value: string }[]
}

const DEFAULT_PRICING: PricingData = {
  title: 'Полный отчёт 64 ДАО',
  price: 14900,
  currency: '₽',
  description: 'разовая оплата · НДС не облагается',
  features: [
    { label: 'Диагностика', value: 'Метод 1 + Метод 2' },
    { label: 'PDF-отчёт', value: 'Включён' },
    { label: 'Онлайн-просмотр', value: 'Без ограничений' },
    { label: 'Срок готовности', value: 'До 30 минут' },
  ],
}

async function getPricing(): Promise<PricingData> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
    const res = await fetch(`${apiUrl}/api/pricing`, { next: { revalidate: 300 } })
    if (res.ok) {
      const data = await res.json()
      return {
        title: data.title ?? DEFAULT_PRICING.title,
        price: data.price ?? DEFAULT_PRICING.price,
        currency: data.currency ?? DEFAULT_PRICING.currency,
        description: data.description ?? DEFAULT_PRICING.description,
        features: Array.isArray(data.features) && data.features.length > 0 ? data.features : DEFAULT_PRICING.features,
      }
    }
  } catch {
    // используем дефолт ниже
  }
  return DEFAULT_PRICING
}

export default async function HomePage() {
  const year = new Date().getFullYear()
  const pricing = await getPricing()
  const priceFormatted = pricing.price.toLocaleString('ru-RU')

  return (
    <div className="landing-scope" style={{ fontFamily: 'Inter, sans-serif', color: 'var(--foreground)', background: 'var(--background)' }}>
      <LandingFonts />
      <SiteNav />

      <main style={{ minHeight: '100vh' }}>

        {/* ── HERO ── */}
        <HeroSection />

        {/* ── PROBLEM ── */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'color-mix(in oklab, var(--muted) 40%, var(--background))' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
              <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
              <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>Знакомо?</span>
            </div>
            <h2 style={{ margin: 0, maxWidth: 820, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(28px,4.5vw,44px)', lineHeight: 1.15, color: 'var(--foreground)' }}>
              Дело не в слабой команде. Дело в том, что все приходят без общей картины.
            </h2>
            <p style={{ marginTop: 24, maxWidth: 720, fontSize: 17, lineHeight: 1.7, color: '#4A4A4A' }}>
              Стратегия живёт в голове собственника. Решения принимаются в режиме тушения пожаров — и каждое «логичное» из них тихо сливает бюджет.
            </p>
            <div style={{ width: 60, height: 2, background: 'var(--accent)', marginTop: 40 }} />
            <div style={{ fontSize: 14, fontStyle: 'italic', color: '#888888', marginTop: 40, marginBottom: 20 }}>4 типичных симптома</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
              {[
                { title: 'Сессии без выводов',            desc: 'Собрались, поспорили о прошлом квартале, разошлись. Решения — на следующий раз.' },
                { title: 'Слитые бюджеты',                desc: 'Запустили рекламу, вышли на рынок, масштабировались — а момент был не тот.' },
                { title: 'Команда тянет в разные стороны', desc: 'У каждого своя картина, потому что общей точки сверки нет.' },
                { title: 'Стратегия — в одной голове',    desc: 'Вы ведёте компанию как будто без навигатора: а туда ли вообще едем?' },
              ].map((item) => (
                <div
                  key={item.title}
                  style={{ borderRadius: 2, background: 'color-mix(in oklab, var(--muted) 70%, #000 6%)', borderLeft: '3px solid var(--accent)', padding: '32px 32px 32px 28px' }}
                >
                  <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: 'var(--foreground)' }}>{item.title}</h3>
                  <p style={{ margin: '14px 0 0', fontSize: 15, color: '#5A5A5A', lineHeight: 1.65 }}>{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── SOLUTION ── */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 880, margin: '0 auto', padding: '100px 40px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
              <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>Что это</span>
            </div>
            <h2 style={{ margin: '24px 0 0', fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(28px,4vw,40px)', fontWeight: 700, lineHeight: 1.2, color: 'var(--foreground)' }}>
              Это не гадание. Это диагностика фазы.
            </h2>
            <p style={{ marginTop: 32, fontSize: 18, lineHeight: 1.8, color: '#3A3A3A' }}>
              64 ДАО не предсказывает будущее и не обещает «правильный ответ». Он определяет, в какой фазе цикла находится компания сейчас, что для этой фазы уместно, а что преждевременно — и формулирует это на управленческом языке.
            </p>
            <p style={{ marginTop: 16, fontSize: 18, lineHeight: 1.8, color: '#3A3A3A' }}>Без иероглифов и мистики.</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 40, marginTop: 40 }}>
              {[
                {
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polygon points="16.2 7.8 13.4 13.4 7.8 16.2 10.6 10.6 16.2 7.8" fill="var(--accent)" stroke="none" />
                    </svg>
                  ),
                  label: 'Определяем фазу',
                },
                {
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <circle cx="12" cy="12" r="6" />
                      <circle cx="12" cy="12" r="2" fill="var(--accent)" stroke="none" />
                    </svg>
                  ),
                  label: 'Что уместно сейчас',
                },
                {
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 0 1-.9-3.8A8.38 8.38 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z" />
                    </svg>
                  ),
                  label: 'Управленческий язык',
                },
              ].map((item) => (
                <div key={item.label} style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
                  {item.icon}
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#3A3A3A', lineHeight: 1.35 }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── HOW ── */}
        <section id="how" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'color-mix(in oklab, var(--muted) 40%, var(--background))' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
              Как это работает
            </div>
            <h2 style={{ margin: 0, maxWidth: 760, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>
              Три шага до точки сверки
            </h2>
            <div style={{ marginTop: 56, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px,1fr))', gap: 32 }}>
              {[
                {
                  n: '01',
                  title: '6 простых вопросов',
                  desc: 'Выбираете из двух вариантов: растущий рынок или устоявшийся, рост или сокращение затрат. Никаких «опишите стратегию на 5 лет».',
                },
                {
                  n: '02',
                  title: 'Определяется фаза',
                  desc: 'Ответы складываются в одну из 64 фаз — как доктор ставит диагноз: где вы на кривой прямо сейчас.',
                },
                {
                  n: '03',
                  title: 'Стратегический отчёт',
                  desc: 'Разбор по 12 направлениям плюс карта бизнес-модели. Готовый предмет для стратегической сессии, а не пустой лист.',
                },
              ].map((step) => (
                <div key={step.n} style={{ borderTop: '1px solid var(--foreground)', paddingTop: 24 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--accent)' }}>{step.n}</div>
                  <h3 style={{ margin: '16px 0 0', fontSize: 20, fontWeight: 600, color: 'var(--foreground)' }}>{step.title}</h3>
                  <p style={{ margin: '12px 0 0', fontSize: 14, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── REPORT ── */}
        <section id="report" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, marginBottom: 20, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
              <span style={{ height: 1, width: 32, background: 'rgba(0,0,0,0.3)' }} />Что внутри отчёта
            </div>
            <h2 style={{ margin: 0, maxWidth: 760, fontFamily: 'Inter,sans-serif', fontSize: 'clamp(32px,4.6vw,48px)', fontWeight: 700, lineHeight: 1.1, letterSpacing: '-0.01em', color: 'var(--foreground)' }}>
              Не таблица слов.<br />Карта вашего положения в цикле.
            </h2>
            <p style={{ marginTop: 20, fontSize: 16, color: 'var(--muted-foreground)' }}>Пример обезличенного заключения доступен до оплаты.</p>

            <div style={{ marginTop: 48, borderRadius: 2, border: '1px solid var(--border)', background: 'var(--card)', boxShadow: '0 30px 80px -50px rgba(20,30,60,0.35)', overflow: 'hidden' }}>
              <div style={{ borderBottom: '1px solid var(--border)', padding: '24px 32px' }}>
                <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--accent)' }}>Отчёт · фаза определена</div>
                <div style={{ marginTop: 8, display: 'flex', alignItems: 'baseline', gap: 12 }}>
                  <h3 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: 'var(--foreground)' }}>Фаза роста</h3>
                  <span style={{ fontSize: 14, color: 'var(--muted-foreground)' }}>· 11 / 64</span>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 1, background: 'var(--border)' }}>
                <div style={{ background: 'var(--card)', padding: 32 }}>
                  <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--muted-foreground)' }}>Где вы на кривой цикла</div>
                  <div style={{ marginTop: 32 }}><CycleCurve /></div>
                </div>
                <div style={{ background: 'var(--card)', padding: 32 }}>
                  <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--muted-foreground)' }}>Инвестировать или подождать</div>
                  <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <GaugeSvg />
                    <div style={{ marginTop: 8, fontSize: 20, fontWeight: 600, color: 'oklch(0.45 0.13 160)' }}>Инвестировать</div>
                    <p style={{ marginTop: 12, textAlign: 'center', fontSize: 14, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>
                      в масштаб — момент попутный.<br />Преждевременно: резать затраты.
                    </p>
                  </div>
                </div>
              </div>
              <div style={{ borderTop: '1px solid var(--border)', background: 'color-mix(in oklab, var(--background) 40%, var(--card))', padding: 32 }}>
                <div style={{ marginBottom: 24, display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
                  <h4 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--foreground)' }}>Метод 2 — бизнес-модель по 9 блокам</h4>
                  <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--accent)' }}>бонус · в подарок · оценка 1–5</div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px,1fr))', gap: 12 }}>
                  {reportBlocks.map((b) => (
                    <div key={b.n} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: 2, border: '1px solid var(--border)', background: 'var(--card)', padding: '16px 20px' }}>
                      <div>
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--muted-foreground)' }}>{b.n}</div>
                        <div style={{ marginTop: 4, fontSize: 14, fontWeight: 600, color: 'var(--foreground)' }}>{b.t}</div>
                      </div>
                      <Dots value={b.v} tone={b.tone} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── EXAMPLE ── */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'var(--brand-navy)', color: 'var(--background)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gridTemplateColumns: '0.85fr 1.15fr', gap: 48, padding: '96px 40px' }}>
            <div>
              <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.6)' }}>Пример отчёта</div>
              <h2 style={{ margin: 0, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: '#ffffff' }}>
                Посмотрите образец заключения до оплаты
              </h2>
              <p style={{ marginTop: 24, maxWidth: 420, fontSize: 16, lineHeight: 1.6, color: 'rgba(255,255,255,0.7)' }}>
                Обезличенный отчёт реальной компании — пролистайте структуру, тон и глубину разбора, чтобы решать осознанно, а не вслепую.
              </p>
              {/* TODO: заменить на /api/sample-report, когда backend-эндпоинт будет готов (отдельный шаг) */}
              <a href="/api/sample-report" style={{ marginTop: 40, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 2, background: 'var(--background)', padding: '14px 24px', fontSize: 14, fontWeight: 500, color: 'var(--foreground)', textDecoration: 'none' }}>
                Скачать пример отчёта
              </a>
            </div>
            <div>
              <div style={{ borderRadius: 2, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.04)', padding: 32 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.5)' }}>
                  <span>Стратегический отчёт</span><span>Стр. 04 / 28</span>
                </div>
                <h3 style={{ margin: '24px 0 0', fontFamily: "'Golos Text',sans-serif", fontSize: 24, lineHeight: 1.2, color: '#ffffff' }}>
                  Фаза 17. Удержание ядра в зреющем рынке
                </h3>
                <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12, fontSize: 14, lineHeight: 1.6, color: 'rgba(255,255,255,0.75)' }}>
                  <p style={{ margin: 0 }}><span style={{ color: 'var(--accent)' }}>Уместно сейчас.</span> Сфокусироваться на ядре клиентов и удержании маржи. Точечно усиливать сильные продукты.</p>
                  <p style={{ margin: 0 }}><span style={{ color: 'var(--accent)' }}>Преждевременно.</span> Выход на смежные рынки и масштабная рекламная экспансия. Высокая вероятность вернуться с ослабленным ядром.</p>
                  <p style={{ margin: 0 }}><span style={{ color: 'var(--accent)' }}>Точка сверки для команды.</span> Договориться, что обсуждаем удержание, а не рост — и пересобрать KPI отдела продаж под эту рамку.</p>
                </div>
                <div style={{ marginTop: 32, display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, borderTop: '1px solid rgba(255,255,255,0.15)', paddingTop: 24, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgba(255,255,255,0.5)' }}>
                  <span>Диагноз</span><span>Навигация</span><span>Решение</span><span>Метод 2</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── FOR WHOM ── */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>Квалификация</div>
            <h2 style={{ margin: 0, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>Для кого это</h2>
            <div style={{ marginTop: 48, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px,1fr))', gap: 32 }}>
              <div style={{ borderRadius: 2, border: '1px solid var(--border)', background: 'var(--card)', padding: 32 }}>
                <div style={{ fontSize: 14, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)' }}>Это для вас, если</div>
                <ul style={{ margin: '24px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {[
                    'Вы собственник или CEO с реальным стратегическим запросом: рост, новый рынок, масштабирование, инвестиции, смена курса',
                    'Впереди стратегическая сессия или крупное решение, а общей картины «где мы сейчас» нет',
                    'Команда спорит о направлении, и каждый тянет в свою сторону',
                    'Вы цените внешнюю оптику, а не только собственную интуицию',
                  ].map((text) => (
                    <li key={text} style={{ display: 'flex', gap: 12, fontSize: 14, lineHeight: 1.6, color: 'var(--foreground)' }}>
                      <span style={{ marginTop: 8, height: 6, width: 6, flexShrink: 0, borderRadius: '9999px', background: 'var(--accent)' }} />
                      {text}
                    </li>
                  ))}
                </ul>
              </div>
              <div style={{ borderRadius: 2, border: '1px solid var(--border)', background: 'var(--card)', padding: 32 }}>
                <div style={{ fontSize: 14, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)' }}>Что вы получите</div>
                <ul style={{ margin: '24px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {[
                    'Получите ясную карту текущей фазы цикла вашей компании',
                    'Увидите следующий разумный шаг — без догадок и обещаний «единственно верного» решения',
                    'Получите внешнюю оптику, которая помогает скорректировать курс вовремя',
                  ].map((text) => (
                    <li key={text} style={{ display: 'flex', gap: 12, fontSize: 14, lineHeight: 1.6, color: 'var(--foreground)' }}>
                      <span style={{ marginTop: 8, height: 6, width: 6, flexShrink: 0, borderRadius: '9999px', background: 'var(--accent)' }} />
                      {text}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ── FAQ ── */}
        <FaqSection priceLabel={`${priceFormatted} ${pricing.currency}`} />

        {/* ── PRICE ── */}
        <section id="price" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gridTemplateColumns: '0.85fr 1.15fr', gap: 80, padding: '96px 40px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
                <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>Стоимость</span>
              </div>
              <h2 style={{ margin: '24px 0 0', fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(28px,4vw,38px)', fontWeight: 700, lineHeight: 1.2, color: 'var(--foreground)' }}>
                Дешевле одного неудачного решения
              </h2>
              <div style={{ width: 80, height: 3, background: 'var(--accent)', margin: '28px 0' }} />
              <p style={{ margin: 0, maxWidth: 420, fontSize: 16, lineHeight: 1.75, color: '#4A4A4A' }}>
                Стратегическая консультация в России — от 300 000 ₽. Один день сессии «ни о чём» или один слитый рекламный бюджет стоят кратно дороже.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 32 }}>
                <span style={{ fontSize: 22, color: '#999999', textDecoration: 'line-through' }}>300 000 ₽</span>
                <span style={{ fontSize: 20, color: '#888888' }}>→</span>
                <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent)' }}>{priceFormatted} {pricing.currency}</span>
              </div>
            </div>
            <div>
              <div style={{ background: 'color-mix(in oklab, var(--muted) 70%, #000 6%)', borderRadius: 8, padding: '48px 40px', boxShadow: '0 4px 24px rgba(0,0,0,0.06)', textAlign: 'center' }}>
                <div style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#9a9a9a' }}>Оплата диагностики</div>
                <h3 style={{ margin: '14px 0 0', fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(28px,3.6vw,34px)', fontWeight: 700, lineHeight: 1.1, color: 'var(--foreground)' }}>
                  {pricing.title}
                </h3>
                <div style={{ marginTop: 28, display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 8 }}>
                  <span style={{ fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(56px,9vw,80px)', fontWeight: 800, lineHeight: 1, color: 'var(--foreground)', letterSpacing: '-0.01em' }}>{priceFormatted}</span>
                  <span style={{ fontSize: 32, fontWeight: 500, color: '#9a9a9a' }}>{pricing.currency}</span>
                </div>
                <div style={{ marginTop: 16, fontSize: 14, color: '#888888' }}>{pricing.description}</div>
                <div style={{ borderTop: '1px solid rgba(0,0,0,0.1)', margin: '32px 0 4px' }} />
                <div style={{ textAlign: 'left' }}>
                  {pricing.features.map((row) => (
                    <div key={row.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '18px 0', borderBottom: '1px solid rgba(0,0,0,0.08)' }}>
                      <span style={{ fontSize: 15, color: '#6A6A6A' }}>{row.label}</span>
                      <span style={{ fontSize: 15, fontWeight: 500, color: 'var(--foreground)' }}>{row.value}</span>
                    </div>
                  ))}
                </div>
                <a href="/login" style={{ marginTop: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, width: '100%', borderRadius: 6, background: '#8597C6', padding: '18px 24px', fontSize: 16, fontWeight: 500, color: '#ffffff', textDecoration: 'none' }}>
                  Перейти к оплате <span aria-hidden="true">→</span>
                </a>
              </div>
              <div style={{ marginTop: 24, background: 'color-mix(in oklab, var(--muted) 70%, #000 6%)', borderRadius: 8, padding: '28px 32px', boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#888888" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>Обязательство по ясности</div>
                </div>
                <p style={{ margin: '14px 0 0', fontSize: 14, lineHeight: 1.75, color: '#555555' }}>
                  Мы не обещаем рост выручки и не принимаем за вас стратегические решения — это зона вашей ответственности. Но мы отвечаем за то, что отчёт будет понятным и пригодным как рамка для разговора о стратегии. Если он окажется неясным — напишите в течение 7 дней, и мы бесплатно дадим короткий разбор-комментарий по вашему отчёту.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── WHY FIRST ── */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'color-mix(in oklab, var(--muted) 40%, var(--background))' }}>
          <div style={{ maxWidth: 1100, margin: '0 auto', padding: '100px 40px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
              <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>Почему диагностика идёт первой</span>
            </div>
            <div style={{ marginTop: 32, maxWidth: 880 }}>
              <div style={{ fontFamily: 'Georgia,serif', fontSize: 72, lineHeight: 0.6, color: 'var(--accent)', opacity: 0.3, marginBottom: 8 }}>"</div>
              <p style={{ margin: 0, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(20px,2.6vw,28px)', fontWeight: 500, lineHeight: 1.5, color: '#1A1A1A' }}>
                Стратегия, выстроенная без понимания текущей фазы, — это аккуратно оформленные предположения. Сверку имеет смысл проходить до решения, а не объяснять задним числом, почему прошлый шаг не сработал.
              </p>
              <div style={{ marginTop: 40 }}>
                <div style={{ width: 40, height: 2, background: '#CCCCCC' }} />
                <div style={{ fontSize: 14, fontStyle: 'italic', color: '#888888', marginTop: 12 }}>Принцип 64 ДАО</div>
              </div>
            </div>
          </div>
        </section>

        {/* ── CONSULTANTS ── */}
        <section id="consultants" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gridTemplateColumns: '0.85fr 1.15fr', gap: 48, padding: '96px 40px' }}>
            <div>
              <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>Для консультантов и фасилитаторов</div>
              <h2 style={{ margin: 0, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>
                Начинайте сессию не с хаоса мнений, а с готовой диагностики
              </h2>
              <p style={{ marginTop: 24, maxWidth: 420, fontSize: 16, color: 'var(--muted-foreground)' }}>
                Входной инструмент, который отличает вас от тех, кто работает только со SWOT и Canvas. Клиент говорит «давайте разберём подробнее» — и это вход к сессии и сопровождению.
              </p>
            </div>
            <div>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 20 }}>
                {[
                  'Вы подаёте не гадание, а входную диагностику фазы компании — деловой инструмент.',
                  'Отчёт — не конец, а дверь: к сессии, сопровождению, регулярной работе с собственником.',
                  'Отличие от SWOT и Canvas — вы приходите с тем, чего у клиента раньше не было.',
                  'В комплекте — скрипт подачи клиенту: как представить отчёт деловым языком и в какой момент сессии его подать.',
                ].map((text) => (
                  <li key={text} style={{ display: 'flex', gap: 16, borderTop: '1px solid var(--border)', paddingTop: 20, fontSize: 16, lineHeight: 1.6, color: 'var(--foreground)' }}>
                    <span style={{ marginTop: 8, height: 1, width: 32, flexShrink: 0, background: 'var(--accent)' }} />
                    {text}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── ABOUT TEASER ── */}
        <section id="about" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gridTemplateColumns: '0.5fr 1fr', gap: 48, padding: '96px 40px' }}>
            <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>О нас</div>
            <div>
              <h2 style={{ margin: 0, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>Команда 64 ДАО</h2>
              <p style={{ marginTop: 24, maxWidth: 680, fontSize: 16, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>
                Мы соединяем метафизику «И-цзин» с практикой стратегического управления. 64 ДАО — это инструмент, который помогает собственникам и консультантам опираться на структуру цикла, а не на догадки.
              </p>
              <Link href="/about" style={{ marginTop: 24, display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 500, color: 'var(--accent)', textDecoration: 'none' }}>
                Подробнее о проекте →
              </Link>
            </div>
          </div>
        </section>

        {/* ── CROSS LINK ── */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)', background: 'color-mix(in oklab, var(--muted) 40%, var(--background))' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '64px 40px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 24, borderRadius: 2, border: '1px solid var(--border)', background: 'var(--card)', padding: 32 }}>
              <div>
                <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--accent)' }}>Партнёрский проект</div>
                <h3 style={{ margin: '8px 0 0', fontFamily: "'Golos Text',sans-serif", fontSize: 24, fontWeight: 600, color: 'var(--foreground)' }}>
                  taoteam.ru — функциональная диагностика команд
                </h3>
                <p style={{ margin: '12px 0 0', maxWidth: 680, fontSize: 14, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>
                  Если 64 ДАО показывает фазу компании, то taoteam.ru разбирает команду: роли, дефициты и зоны напряжения. Два инструмента работают вместе — стратегия и команда в одной рамке.
                </p>
              </div>
              <a href="https://taoteam.ru" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 2, border: '1px solid rgba(0,0,0,0.2)', padding: '12px 24px', fontSize: 14, fontWeight: 500, color: 'var(--foreground)', textDecoration: 'none', whiteSpace: 'nowrap' }}>
                Перейти на taoteam.ru →
              </a>
            </div>
          </div>
        </section>

        {/* ── CONTACT ── */}
        <ContactSection />

        {/* ── FINAL CTA ── */}
        <section id="cta" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '112px 40px', textAlign: 'center' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
              <span style={{ height: 1, width: 32, background: 'var(--accent)' }} />Точка сверки<span style={{ height: 1, width: 32, background: 'var(--accent)' }} />
            </div>
            <h2 style={{ margin: '24px auto 0', maxWidth: 760, fontFamily: "'Golos Text',sans-serif", fontSize: 'clamp(36px,5.2vw,64px)', lineHeight: 1.05, color: 'var(--foreground)' }}>
              Узнайте свою фазу до следующего крупного решения
            </h2>
            <p style={{ margin: '24px auto 0', maxWidth: 560, fontSize: 16, color: 'var(--muted-foreground)' }}>
              Несколько минут сейчас — вместо месяцев разбора последствий потом.
            </p>
            <div style={{ marginTop: 40, display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
              <a href="/login" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 2, background: 'var(--foreground)', padding: '16px 32px', fontSize: 14, fontWeight: 500, color: 'var(--background)', textDecoration: 'none' }}>
                Пройти диагностику
              </a>
              <a href="#contact" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 2, border: '1px solid rgba(0,0,0,0.2)', padding: '16px 32px', fontSize: 14, fontWeight: 500, color: 'var(--foreground)', textDecoration: 'none' }}>
                Обсудить с нами
              </a>
            </div>
            <p style={{ marginTop: 32, fontSize: 14, color: 'var(--muted-foreground)' }}>
              {priceFormatted} {pricing.currency} · Метод 1 + Метод 2 · обязательство по ясности
            </p>
          </div>
        </section>
      </main>

      <SiteFooter year={year} />
      <CookieBanner />
    </div>
  )
}

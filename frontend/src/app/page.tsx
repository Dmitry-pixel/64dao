'use client';

import { useEffect, useState, FormEvent } from 'react';
import Link from 'next/link';
import { Logo } from '@/components/Logo';
import './landing.css';
import { HexMatrix, YinYang, CycleCurve, Gauge, Dots } from './LandingVisuals';

const FAQ_DATA = [
  {
    q: 'Это что, гадание?',
    a: 'Нет. 64 ДАО не предсказывает будущее и не обещает «правильный ответ». Это диагностика текущей фазы цикла, сформулированная на управленческом языке. Вы выносите на стол диагностику фазы компании, а не гороскоп.',
  },
  {
    q: 'Я и так знаю свой бизнес. Что мне это даст?',
    a: 'Знаете — лучше любого консультанта. 64 ДАО даёт второй взгляд: не «что у вас происходит», а «в какой фазе цикла вы находитесь и что это меняет в решениях». Ту оптику, которую трудно поймать изнутри.',
  },
  {
    q: 'Автоматика поймёт специфику моего бизнеса?',
    a: 'Ей это и не нужно. 64 ДАО не лезет в вашу продуктовую кухню и не требует NDA. Он даёт большую картину направления — опираться на эмоции или технологичность, выходить на рынок сейчас или рано. Детали остаются за вами.',
  },
  {
    q: 'Что именно я получу за 14 900 ₽?',
    a: 'Диагностику по 6 вопросам, определение фазы из 64, стратегический отчёт по 12 направлениям и Метод 2 — разбор бизнес-модели по 9 блокам. На выходе документ, с которого можно начинать стратегическую сессию.',
  },
  {
    q: 'Сейчас операционка, не до стратегии.',
    a: 'Именно поэтому. Пожары часто начинаются с одного неверного «логичного» решения. Диагностика занимает минуты, а сверка фазы помогает не залить бюджет туда, откуда потом придётся выгребать месяцами.',
  },
  {
    q: 'Что такое «И Цзин»?',
    a: '«И Цзин», часто переводится как «Книга перемен», является одним из основополагающих текстов китайской культуры. Первоначально это было руководство по гаданию, но с течением веков оно превратилось в крупный философский труд, оказавший влияние на такие философские школы, как конфуцианство и даосизм. И-Цзин состоит из 64 гексаграмм, каждая из которых состоит из шести линий, которые могут быть сплошными (Ян) или прерывистыми (Инь). Эти гексаграммы традиционно получаются с помощью методов гадания и интерпретируются для получения информации и руководства в конкретных ситуациях. Помимо использования в целях предсказания, «И Цзин» рассматривается как символическая карта процессов изменений и вселенской динамики.',
  },
  {
    q: 'Нужны ли мне предварительные знания «И Цзин»?',
    a: 'Нет. Система 64dao.ru разработана таким образом, чтобы она была доступна предпринимателям, даже не имеющим предварительных знаний о традиционной книге «И Цзин». Чёткая структура поможет вам шаг за шагом, что позволит быстро получить доступ к необходимой информации.',
  },
  {
    q: 'Что из себя представляет современная адаптация 64dao для предпринимателей?',
    a: 'В основе его лежат три фундаментальных принципа. Система 64dao.ru раскрывает более глубокую динамику, влияющую на ситуацию, обеспечивая более широкое видение перед принятием решения. 1. Следуйте за потоком перемен — каждая ситуация развивается в соответствии с циклами преобразований. 2. 64dao.ru помогает вам понять, когда следует начать действовать, когда подождать, а когда скорректировать свой подход. 3. Мудро предвидеть и адаптироваться — вместо того, чтобы реагировать на внешние события, это позволяет вам чувствовать подходящий момент для действий.',
  },
  {
    q: 'Является ли сервис 64dao.ru заменой консультанту?',
    a: 'Это автономная альтернатива или мощное дополнение. 64dao.ru предлагает мгновенный доступ к внешней, структурированной информации — без ограничений по расписанию или почасовой оплаты — обеспечивая при этом высокий уровень ясности ваших решений.',
  },
  {
    q: 'Как мне получить доступ к сервису 64dao.ru?',
    a: 'Доступ к сервису 64dao.ru доступен через безопасную, интуитивно понятную онлайн-платформу, доступную 24 часа в сутки 7 дней в неделю с вашего компьютера, планшета или смартфона.',
  },
];

const REPORT_BLOCKS: { n: string; t: string; v: number; tone: 'ok' | 'warn' | 'alert' }[] = [
  { n: '01', t: 'Ключевые партнёры', v: 4, tone: 'ok' },
  { n: '02', t: 'Ключевые активности', v: 3, tone: 'ok' },
  { n: '03', t: 'Ключевые ресурсы', v: 4, tone: 'ok' },
  { n: '04', t: 'Ценностное предложение', v: 5, tone: 'ok' },
  { n: '05', t: 'Отношения с клиентами', v: 3, tone: 'warn' },
  { n: '06', t: 'Каналы', v: 2, tone: 'alert' },
  { n: '07', t: 'Сегменты клиентов', v: 4, tone: 'ok' },
  { n: '08', t: 'Структура издержек', v: 3, tone: 'warn' },
  { n: '09', t: 'Потоки доходов', v: 4, tone: 'ok' },
];

const API = process.env.NEXT_PUBLIC_API_URL || '';

const DEFAULT_PRICING = {
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
};

interface PricingData {
  title: string;
  price: number;
  currency: string;
  description: string;
  features: { label: string; value: string }[];
}

function navClick(e: React.MouseEvent<HTMLAnchorElement>) {
  const href = e.currentTarget.getAttribute('href') || '';
  const id = href.includes('#') ? href.slice(href.indexOf('#') + 1) : '';
  if (!id) return;
  const el = document.getElementById(id);
  if (!el) return;
  e.preventDefault();
  const headerH = 72;
  const top = window.scrollY + el.getBoundingClientRect().top - headerH;
  window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
}

function scrollTop(e: React.MouseEvent<HTMLAnchorElement>) {
  e.preventDefault();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

export default function LandingPage() {
  const [faqOpen, setFaqOpen] = useState<number | null>(null);
  const [contactSent, setContactSent] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', message: '' });
  const [cookieAccepted, setCookieAccepted] = useState(true);
  const [pricing, setPricing] = useState<PricingData>(DEFAULT_PRICING);

  useEffect(() => {
    fetch(`${API}/api/pricing`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setPricing(data);
      })
      .catch(() => {
        /* остаёмся на DEFAULT_PRICING */
      });
  }, []);

  useEffect(() => {
    try {
      setCookieAccepted(localStorage.getItem('cookie-consent') === '1');
    } catch {
      /* ignore */
    }
  }, []);

  function submitForm(e: FormEvent) {
    e.preventDefault();
    // TODO: подключить реальную отправку (например POST /api/contact)
    setContactSent(true);
  }

  function acceptCookie() {
    try {
      localStorage.setItem('cookie-consent', '1');
    } catch {
      /* ignore */
    }
    setCookieAccepted(true);
  }

  const year = new Date().getFullYear();

  return (
    <div className="landing-root" style={{ minHeight: '100vh' }}>
      {/* HEADER */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          background: 'var(--brand-teal)',
          borderBottom: '1px solid rgba(255,255,255,0.25)',
          backdropFilter: 'blur(8px)',
        }}
      >
        <div
          style={{
            maxWidth: 1280,
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 24,
            padding: '12px 40px',
          }}
        >
          <a href="#top" onClick={scrollTop} style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
            <Logo />
          </a>
          <nav
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 28,
              fontSize: 12,
              textTransform: 'uppercase',
              letterSpacing: '0.18em',
            }}
          >
            <a href="#how" onClick={navClick} className="landing-nav-link">Как это работает</a>
            <a href="#report" onClick={navClick} className="landing-nav-link">Что в отчёте</a>
            <a href="#price" onClick={navClick} className="landing-nav-link">Стоимость</a>
            <Link href="/about" className="landing-nav-link">О нас</Link>
            <a href="#contact" onClick={navClick} className="landing-nav-link">Контакты</a>
            <Link href="/login" className="landing-nav-link">Вход / Регистрация</Link>
          </nav>
          <Link
            href="/login"
            className="landing-btn-accent"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 2,
              background: 'var(--accent)',
              padding: '12px 20px',
              fontSize: 14,
              fontWeight: 500,
              color: 'var(--accent-foreground)',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            Пройти диагностику
          </Link>
        </div>
      </header>

      <main style={{ minHeight: '100vh' }}>
        {/* HERO */}
        <section id="top" style={{ position: 'relative', overflow: 'hidden', borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <YinYang />
          <div
            style={{
              position: 'relative',
              zIndex: 10,
              maxWidth: 1280,
              margin: '0 auto',
              display: 'grid',
              gridTemplateColumns: '1.35fr 1fr',
              alignItems: 'center',
              gap: 48,
              padding: '112px 40px',
            }}
          >
            <div style={{ minWidth: 0 }}>
              <h1
                style={{
                  margin: 0,
                  fontWeight: 700,
                  fontSize: 'clamp(34px,4.6vw,60px)',
                  lineHeight: 1.12,
                  letterSpacing: '-0.01em',
                  color: 'var(--foreground)',
                }}
              >
                «И-цзин» для разработки и управления стратегией изменений компании
              </h1>
              <div style={{ marginTop: 32, height: 3, width: 80, background: 'var(--accent)' }} />
              <p
                style={{
                  marginTop: 32,
                  maxWidth: 640,
                  fontSize: 18,
                  lineHeight: 1.6,
                  color: 'color-mix(in oklab, var(--foreground) 80%, transparent)',
                }}
              >
                64 ДАО — инструмент стратегического диагностирования, основанный на метафизике «И-цзин». Определяет, в
                какой фазе находится компания, какие управленческие решения уместны сейчас, и служит опорой при
                проведении стратегических сессий.
              </p>
              <div style={{ marginTop: 40, display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                <Link
                  href="/login"
                  className="landing-btn-accent"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    borderRadius: 2,
                    background: 'var(--accent)',
                    padding: '14px 24px',
                    fontSize: 14,
                    fontWeight: 500,
                    color: 'var(--accent-foreground)',
                    textDecoration: 'none',
                  }}
                >
                  Пройти диагностику <span aria-hidden="true">→</span>
                </Link>
                <a
                  href="#report"
                  onClick={navClick}
                  className="landing-btn-accent"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: 2,
                    background: 'var(--foreground)',
                    padding: '14px 24px',
                    fontSize: 14,
                    fontWeight: 500,
                    color: 'var(--background)',
                    textDecoration: 'none',
                  }}
                >
                  Посмотреть пример отчёта
                </a>
              </div>
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ position: 'relative' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: 10,
                    fontWeight: 500,
                    textTransform: 'uppercase',
                    letterSpacing: '0.24em',
                    color: 'var(--muted-foreground)',
                  }}
                >
                  <span>идёт выборка</span>
                  <span>64 фазы</span>
                </div>
                <HexMatrix />
                <div style={{ marginTop: 20, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--accent)' }}>
                      Фаза роста
                    </div>
                    <div style={{ marginTop: 4, fontSize: 14, color: 'var(--foreground)' }}>11 / 64 · ваша фаза</div>
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>пример результата</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* PROBLEM */}
        <section
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'color-mix(in oklab, var(--muted) 40%, var(--background))',
          }}
        >
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
              <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
              <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>
                Знакомо?
              </span>
            </div>
            <h2
              style={{
                margin: 0,
                maxWidth: 820,
                fontSize: 'clamp(28px,4.5vw,44px)',
                lineHeight: 1.15,
                color: 'var(--foreground)',
              }}
            >
              Дело не в слабой команде. Дело в том, что все приходят без общей картины.
            </h2>
            <p style={{ marginTop: 24, maxWidth: 720, fontSize: 17, lineHeight: 1.7, color: '#4A4A4A' }}>
              Стратегия живёт в голове собственника. Решения принимаются в режиме тушения пожаров — и каждое
              «логичное» из них тихо сливает бюджет.
            </p>
            <div style={{ width: 60, height: 2, background: 'var(--accent)', marginTop: 40 }} />
            <div style={{ fontSize: 14, fontStyle: 'italic', color: '#888888', marginTop: 40, marginBottom: 20 }}>
              4 типичных симптома
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24 }}>
              {[
                { t: 'Сессии без выводов', d: 'Собрались, поспорили о прошлом квартале, разошлись. Решения — на следующий раз.' },
                { t: 'Слитые бюджеты', d: 'Запустили рекламу, вышли на рынок, масштабировались — а момент был не тот.' },
                { t: 'Команда тянет в разные стороны', d: 'У каждого своя картина, потому что общей точки сверки нет.' },
                { t: 'Стратегия — в одной голове', d: 'Вы ведёте компанию как будто без навигатора: а туда ли вообще едем?' },
              ].map((item) => (
                <div
                  key={item.t}
                  style={{
                    borderRadius: 2,
                    background: 'color-mix(in oklab, var(--muted) 70%, #000 6%)',
                    borderLeft: '3px solid var(--accent)',
                    padding: '32px 32px 32px 28px',
                  }}
                >
                  <h3 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: 'var(--foreground)' }}>{item.t}</h3>
                  <p style={{ margin: '14px 0 0', fontSize: 15, color: '#5A5A5A', lineHeight: 1.65 }}>{item.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
        {/* SOLUTION */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 880, margin: '0 auto', padding: '100px 40px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
              <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>
                Что это
              </span>
            </div>
            <h2
              style={{
                margin: '24px 0 0',
                fontSize: 'clamp(28px,4vw,40px)',
                fontWeight: 700,
                lineHeight: 1.2,
                color: 'var(--foreground)',
              }}
            >
              Это не гадание. Это диагностика фазы.
            </h2>
            <p style={{ marginTop: 32, fontSize: 18, lineHeight: 1.8, color: '#3A3A3A' }}>
              64 ДАО не предсказывает будущее и не обещает «правильный ответ». Он определяет, в какой фазе цикла
              находится компания сейчас, что для этой фазы уместно, а что преждевременно — и формулирует это на
              управленческом языке.
            </p>
            <p style={{ marginTop: 16, fontSize: 18, lineHeight: 1.8, color: '#3A3A3A' }}>Без иероглифов и мистики.</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 40, marginTop: 40 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
                <svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <circle cx={12} cy={12} r={10} />
                  <polygon points="16.2 7.8 13.4 13.4 7.8 16.2 10.6 10.6 16.2 7.8" fill="var(--accent)" stroke="none" />
                </svg>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#3A3A3A', lineHeight: 1.35 }}>Определяем фазу</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
                <svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <circle cx={12} cy={12} r={10} />
                  <circle cx={12} cy={12} r={6} />
                  <circle cx={12} cy={12} r={2} fill="var(--accent)" stroke="none" />
                </svg>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#3A3A3A', lineHeight: 1.35 }}>Что уместно сейчас</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
                <svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 0 1-.9-3.8A8.38 8.38 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z" />
                </svg>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#3A3A3A', lineHeight: 1.35 }}>Управленческий язык</div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW */}
        <section
          id="how"
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'color-mix(in oklab, var(--muted) 40%, var(--background))',
          }}
        >
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
              Как это работает
            </div>
            <h2 style={{ margin: 0, maxWidth: 760, fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>
              Три шага до точки сверки
            </h2>
            <div style={{ marginTop: 56, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px,1fr))', gap: 32 }}>
              {[
                { n: '01', t: '6 простых вопросов', d: 'Выбираете из двух вариантов: растущий рынок или устоявшийся, рост или сокращение затрат. Никаких «опишите стратегию на 5 лет».' },
                { n: '02', t: 'Определяется фаза', d: 'Ответы складываются в одну из 64 фаз — как доктор ставит диагноз: где вы на кривой прямо сейчас.' },
                { n: '03', t: 'Стратегический отчёт', d: 'Разбор по 12 направлениям плюс карта бизнес-модели. Готовый предмет для стратегической сессии, а не пустой лист.' },
              ].map((s) => (
                <div key={s.n} style={{ borderTop: '1px solid var(--foreground)', paddingTop: 24 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--accent)' }}>{s.n}</div>
                  <h3 style={{ margin: '16px 0 0', fontSize: 20, fontWeight: 600, color: 'var(--foreground)' }}>{s.t}</h3>
                  <p style={{ margin: '12px 0 0', fontSize: 14, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>{s.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* REPORT */}
        <section id="report" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 12,
                marginBottom: 20,
                fontSize: 12,
                textTransform: 'uppercase',
                letterSpacing: '0.22em',
                color: 'var(--muted-foreground)',
              }}
            >
              <span style={{ height: 1, width: 32, background: 'rgba(0,0,0,0.3)' }} />
              Что внутри отчёта
            </div>
            <h2
              style={{
                margin: 0,
                maxWidth: 760,
                fontFamily: 'Inter, sans-serif',
                fontSize: 'clamp(32px,4.6vw,48px)',
                fontWeight: 700,
                lineHeight: 1.1,
                letterSpacing: '-0.01em',
                color: 'var(--foreground)',
              }}
            >
              Не таблица слов.
              <br />
              Карта вашего положения в цикле.
            </h2>
            <p style={{ marginTop: 20, fontSize: 16, color: 'var(--muted-foreground)' }}>
              Пример обезличенного заключения доступен до оплаты.
            </p>

            <div
              style={{
                marginTop: 48,
                borderRadius: 2,
                border: '1px solid var(--border)',
                background: 'var(--card)',
                boxShadow: '0 30px 80px -50px rgba(20,30,60,0.35)',
                overflow: 'hidden',
              }}
            >
              <div style={{ borderBottom: '1px solid var(--border)', padding: '24px 32px' }}>
                <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--accent)' }}>
                  Отчёт · фаза определена
                </div>
                <div style={{ marginTop: 8, display: 'flex', alignItems: 'baseline', gap: 12 }}>
                  <h3 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: 'var(--foreground)' }}>Фаза роста</h3>
                  <span style={{ fontSize: 14, color: 'var(--muted-foreground)' }}>· 11 / 64</span>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 1, background: 'var(--border)' }}>
                <div style={{ background: 'var(--card)', padding: 32 }}>
                  <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--muted-foreground)' }}>
                    Где вы на кривой цикла
                  </div>
                  <div style={{ marginTop: 32 }}>
                    <CycleCurve />
                  </div>
                </div>
                <div style={{ background: 'var(--card)', padding: 32 }}>
                  <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--muted-foreground)' }}>
                    Инвестировать или подождать
                  </div>
                  <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <Gauge />
                    <div style={{ marginTop: 8, fontSize: 20, fontWeight: 600, color: 'oklch(0.45 0.13 160)' }}>Инвестировать</div>
                    <p style={{ marginTop: 12, textAlign: 'center', fontSize: 14, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>
                      в масштаб — момент попутный.
                      <br />
                      Преждевременно: резать затраты.
                    </p>
                  </div>
                </div>
              </div>
              <div
                style={{
                  borderTop: '1px solid var(--border)',
                  background: 'color-mix(in oklab, var(--background) 40%, var(--card))',
                  padding: 32,
                }}
              >
                <div
                  style={{
                    marginBottom: 24,
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'baseline',
                    justifyContent: 'space-between',
                    gap: 12,
                  }}
                >
                  <h4 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--foreground)' }}>
                    Метод 2 — бизнес-модель по 9 блокам
                  </h4>
                  <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--accent)' }}>
                    бонус · в подарок · оценка 1–5
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px,1fr))', gap: 12 }}>
                  {REPORT_BLOCKS.map((b) => (
                    <div
                      key={b.n}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        borderRadius: 2,
                        border: '1px solid var(--border)',
                        background: 'var(--card)',
                        padding: '16px 20px',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--muted-foreground)' }}>
                          {b.n}
                        </div>
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
        {/* EXAMPLE */}
        <section
          id="example"
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'var(--brand-navy)',
            color: 'var(--background)',
          }}
        >
          <div
            style={{
              maxWidth: 1280,
              margin: '0 auto',
              display: 'grid',
              gridTemplateColumns: '0.85fr 1.15fr',
              gap: 48,
              padding: '96px 40px',
            }}
          >
            <div>
              <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.6)' }}>
                Пример отчёта
              </div>
              <h2 style={{ margin: 0, fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: '#ffffff' }}>
                Посмотрите образец заключения до оплаты
              </h2>
              <p style={{ marginTop: 24, maxWidth: 420, fontSize: 16, lineHeight: 1.6, color: 'rgba(255,255,255,0.7)' }}>
                Обезличенный отчёт реальной компании — пролистайте структуру, тон и глубину разбора, чтобы решать
                осознанно, а не вслепую.
              </p>
              <a
                href="#contact"
                onClick={navClick}
                className="landing-btn-accent"
                style={{
                  marginTop: 40,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 2,
                  background: 'var(--background)',
                  padding: '14px 24px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--foreground)',
                  textDecoration: 'none',
                }}
              >
                Скачать пример отчёта
              </a>
            </div>
            <div>
              <div
                style={{
                  borderRadius: 2,
                  border: '1px solid rgba(255,255,255,0.15)',
                  background: 'rgba(255,255,255,0.04)',
                  padding: 32,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: 10,
                    textTransform: 'uppercase',
                    letterSpacing: '0.22em',
                    color: 'rgba(255,255,255,0.5)',
                  }}
                >
                  <span>Стратегический отчёт</span>
                  <span>Стр. 04 / 28</span>
                </div>
                <h3 style={{ margin: '24px 0 0', fontSize: 24, lineHeight: 1.2, color: '#ffffff' }}>
                  Фаза 17. Удержание ядра в зреющем рынке
                </h3>
                <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12, fontSize: 14, lineHeight: 1.6, color: 'rgba(255,255,255,0.75)' }}>
                  <p style={{ margin: 0 }}>
                    <span style={{ color: 'var(--accent)' }}>Уместно сейчас.</span> Сфокусироваться на ядре клиентов и
                    удержании маржи. Точечно усиливать сильные продукты.
                  </p>
                  <p style={{ margin: 0 }}>
                    <span style={{ color: 'var(--accent)' }}>Преждевременно.</span> Выход на смежные рынки и
                    масштабная рекламная экспансия. Высокая вероятность вернуться с ослабленным ядром.
                  </p>
                  <p style={{ margin: 0 }}>
                    <span style={{ color: 'var(--accent)' }}>Точка сверки для команды.</span> Договориться, что
                    обсуждаем удержание, а не рост — и пересобрать KPI отдела продаж под эту рамку.
                  </p>
                </div>
                <div
                  style={{
                    marginTop: 32,
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4,1fr)',
                    gap: 8,
                    borderTop: '1px solid rgba(255,255,255,0.15)',
                    paddingTop: 24,
                    fontSize: 11,
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    color: 'rgba(255,255,255,0.5)',
                  }}
                >
                  <span>Диагноз</span>
                  <span>Навигация</span>
                  <span>Решение</span>
                  <span>Метод 2</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FOR WHOM */}
        <section style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
              Квалификация
            </div>
            <h2 style={{ margin: 0, fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>
              Для кого это
            </h2>
            <div style={{ marginTop: 48, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px,1fr))', gap: 32 }}>
              <div style={{ borderRadius: 2, border: '1px solid var(--border)', background: 'var(--card)', padding: 32 }}>
                <div style={{ fontSize: 14, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)' }}>
                  Это для вас, если
                </div>
                <ul style={{ margin: '24px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {[
                    'Вы собственник или CEO с реальным стратегическим запросом: рост, новый рынок, масштабирование, инвестиции, смена курса',
                    'Впереди стратегическая сессия или крупное решение, а общей картины «где мы сейчас» нет',
                    'Команда спорит о направлении, и каждый тянет в свою сторону',
                    'Вы цените внешнюю оптику, а не только собственную интуицию',
                  ].map((li) => (
                    <li key={li} style={{ display: 'flex', gap: 12, fontSize: 14, lineHeight: 1.6, color: 'var(--foreground)' }}>
                      <span style={{ marginTop: 8, height: 6, width: 6, flex: 'none', borderRadius: '9999px', background: 'var(--accent)' }} />
                      {li}
                    </li>
                  ))}
                </ul>
              </div>
              <div style={{ borderRadius: 2, border: '1px solid var(--border)', background: 'var(--card)', padding: 32 }}>
                <div style={{ fontSize: 14, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)' }}>
                  Что вы получите
                </div>
                <ul style={{ margin: '24px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {[
                    'Получите ясную карту текущей фазы цикла вашей компании',
                    'Увидите следующий разумный шаг — без догадок и обещаний «единственно верного» решения',
                    'Получите внешнюю оптику, которая помогает скорректировать курс вовремя',
                  ].map((li) => (
                    <li key={li} style={{ display: 'flex', gap: 12, fontSize: 14, lineHeight: 1.6, color: 'var(--foreground)' }}>
                      <span style={{ marginTop: 8, height: 6, width: 6, flex: 'none', borderRadius: '9999px', background: 'var(--accent)' }} />
                      {li}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'color-mix(in oklab, var(--muted) 40%, var(--background))',
          }}
        >
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
            <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
              Честные ответы
            </div>
            <h2 style={{ margin: 0, fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>
              Что обычно спрашивают
            </h2>
            <div style={{ marginTop: 48, borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
              {FAQ_DATA.map((f, i) => {
                const open = faqOpen === i;
                return (
                  <button
                    key={f.q}
                    type="button"
                    onClick={() => setFaqOpen(open ? null : i)}
                    className="landing-faq-btn"
                    style={{
                      display: 'block',
                      width: '100%',
                      cursor: 'pointer',
                      padding: '24px 0',
                      textAlign: 'left',
                      background: 'transparent',
                      border: 'none',
                      borderTop: '1px solid var(--border)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24 }}>
                      <span style={{ fontSize: 18, fontWeight: 500, color: 'var(--foreground)' }}>{f.q}</span>
                      <span style={{ marginTop: 4, fontSize: 24, lineHeight: 1, color: 'var(--accent)' }}>{open ? '–' : '+'}</span>
                    </div>
                    {open && (
                      <p style={{ margin: '16px 0 0', maxWidth: 780, fontSize: 14, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>
                        {f.a}
                      </p>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </section>
        {/* PRICE */}
        <section id="price" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div
            style={{
              maxWidth: 1280,
              margin: '0 auto',
              display: 'grid',
              gridTemplateColumns: '0.85fr 1.15fr',
              gap: 80,
              padding: '96px 40px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
                <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>
                  Стоимость
                </span>
              </div>
              <h2 style={{ margin: '24px 0 0', fontSize: 'clamp(28px,4vw,38px)', fontWeight: 700, lineHeight: 1.2, color: 'var(--foreground)' }}>
                Дешевле одного неудачного решения
              </h2>
              <div style={{ width: 80, height: 3, background: 'var(--accent)', margin: '28px 0' }} />
              <p style={{ margin: 0, maxWidth: 420, fontSize: 16, lineHeight: 1.75, color: '#4A4A4A' }}>
                Стратегическая консультация в России — от 300 000 ₽. Один день сессии «ни о чём» или один слитый
                рекламный бюджет стоят кратно дороже.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 32 }}>
                <span style={{ fontSize: 22, color: '#999999', textDecoration: 'line-through' }}>300 000 ₽</span>
                <span style={{ fontSize: 20, color: '#888888' }}>→</span>
                <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent)' }}>
                  {pricing.price.toLocaleString('ru-RU')} {pricing.currency}
                </span>
              </div>
            </div>
            <div>
              <div
                style={{
                  background: 'color-mix(in oklab, var(--muted) 70%, #000 6%)',
                  borderRadius: 8,
                  padding: '48px 40px',
                  boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#9a9a9a' }}>
                  Оплата диагностики
                </div>
                <h3
                  style={{
                    margin: '14px 0 0',
                    fontSize: 'clamp(28px,3.6vw,34px)',
                    fontWeight: 700,
                    lineHeight: 1.1,
                    color: 'var(--foreground)',
                  }}
                >
                  {pricing.title}
                </h3>
                <div style={{ marginTop: 28, display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 8 }}>
                  <span
                    style={{
                      fontSize: 'clamp(56px,9vw,80px)',
                      fontWeight: 800,
                      lineHeight: 1,
                      color: 'var(--foreground)',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {pricing.price.toLocaleString('ru-RU')}
                  </span>
                  <span style={{ fontSize: 32, fontWeight: 500, color: '#9a9a9a' }}>{pricing.currency}</span>
                </div>
                <div style={{ marginTop: 16, fontSize: 14, color: '#888888' }}>{pricing.description}</div>

                <div style={{ borderTop: '1px solid rgba(0,0,0,0.1)', margin: '32px 0 4px' }} />
                <div style={{ textAlign: 'left' }}>
                  {pricing.features.map((f) => (
                    <div
                      key={f.label}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 16,
                        padding: '18px 0',
                        borderBottom: '1px solid rgba(0,0,0,0.08)',
                      }}
                    >
                      <span style={{ fontSize: 15, color: '#6A6A6A' }}>{f.label}</span>
                      <span style={{ fontSize: 15, fontWeight: 500, color: 'var(--foreground)' }}>{f.value}</span>
                    </div>
                  ))}
                </div>

                <Link
                  href="/login"
                  className="landing-btn-soft-blue"
                  style={{
                    marginTop: 32,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 10,
                    width: '100%',
                    borderRadius: 6,
                    padding: '18px 24px',
                    fontSize: 16,
                    fontWeight: 500,
                    color: '#ffffff',
                    textDecoration: 'none',
                  }}
                >
                  Перейти к оплате <span aria-hidden="true">→</span>
                </Link>
              </div>
              <div
                style={{
                  marginTop: 24,
                  background: 'color-mix(in oklab, var(--muted) 70%, #000 6%)',
                  borderRadius: 8,
                  padding: '28px 32px',
                  boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="#888888" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>
                    Обязательство по ясности
                  </div>
                </div>
                <p style={{ margin: '14px 0 0', fontSize: 14, lineHeight: 1.75, color: '#555555' }}>
                  Мы не обещаем рост выручки и не принимаем за вас стратегические решения — это зона вашей
                  ответственности. Но мы отвечаем за то, что отчёт будет понятным и пригодным как рамка для разговора
                  о стратегии. Если он окажется неясным — напишите в течение 7 дней, и мы бесплатно дадим короткий
                  разбор-комментарий по вашему отчёту.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* WHY FIRST */}
        <section
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'color-mix(in oklab, var(--muted) 40%, var(--background))',
          }}
        >
          <div style={{ maxWidth: 1100, margin: '0 auto', padding: '100px 40px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
              <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 2, color: '#888888' }}>
                Почему диагностика идёт первой
              </span>
            </div>
            <div style={{ marginTop: 32, maxWidth: 880 }}>
              <div style={{ fontFamily: 'Georgia, serif', fontSize: 72, lineHeight: 0.6, color: 'var(--accent)', opacity: 0.3, marginBottom: 8 }}>
                &ldquo;
              </div>
              <p style={{ margin: 0, fontSize: 'clamp(20px,2.6vw,28px)', fontWeight: 500, lineHeight: 1.5, color: '#1A1A1A' }}>
                Стратегия, выстроенная без понимания текущей фазы, — это аккуратно оформленные предположения. Сверку
                имеет смысл проходить до решения, а не объяснять задним числом, почему прошлый шаг не сработал.
              </p>
              <div style={{ marginTop: 40 }}>
                <div style={{ width: 40, height: 2, background: '#CCCCCC' }} />
                <div style={{ fontSize: 14, fontStyle: 'italic', color: '#888888', marginTop: 12 }}>Принцип 64 ДАО</div>
              </div>
            </div>
          </div>
        </section>

        {/* CONSULTANTS */}
        <section id="consultants" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div
            style={{
              maxWidth: 1280,
              margin: '0 auto',
              display: 'grid',
              gridTemplateColumns: '0.85fr 1.15fr',
              gap: 48,
              padding: '96px 40px',
            }}
          >
            <div>
              <div style={{ marginBottom: 16, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
                Для консультантов и фасилитаторов
              </div>
              <h2 style={{ margin: 0, fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>
                Начинайте сессию не с хаоса мнений, а с готовой диагностики
              </h2>
              <p style={{ marginTop: 24, maxWidth: 420, fontSize: 16, color: 'var(--muted-foreground)' }}>
                Входной инструмент, который отличает вас от тех, кто работает только со SWOT и Canvas. Клиент говорит
                «давайте разберём подробнее» — и это вход к сессии и сопровождению.
              </p>
            </div>
            <div>
              <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 20 }}>
                {[
                  'Вы подаёте не гадание, а входную диагностику фазы компании — деловой инструмент.',
                  'Отчёт — не конец, а дверь: к сессии, сопровождению, регулярной работе с собственником.',
                  'Отличие от SWOT и Canvas — вы приходите с тем, чего у клиента раньше не было.',
                  'В комплекте — скрипт подачи клиенту: как представить отчёт деловым языком и в какой момент сессии его подать.',
                ].map((li) => (
                  <li
                    key={li}
                    style={{
                      display: 'flex',
                      gap: 16,
                      borderTop: '1px solid var(--border)',
                      paddingTop: 20,
                      fontSize: 16,
                      lineHeight: 1.6,
                      color: 'var(--foreground)',
                    }}
                  >
                    <span style={{ marginTop: 8, height: 1, width: 32, flex: 'none', background: 'var(--accent)' }} />
                    {li}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
        {/* ABOUT (краткий блок на главной, полная страница — /about) */}
        <section id="about" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div
            style={{
              maxWidth: 1280,
              margin: '0 auto',
              display: 'grid',
              gridTemplateColumns: '0.5fr 1fr',
              gap: 48,
              padding: '96px 40px',
            }}
          >
            <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--muted-foreground)' }}>
              О нас
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 'clamp(32px,4.6vw,48px)', lineHeight: 1.1, color: 'var(--foreground)' }}>
                Команда 64 ДАО
              </h2>
              <p style={{ marginTop: 24, maxWidth: 680, fontSize: 16, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>
                Мы соединяем метафизику «И-цзин» с практикой стратегического управления. 64 ДАО — это инструмент,
                который помогает собственникам и консультантам опираться на структуру цикла, а не на догадки.
              </p>
              <Link
                href="/about"
                className="landing-nav-link"
                style={{
                  marginTop: 24,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--accent)',
                  textDecoration: 'none',
                }}
              >
                Подробнее о проекте <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </section>

        {/* CROSS LINK */}
        <section
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'color-mix(in oklab, var(--muted) 40%, var(--background))',
          }}
        >
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '64px 40px' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                alignItems: 'center',
                gap: 24,
                borderRadius: 2,
                border: '1px solid var(--border)',
                background: 'var(--card)',
                padding: 32,
              }}
            >
              <div>
                <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--accent)' }}>
                  Партнёрский проект
                </div>
                <h3 style={{ margin: '8px 0 0', fontSize: 24, fontWeight: 600, color: 'var(--foreground)' }}>
                  taoteam.ru — функциональная диагностика команд
                </h3>
                <p style={{ margin: '12px 0 0', maxWidth: 680, fontSize: 14, lineHeight: 1.6, color: 'var(--muted-foreground)' }}>
                  Если 64 ДАО показывает фазу компании, то taoteam.ru разбирает команду: роли, дефициты и зоны
                  напряжения. Два инструмента работают вместе — стратегия и команда в одной рамке.
                </p>
              </div>
              <a
                href="https://taoteam.ru"
                target="_blank"
                rel="noreferrer"
                className="landing-btn-outline"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 2,
                  border: '1px solid rgba(0,0,0,0.2)',
                  padding: '12px 24px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--foreground)',
                  textDecoration: 'none',
                  whiteSpace: 'nowrap',
                }}
              >
                Перейти на taoteam.ru →
              </a>
            </div>
          </div>
        </section>

        {/* CONTACT */}
        <section
          id="contact"
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.06)',
            background: 'color-mix(in oklab, var(--brand-teal) 12%, var(--background))',
          }}
        >
          <div
            style={{
              maxWidth: 1280,
              margin: '0 auto',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 64,
              padding: '96px 40px',
            }}
          >
            <div>
              <div style={{ marginBottom: 24, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'var(--accent)' }}>
                Контакты
              </div>
              <h2 style={{ margin: 0, fontSize: 'clamp(36px,5vw,60px)', lineHeight: 1.05, color: 'var(--foreground)' }}>
                Свяжитесь
                <br />с нами
              </h2>
              <p style={{ marginTop: 32, maxWidth: 420, fontSize: 16, color: 'var(--muted-foreground)' }}>
                Оставьте сообщение, если хотите обсудить внедрение 64 ДАО, стратегическую сессию или доступ для
                команды.
              </p>
              <dl style={{ marginTop: 48, borderTop: '1px solid rgba(0,0,0,0.1)', paddingTop: 32, display: 'flex', flexDirection: 'column', gap: 24 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', alignItems: 'baseline', columnGap: 24, borderBottom: '1px solid rgba(0,0,0,0.1)', paddingBottom: 24 }}>
                  <dt style={{ fontSize: 18, color: 'var(--foreground)' }}>64dao.ru</dt>
                  <dd style={{ margin: 0, fontSize: 14, color: 'var(--muted-foreground)' }}>платформа стратегической диагностики</dd>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', alignItems: 'baseline', columnGap: 24 }}>
                  <dt style={{ maxWidth: 96, fontSize: 18, color: 'var(--foreground)' }}>Ответ по форме</dt>
                  <dd style={{ margin: 0, fontSize: 14, color: 'var(--muted-foreground)' }}>обратная связь для запросов и партнёров</dd>
                </div>
              </dl>
            </div>
            <div>
              {contactSent ? (
                <div
                  style={{
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--card)',
                    padding: 32,
                    textAlign: 'center',
                    color: 'var(--foreground)',
                    boxShadow: '0 30px 80px -40px rgba(20,30,60,0.25)',
                  }}
                >
                  Спасибо! Ваше сообщение отправлено.
                </div>
              ) : (
                <form onSubmit={submitForm} style={{ display: 'grid', gap: 20 }}>
                  <label style={{ display: 'block' }}>
                    <span style={{ marginBottom: 8, display: 'block', fontSize: 14, fontWeight: 500, color: 'var(--foreground)' }}>
                      Имя
                    </span>
                    <input
                      required
                      maxLength={100}
                      placeholder="Как к вам обращаться"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="landing-input"
                      style={{
                        width: '100%',
                        borderRadius: 6,
                        border: '1px solid var(--border)',
                        background: 'var(--card)',
                        padding: '12px 16px',
                        fontSize: 16,
                        color: 'var(--foreground)',
                        fontFamily: 'Inter, sans-serif',
                      }}
                    />
                  </label>
                  <label style={{ display: 'block' }}>
                    <span style={{ marginBottom: 8, display: 'block', fontSize: 14, fontWeight: 500, color: 'var(--foreground)' }}>
                      Email
                    </span>
                    <input
                      required
                      type="email"
                      maxLength={255}
                      placeholder="name@company.ru"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      className="landing-input"
                      style={{
                        width: '100%',
                        borderRadius: 6,
                        border: '1px solid var(--border)',
                        background: 'var(--card)',
                        padding: '12px 16px',
                        fontSize: 16,
                        color: 'var(--foreground)',
                        fontFamily: 'Inter, sans-serif',
                      }}
                    />
                  </label>
                  <label style={{ display: 'block' }}>
                    <span style={{ marginBottom: 8, display: 'block', fontSize: 14, fontWeight: 500, color: 'var(--foreground)' }}>
                      Сообщение
                    </span>
                    <textarea
                      required
                      maxLength={1000}
                      rows={5}
                      placeholder="Расскажите, какой вопрос хотите обсудить"
                      value={form.message}
                      onChange={(e) => setForm({ ...form, message: e.target.value })}
                      className="landing-input"
                      style={{
                        width: '100%',
                        borderRadius: 6,
                        border: '1px solid var(--border)',
                        background: 'var(--card)',
                        padding: '12px 16px',
                        fontSize: 16,
                        color: 'var(--foreground)',
                        resize: 'vertical',
                        fontFamily: 'Inter, sans-serif',
                      }}
                    />
                  </label>
                  <button
                    type="submit"
                    className="landing-btn-accent"
                    style={{
                      marginTop: 8,
                      display: 'inline-flex',
                      width: '100%',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: 6,
                      background: 'var(--foreground)',
                      padding: '16px 32px',
                      fontSize: 14,
                      fontWeight: 500,
                      color: 'var(--background)',
                      border: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    Отправить
                  </button>
                </form>
              )}
            </div>
          </div>
        </section>

        {/* FINAL CTA */}
        <section id="cta" style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto', padding: '112px 40px', textAlign: 'center' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 12,
                fontSize: 12,
                textTransform: 'uppercase',
                letterSpacing: '0.22em',
                color: 'var(--muted-foreground)',
              }}
            >
              <span style={{ height: 1, width: 32, background: 'var(--accent)' }} />
              Точка сверки
              <span style={{ height: 1, width: 32, background: 'var(--accent)' }} />
            </div>
            <h2 style={{ margin: '24px auto 0', maxWidth: 760, fontSize: 'clamp(36px,5.2vw,64px)', lineHeight: 1.05, color: 'var(--foreground)' }}>
              Узнайте свою фазу до следующего крупного решения
            </h2>
            <p style={{ margin: '24px auto 0', maxWidth: 560, fontSize: 16, color: 'var(--muted-foreground)' }}>
              Несколько минут сейчас — вместо месяцев разбора последствий потом.
            </p>
            <div style={{ marginTop: 40, display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
              <Link
                href="/login"
                className="landing-btn-accent"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 2,
                  background: 'var(--foreground)',
                  padding: '16px 32px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--background)',
                  textDecoration: 'none',
                }}
              >
                Пройти диагностику
              </Link>
              <a
                href="#contact"
                onClick={navClick}
                className="landing-btn-outline"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 2,
                  border: '1px solid rgba(0,0,0,0.2)',
                  padding: '16px 32px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--foreground)',
                  textDecoration: 'none',
                }}
              >
                Обсудить с нами
              </a>
            </div>
            <p style={{ marginTop: 32, fontSize: 14, color: 'var(--muted-foreground)' }}>
              {pricing.price.toLocaleString('ru-RU')} {pricing.currency} · Метод 1 + Метод 2 · обязательство по ясности
            </p>
          </div>
        </section>

        {/* FOOTER */}
        <footer style={{ background: 'var(--brand-teal)' }}>
          <div
            style={{
              maxWidth: 1280,
              margin: '0 auto',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))',
              gap: 32,
              padding: '48px 40px',
            }}
          >
            <div>
              <a href="#top" onClick={scrollTop} style={{ display: 'inline-flex', textDecoration: 'none' }}>
                <Logo />
              </a>
              <p style={{ margin: '16px 0 0', maxWidth: 260, fontSize: 14, color: 'rgba(255,255,255,0.8)' }}>
                Стратегическая диагностика компании на основе «И-цзин».
              </p>
              <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
                <a
                  href="https://t.me/"
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Telegram"
                  className="landing-social-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: 40,
                    width: 40,
                    borderRadius: '9999px',
                    background: 'rgba(255,255,255,0.18)',
                    color: '#1f3a52',
                    textDecoration: 'none',
                  }}
                >
                  <svg width={20} height={20} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71l-4.07-3.04-1.95 1.9c-.21.21-.39.4-.78.4z" />
                  </svg>
                </a>
                <a
                  href="https://vk.com/"
                  target="_blank"
                  rel="noreferrer"
                  aria-label="ВКонтакте"
                  className="landing-social-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: 40,
                    width: 40,
                    borderRadius: '9999px',
                    background: 'rgba(255,255,255,0.18)',
                    color: '#1f3a52',
                    textDecoration: 'none',
                    fontFamily: 'Inter, sans-serif',
                    fontWeight: 800,
                    fontSize: 14,
                    letterSpacing: '-0.02em',
                  }}
                >
                  VK
                </a>
                <a
                  href="https://max.ru/"
                  target="_blank"
                  rel="noreferrer"
                  aria-label="MAX"
                  className="landing-social-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: 40,
                    width: 40,
                    borderRadius: '9999px',
                    background: 'rgba(255,255,255,0.18)',
                    color: '#1f3a52',
                    textDecoration: 'none',
                    fontFamily: 'Inter, sans-serif',
                    fontWeight: 800,
                    fontSize: 11,
                    letterSpacing: '-0.01em',
                  }}
                >
                  MAX
                </a>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.7)' }}>
                Разделы
              </div>
              <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
                <li><a href="#how" onClick={navClick} className="landing-footer-link">Как это работает</a></li>
                <li><a href="#report" onClick={navClick} className="landing-footer-link">Что в отчёте</a></li>
                <li><a href="#price" onClick={navClick} className="landing-footer-link">Стоимость</a></li>
                <li><Link href="/about" className="landing-footer-link">О нас</Link></li>
                <li><a href="#contact" onClick={navClick} className="landing-footer-link">Контакты</a></li>
              </ul>
            </div>
            <div>
              <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.7)' }}>
                Правовая информация
              </div>
              <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
                <li><Link href="/documents/privacy-policy" className="landing-footer-link">Политика обработки персональных данных</Link></li>
                <li><Link href="/documents/user-agreement" className="landing-footer-link">Пользовательское соглашение</Link></li>
                <li><Link href="/documents/personal-data-consent" className="landing-footer-link">Согласие на обработку персональных данных</Link></li>
              </ul>
            </div>
            <div>
              <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.7)' }}>
                Партнёры
              </div>
              <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
                <li><a href="https://taoteam.ru" target="_blank" rel="noreferrer" className="landing-footer-link">taoteam.ru</a></li>
              </ul>
            </div>
          </div>
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.2)' }}>
            <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 40px', fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>
              © {year} 64 ДАО — все права защищены
            </div>
          </div>
        </footer>
      </main>

      {!cookieAccepted && (
        <div
          style={{
            position: 'fixed',
            left: 16,
            right: 16,
            bottom: 16,
            zIndex: 50,
            maxWidth: 768,
            margin: '0 auto',
            borderRadius: 2,
            border: '1px solid var(--border)',
            background: 'var(--card)',
            padding: 20,
            boxShadow: '0 20px 60px -20px rgba(0,0,0,0.3)',
          }}
        >
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--foreground)' }}>
            Мы используем файлы cookie и рекомендательные технологии. Подробно описали в Политике конфиденциальности
            (вообще ничего лишнего не собираем и за границу не передаём). Но вы можете отключить cookies в своём
            браузере, если не согласны.
          </p>
          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={acceptCookie}
              className="landing-btn-accent"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 2,
                background: 'var(--accent)',
                padding: '10px 20px',
                fontSize: 14,
                fontWeight: 500,
                color: 'var(--accent-foreground)',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Соглашаюсь с использованием cookies
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

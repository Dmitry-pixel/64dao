'use client'
import { useEffect, useRef } from 'react'
import './landing.css'

export default function HomePage() {
  const cookieRef = useRef<HTMLDivElement>(null)

  function closeCookie() {
    cookieRef.current?.classList.remove('visible')
    try { localStorage.setItem('64dao-cookie', '1') } catch(e) {}
  }

  function handleContactSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const btn = (e.target as HTMLFormElement).querySelector('button[type="submit"]') as HTMLButtonElement
    if (!btn) return
    btn.disabled = true
    btn.textContent = 'Спасибо, ответим в течение суток'
    setTimeout(() => {
      btn.disabled = false
      btn.textContent = 'Отправить'
      ;(e.target as HTMLFormElement).reset()
    }, 3500)
  }

  useEffect(() => {
    const burger = document.getElementById('burger')
    const mobileMenu = document.getElementById('mobile-menu')
    if (!burger || !mobileMenu) return

    function closeMobileMenu() {
      burger!.classList.remove('is-open')
      mobileMenu!.classList.remove('is-open')
      burger!.setAttribute('aria-expanded', 'false')
      mobileMenu!.setAttribute('aria-hidden', 'true')
      document.body.style.overflow = ''
    }
    function openMobileMenu() {
      burger!.classList.add('is-open')
      mobileMenu!.classList.add('is-open')
      burger!.setAttribute('aria-expanded', 'true')
      mobileMenu!.setAttribute('aria-hidden', 'false')
      document.body.style.overflow = 'hidden'
    }
    const burgerClick = () => {
      if (mobileMenu!.classList.contains('is-open')) closeMobileMenu()
      else openMobileMenu()
    }
    burger.addEventListener('click', burgerClick)
    mobileMenu.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMobileMenu))
    const escHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileMenu!.classList.contains('is-open')) closeMobileMenu()
    }
    window.addEventListener('keydown', escHandler)
    const mq = window.matchMedia('(min-width: 761px)')
    const mqHandler = (e: MediaQueryListEvent) => { if (e.matches) closeMobileMenu() }
    mq.addEventListener('change', mqHandler)

    const header = document.getElementById('header')
    const onScroll = () => { header?.classList.toggle('scrolled', window.scrollY > 8) }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()

    const t = setTimeout(() => {
      try { if (localStorage.getItem('64dao-cookie') === '1') return } catch(e) {}
      cookieRef.current?.classList.add('visible')
    }, 2500)

    document.querySelectorAll('a[href^="#"]').forEach(a => {
      a.addEventListener('click', (e) => {
        const id = (a as HTMLAnchorElement).getAttribute('href')
        if (!id || id.length < 2) return
        const el = document.querySelector(id)
        if (!el) return
        e.preventDefault()
        const top = el.getBoundingClientRect().top + window.scrollY - 60
        window.scrollTo({ top, behavior: 'smooth' })
      })
    })

    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          ;(e.target as HTMLElement).style.opacity = '1'
          ;(e.target as HTMLElement).style.transform = 'translateY(0)'
          io.unobserve(e.target)
        }
      })
    }, { threshold: 0.12 })
    document.querySelectorAll('.section, .contact-section, .hero-left, .hero-right').forEach(el => {
      ;(el as HTMLElement).style.opacity = '0'
      ;(el as HTMLElement).style.transform = 'translateY(18px)'
      ;(el as HTMLElement).style.transition = 'opacity .7s ease, transform .7s ease'
      io.observe(el)
    })

    return () => {
      burger.removeEventListener('click', burgerClick)
      window.removeEventListener('keydown', escHandler)
      mq.removeEventListener('change', mqHandler)
      window.removeEventListener('scroll', onScroll)
      clearTimeout(t)
      io.disconnect()
    }
  }, [])

  return (
    <>
{/* ========== HEADER ========== */}
<header className="site-header" id="header">
  <div className="wrap header-inner">
    <a href="#" className="logo" aria-label="64 ДАО">
      <img className="logo-mark" src="/assets/logo.svg" alt="64 ДАО" />
    </a>
    <nav className="nav">
      <a href="https://64dao.ru/about">О нас</a>
      <a href="#pricing">Стоимость</a>
      <a href="#process">Процесс</a>
      <a href="#contacts">Контакты</a>
    </nav>
    <a href="https://64dao.ru/login" className="btn btn--outline header-login" style="height:44px; padding:0 20px; font-size:14px;">Вход / Регистрация</a>
    <button className="burger" id="burger" aria-label="Меню" aria-expanded="false" aria-controls="mobile-menu"><span></span><span></span><span></span></button>
  </div>
</header>

{/* ========== MOBILE MENU ========== */}
<div className="mobile-menu" id="mobile-menu" aria-hidden="true">
  <nav>
    <a href="https://64dao.ru/about">О&nbsp;нас</a>
    <a href="#pricing">Стоимость</a>
    <a href="#process">Процесс</a>
    <a href="#method2">Метод 2</a>
    <a href="#contacts">Контакты</a>
  </nav>
  <a href="https://64dao.ru/login" className="mobile-menu-cta">Вход / Регистрация</a>
  <div className="mm-meta">64 ДАО &middot; стратегическая диагностика</div>
</div>

{/* ========== HERO ========== */}
<section className="hero">
  <div className="wrap hero-grid">
    <div className="hero-left">
      <div className="hero-meta">
        <span className="divider"></span>
        <span className="eyebrow">Стратегическая диагностика · И-цзин</span>
      </div>
      <h1>«И-цзин» для разработки и&nbsp;управления стратегией <em>изменений</em> компании</h1>
      <p className="hero-sub">
        64 ДАО — инструмент стратегического диагностирования, основанный на метафизике «И-цзин». Определяет, в&nbsp;какой фазе находится компания, какие управленческие решения уместны сейчас, и&nbsp;служит опорой при проведении стратегических сессий.
      </p>
      <div className="hero-cta">
        <a href="#pricing" className="btn btn--red btn--lg">
          Узнать стоимость
          <svg className="arrow" viewBox="0 0 16 10" fill="none"><path d="M1 5h13M10 1l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>
        </a>
        <div className="pdf-buttons">
          <a className="pdf-btn" href="#" download>
            <svg className="pdf-ico" width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 2v9m0 0l-3.5-3.5M9 11l3.5-3.5M3 14v1a1 1 0 001 1h10a1 1 0 001-1v-1" stroke="currentColor" stroke-width="1.4" stroke-linecap="square"/>
            </svg>
            <span><small>Пример отчёта</small>Метод 1</span>
          </a>
          <a className="pdf-btn" href="#" download>
            <svg className="pdf-ico" width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 2v9m0 0l-3.5-3.5M9 11l3.5-3.5M3 14v1a1 1 0 001 1h10a1 1 0 001-1v-1" stroke="currentColor" stroke-width="1.4" stroke-linecap="square"/>
            </svg>
            <span><small>Пример отчёта</small>Метод 2</span>
          </a>
        </div>
      </div>
    </div>
    <div className="hero-right">
      <div className="hero-corner-tl"></div>
      <div className="hero-corner-br"></div>
      <video className="hero-lattice" src="/assets/ching.mp4" autoPlay loop muted playsinline></video>
      <div className="hero-caption">Много сценариев. Актуален один.</div>
    </div>
  </div>
</section>

{/* ========== METHOD: 6 параметров как гексаграмма ========== */}
<section className="section section--alt" id="method">
  <div className="wrap">
    <div className="section-head">
      <div>
        <span className="label">01 — Метод</span>
      </div>
      <div>
        <h2>64 ДАО — инструмент для работы с&nbsp;неопределённостью</h2>
        <p className="lead">
          В&nbsp;основе системы — принцип «И-цзин», которому более 5&nbsp;000 лет: всё во Вселенной находится в&nbsp;движении, а гармония достигается не через статичность, а через адаптацию к&nbsp;переменам. Каждая компания в&nbsp;моменте описывается шестью параметрами — тремя внутренними и&nbsp;тремя внешними, — которые складываются в&nbsp;одну из 64&nbsp;гексаграмм.
        </p>
      </div>
    </div>

    <div className="method-grid">
      <div className="method-text">
        <p style="font-size:17px; color: var(--ink); margin-bottom: 18px;">
          <strong>Гексаграмма — это формальная диаграмма данных о&nbsp;вашей компании.</strong>
        </p>
        <p>
          Шесть параметров — это срез стратегического состояния. Их сочетание определяет текущую гексаграмму. Когда конфигурация ограничивает рост или перестаёт соответствовать реальности, метод подсказывает целевую гексаграмму и&nbsp;путь перехода.
        </p>
        <p>
          Конгломератам и&nbsp;крупным компаниям удобно применять анализ к&nbsp;отдельным подразделениям — каждое получает собственную гексаграмму и&nbsp;сценарий.
        </p>
        <div className="stat-row">
          <div className="stat">
            <div className="num">6</div>
            <div className="lbl">параметров<br>в диагностике</div>
          </div>
          <div className="stat">
            <div className="num">64</div>
            <div className="lbl">стратегических<br>сценария</div>
          </div>
          <div className="stat">
            <div className="num">5 000</div>
            <div className="lbl">лет<br>методологии</div>
          </div>
        </div>
      </div>

      <div className="hex-board">
        <div className="hex-tag external">Внешние факторы</div>
        <div className="hex-rows">
          {/* Lines are listed bottom-up; column-reverse flips them so visual top = top line */}
          <div className="hex-row">
            <div className="hex-label left"><span>Цель</span><span className="num">01</span></div>
            <div className="hex-line solid"></div>
            <div className="hex-label"></div>
          </div>
          <div className="hex-row">
            <div className="hex-label left"><span>Стратегия</span><span className="num">02</span></div>
            <div className="hex-line broken"></div>
            <div className="hex-label"></div>
          </div>
          <div className="hex-row">
            <div className="hex-label left"><span>Организация</span><span className="num">03</span></div>
            <div className="hex-line solid"></div>
            <div className="hex-label"></div>
          </div>
          {/* divider between internal/external */}
          <div className="hex-divider-row">
            <div></div>
            <div className="hex-divider"></div>
            <div></div>
          </div>
          <div className="hex-row">
            <div className="hex-label left"></div>
            <div className="hex-line accent broken"></div>
            <div className="hex-label"><span className="num">04</span><span>Тип ценности</span></div>
          </div>
          <div className="hex-row">
            <div className="hex-label left"></div>
            <div className="hex-line accent solid"></div>
            <div className="hex-label"><span className="num">05</span><span>Состояние рынка</span></div>
          </div>
          <div className="hex-row">
            <div className="hex-label left"></div>
            <div className="hex-line accent broken"></div>
            <div className="hex-label"><span className="num">06</span><span>Тип потребителя</span></div>
          </div>
        </div>
        <div className="hex-tag internal">Внутренние факторы</div>
      </div>
    </div>
  </div>
</section>

{/* ========== PROCESS ========== */}
<section className="section" id="process">
  <div className="wrap">
    <div className="section-head">
      <div><span className="label">02 — Процесс</span></div>
      <div>
        <h2>Как устроен процесс</h2>
        <p className="lead">
          Тексты «И-цзин» в&nbsp;отчёте адаптированы для разработки и&nbsp;управления стратегией компании, используя гексаграммы как метафоры для анализа ситуации, выбора тактики и&nbsp;прогнозирования изменений. После ответов на&nbsp;вопросы система анализирует и&nbsp;формирует отчёт.
        </p>
      </div>
    </div>

    <div className="steps">
      <div className="step">
        <div className="step-top">
          <span className="step-num">— 01 —</span>
          <div className="step-hex">
            <div className="l"></div>
            <div className="l b"></div>
            <div className="l b"></div>
            <div className="l"></div>
            <div className="l b"></div>
            <div className="l"></div>
          </div>
        </div>
        <h3>Отвечаете на&nbsp;вопросы</h3>
        <p>Структурированная форма диагностики: шесть блоков вопросов о&nbsp;вашей компании и&nbsp;её окружении.</p>
      </div>
      <div className="step">
        <div className="step-top">
          <span className="step-num">— 02 —</span>
          <div className="step-hex t">
            <div className="l"></div>
            <div className="l"></div>
            <div className="l b"></div>
            <div className="l b"></div>
            <div className="l"></div>
            <div className="l b"></div>
          </div>
        </div>
        <h3>Система анализирует</h3>
        <p>Алгоритм определяет вашу текущую гексаграмму, выявляет сценарий и&nbsp;возможный переход.</p>
      </div>
      <div className="step">
        <div className="step-top">
          <span className="step-num">— 03 —</span>
          <div className="step-hex">
            <div className="l b"></div>
            <div className="l"></div>
            <div className="l"></div>
            <div className="l b"></div>
            <div className="l"></div>
            <div className="l"></div>
          </div>
        </div>
        <h3>Получаете отчёт</h3>
        <p>PDF с&nbsp;разбором сценария: инновационная стратегия, ценностная дисциплина, принципы лидерства, фокус, путь роста.</p>
      </div>
    </div>

    <div className="process-cta">
      <a href="https://64dao.ru/login" className="btn btn--deep">
        Получить отчёт
        <svg className="arrow" viewBox="0 0 16 10" fill="none"><path d="M1 5h13M10 1l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>
      </a>
    </div>
  </div>
</section>

{/* ========== AUDIENCE ========== */}
<section className="section section--alt">
  <div className="wrap">
    <div className="section-head">
      <div><span className="label">03 — Кому подходит</span></div>
      <div>
        <h2>Кому подходит инструмент</h2>
        <p className="lead">
          Стратегическая диагностика помогает понять текущее состояние, выбрать направление развития и&nbsp;спланировать переход от «как есть» к&nbsp;«как должно быть».
        </p>
      </div>
    </div>

    <div className="audience-grid">
      <div className="aud-card">
        <div className="aud-hex">
          <div className="l b"></div>
          <div className="l"></div>
          <div className="l b"></div>
          <div className="l"></div>
          <div className="l b"></div>
          <div className="l"></div>
        </div>
        <div className="aud-num">01 — 03</div>
        <div className="aud-title">Собственникам<br>и&nbsp;руководителям</div>
        <div className="aud-sub">Подходит, если:</div>
        <ul className="aud-list">
          <li>Компания упёрлась в&nbsp;потолок роста</li>
          <li>Нужен новый вектор развития</li>
          <li>Решения принимаются в&nbsp;условиях неопределённости</li>
          <li>Цена ошибки высока</li>
        </ul>
      </div>
      <div className="aud-card">
        <div className="aud-hex">
          <div className="l"></div>
          <div className="l b"></div>
          <div className="l"></div>
          <div className="l b"></div>
          <div className="l"></div>
          <div className="l b"></div>
        </div>
        <div className="aud-num">02 — 03</div>
        <div className="aud-title">Менеджерам</div>
        <div className="aud-sub">Подходит, если:</div>
        <ul className="aud-list">
          <li>Меняется стратегия, структура или модель бизнеса</li>
          <li>Нужно согласовывать действия разных подразделений</li>
          <li>Важно понимать последствия управленческих решений</li>
        </ul>
      </div>
      <div className="aud-card">
        <div className="aud-hex">
          <div className="l"></div>
          <div className="l"></div>
          <div className="l b"></div>
          <div className="l"></div>
          <div className="l"></div>
          <div className="l b"></div>
        </div>
        <div className="aud-num">03 — 03</div>
        <div className="aud-title">Компаниям<br>в&nbsp;точке перехода</div>
        <div className="aud-sub">Подходит, если:</div>
        <ul className="aud-list">
          <li>Быстро растёт и&nbsp;теряет управляемость</li>
          <li>Проходит через кризис или спад</li>
          <li>Выходит на&nbsp;новые рынки</li>
          <li>Меняет формат работы и&nbsp;команду</li>
        </ul>
      </div>
    </div>

    <div className="audience-cta">
      <a href="https://64dao.ru/login" className="btn btn--deep">
        Получить отчёт
        <svg className="arrow" viewBox="0 0 16 10" fill="none"><path d="M1 5h13M10 1l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>
      </a>
    </div>
  </div>
</section>

{/* ========== METHOD 2 ========== */}
<section className="section" id="method2">
  <div className="wrap">
    <div className="m2-grid">
      <div className="m2-text">
        <span className="eyebrow">Второй уровень · Метод 2</span>
        <h2>Диагностика бизнес-модели</h2>
        <p>
          Канва бизнес-модели как инструмент диалога руководителей, а&nbsp;не статический документ. Акцент — на&nbsp;выявлении неопределённостей, гипотез и&nbsp;стратегических вопросов в&nbsp;каждом блоке.
        </p>
        <p>
          Форма бизнес-модели соответствует принципу формы в&nbsp;Дао: всё связано со&nbsp;всем, и&nbsp;незаполненный блок — это пробоина в&nbsp;корпусе.
        </p>
        <div className="m2-warn">
          <strong>Системный риск.</strong> Если хотя&nbsp;бы один блок остаётся без оценки, бизнес-модель не&nbsp;работает целиком: компания может разориться из-за разрыва, который сегодня кажется незначительным.
        </div>
        <div style="margin-top: 32px;">
          <a href="https://64dao.ru/login" className="btn btn--outline">
            Пройти диагностику
            <svg className="arrow" viewBox="0 0 16 10" fill="none"><path d="M1 5h13M10 1l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>
          </a>
        </div>
      </div>

      <div>
        <div className="m2-canvas-title">9 блоков бизнес-модели</div>
        <div className="canvas" aria-label="Канва бизнес-модели">
          <div className="canvas-cell active">
            <div className="cn">01</div>
            <div className="ct">Ключевые партнёры</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">02</div>
            <div className="ct">Ключевые активности</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">03</div>
            <div className="ct">Ключевые ресурсы</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">04</div>
            <div className="ct">Ценностное предложение</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">05</div>
            <div className="ct">Отношения с&nbsp;клиентами</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">06</div>
            <div className="ct">Каналы</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">07</div>
            <div className="ct">Сегменты клиентов</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">08</div>
            <div className="ct">Структура издержек</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
          <div className="canvas-cell">
            <div className="cn">09</div>
            <div className="ct">Потоки доходов</div>
            <div className="clines"><span></span><span></span><span></span></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

{/* ========== PRICING ========== */}
<section className="section section--alt" id="pricing">
  <div className="wrap">
    <div className="section-head">
      <div><span className="label">04 — Стоимость</span></div>
      <div>
        <h2>Один доступ. Один результат.</h2>
        <p className="lead">
          Покупая доступ к&nbsp;платформе, вы получаете весь цикл диагностики и&nbsp;готовый PDF-отчёт. Без подписок, дополнительных тарифов и&nbsp;скрытых платежей.
        </p>
      </div>
    </div>
    <div className="pricing-wrap">
      <div className="price-card">
        <div className="price-eyebrow">Оплата диагностики</div>
        <h3>Полный отчёт 64&nbsp;ДАО</h3>
        <div className="price-amount-wrap">
          <div className="price-amount">14&nbsp;900<small>₽</small></div>
          <div className="price-note">разовая оплата · НДС не облагается</div>
        </div>
        <ul className="price-list">
          <li><span className="k">Диагностика</span><span className="v">Метод 1 + Метод 2</span></li>
          <li><span className="k">PDF-отчёт</span><span className="v">Включён</span></li>
          <li><span className="k">Онлайн-просмотр</span><span className="v">Без ограничений</span></li>
          <li><span className="k">Срок готовности</span><span className="v">До 30 минут</span></li>
        </ul>
        <a href="https://64dao.ru/login" className="price-cta">
          Перейти к&nbsp;оплате
          <svg className="arrow" viewBox="0 0 16 10" fill="none"><path d="M1 5h13M10 1l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="square"/></svg>
        </a>
      </div>
    </div>
  </div>
</section>

{/* ========== CONTACT ========== */}
<section className="contact-section" id="contacts">
  <div className="wrap">
    <div className="contact-grid">
      <div className="contact-card">
        <div className="contact-eyebrow">Контакты</div>
        <h2 className="contact-title">Свяжитесь<br>с&nbsp;нами</h2>
        <p className="contact-lead">
          Оставьте сообщение, если хотите обсудить внедрение 64&nbsp;ДАО, стратегическую сессию или доступ для команды.
        </p>
        <div className="contact-meta">
          <div className="row">
            <div className="h">64dao.ru</div>
            <div className="d">платформа стратегической диагностики</div>
          </div>
          <div className="row">
            <div className="h">Ответ по форме</div>
            <div className="d">обратная связь для запросов и&nbsp;партнёрств</div>
          </div>
        </div>
      </div>
      <form className="contact-form" id="contact-form" onSubmit={handleContactSubmit}>
        <div className="field">
          <label htmlFor="f-name">Имя</label>
          <input id="f-name" name="name" type="text" placeholder="Как к&nbsp;вам обращаться" required />
        </div>
        <div className="field">
          <label htmlFor="f-email">Email</label>
          <input id="f-email" name="email" type="email" placeholder="name@company.ru" required />
        </div>
        <div className="field">
          <label htmlFor="f-msg">Сообщение</label>
          <textarea id="f-msg" name="message" placeholder="Расскажите, какой вопрос хотите обсудить" required></textarea>
        </div>
        <button type="submit" className="form-submit">Отправить</button>
      </form>
    </div>
  </div>
</section>

{/* ========== FOOTER ========== */}
<footer className="site-footer">
  <div className="wrap">
    <div className="footer-grid">
      <div className="footer-brand">
        <a href="#" className="logo" aria-label="64 ДАО">
          <img className="logo-mark" src="/assets/logo.svg" alt="64 ДАО" style="height:56px;" />
        </a>
        <p className="footer-tag">
          Стратегическая диагностика бизнеса на&nbsp;основе принципа «И-цзин». Готовые рекомендации в&nbsp;PDF.
        </p>
      </div>
      <div className="footer-col">
        <h4>Карта сайта</h4>
        <ul className="footer-list">
          <li><a href="https://64dao.ru/about">О&nbsp;нас</a></li>
          <li><a href="#pricing">Стоимость</a></li>
          <li><a href="#process">Процесс</a></li>
          <li><a href="#method2">Метод 2</a></li>
        </ul>
      </div>
      <div className="footer-col">
        <h4>Юридическое</h4>
        <ul className="footer-list">
          <li><a href="/privacy">Политика обработки персональных данных</a></li>
          <li><a href="/terms">Пользовательское соглашение</a></li>
          <li><a href="/consent">Согласие на обработку персональных данных</a></li>
        </ul>
      </div>
      <div className="footer-col">
        <h4>Контакты</h4>
        <ul className="footer-list">
          <li><a href="#contacts">Написать нам</a></li>
          <li><a href="https://64dao.ru/login">Вход / Регистрация</a></li>
        </ul>
      </div>
    </div>
    <div className="footer-bottom">
      <div>© 2024–2026 · 64 ДАО · Все права защищены</div>
      <div className="footer-socials">
        <a className="soc" href="https://t.me/" aria-label="Telegram" target="_blank" rel="noopener">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M21.5 3.5L2.6 10.8c-1.1.4-1.1 1.5-.2 1.8l4.8 1.5 1.8 5.7c.2.7.4.9 1 .9.5 0 .7-.2 1-.6l2.4-2.3 5 3.7c.9.5 1.6.2 1.8-.8L23 5c.3-1.2-.4-1.8-1.5-1.5zm-4.2 4.2l-8 7.2-.3 3.2-1.4-4.4 9.7-6z"/>
          </svg>
        </a>
        <a className="soc" href="https://vk.com/" aria-label="VK" target="_blank" rel="noopener">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M2 6.2c.1-1.5 1.1-2.5 2.7-2.5h14.6c1.6 0 2.6 1 2.7 2.5l.3 11.6c0 1.5-1 2.5-2.6 2.5H4.6C3 20.3 2 19.3 2 17.8L2 6.2zm5.4 1c-.5 0-.7.2-.6.7.7 3.6 2.8 6.9 7.6 9 .5.2.7.1.7-.4v-1.7c0-.5.2-.6.5-.4.7.6 1.7 1.7 2.4 2.4.3.3.5.3.9.3h2.1c.5 0 .6-.3.3-.8-.4-.8-1.7-2.4-2.4-3.2-.3-.4-.3-.6 0-1 .6-.8 1.8-2.5 2.2-3.4.3-.5.1-.8-.4-.8h-2c-.5 0-.7.1-.9.5-.5 1-1.3 2.2-2 2.9-.3.3-.5.3-.6-.2-.1-1.2 0-2.6-.1-3-.1-.6-.4-.8-1-.8h-2.5c-.4 0-.7.2-.7.4 0 .3.6.2.6 1.3v3c0 .4-.1.5-.4.3-1.6-1.1-2.6-3-3.2-4.6-.2-.4-.3-.5-.8-.5H7.4z"/>
          </svg>
        </a>
        <a className="soc" href="#" aria-label="Я.Мессенджер" target="_blank" rel="noopener">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 2C6.5 2 2 6.3 2 11.6c0 2.9 1.4 5.4 3.6 7.1L4.4 22l3.8-1.6c1.2.5 2.5.8 3.8.8 5.5 0 10-4.3 10-9.6S17.5 2 12 2zm0 17.6c-1.2 0-2.4-.3-3.5-.7l-.3-.1-2.3 1 .8-2.4-.2-.3C5.3 15.6 4.2 13.7 4.2 11.6 4.2 7.4 7.7 4 12 4s7.8 3.4 7.8 7.6-3.5 8-7.8 8z"/>
          </svg>
        </a>
      </div>
    </div>
  </div>
</footer>

{/* ========== COOKIE ========== */}
<div className="cookie" id="cookie" ref={cookieRef}>
  <button className="cookie-close" aria-label="Закрыть" onClick={closeCookie}>
    <svg width="14" height="14" viewBox="0 0 14 14"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" stroke-width="1.4"/></svg>
  </button>
  <p>Мы используем куки (cookies) с&nbsp;целью повышения удобства вашей работы с&nbsp;сайтом. Продолжая использовать сайт, вы&nbsp;даёте своё согласие на&nbsp;работу с&nbsp;этими файлами.</p>
  <button className="btn" onClick={closeCookie}>Продолжить</button>
</div>
    </>
  )
}

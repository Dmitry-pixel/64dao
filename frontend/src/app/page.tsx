'use client'
import { useEffect, useRef } from 'react'

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
      <style>{`
/* ---------- TOKENS ---------- */
  :root{
    --bg: #F6F5ED;
    --bg-2: #EFEDE0;
    --ink: #202020;
    --ink-2: #4A4A48;
    --ink-3: #7A7A78;
    --line: #D9D6C8;
    --line-2: #C0C1C5;
    --teal: #73BDC7;
    --lav:  #87A5D0;
    --deep: #124187;
    --red:  #DF3128;
    --max: 1240px;
    --pad-x: clamp(20px, 4vw, 80px);
    --section-y: clamp(72px, 9vw, 120px);
    --rad: 4px;
  }
  *{ box-sizing: border-box; }
  html,body{ margin:0; padding:0; background:var(--bg); color:var(--ink); }
  body{
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    font-size: 17px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }
  h1,h2,h3,h4{
    font-family: 'Golos Text', 'Inter', sans-serif;
    font-weight: 600;
    letter-spacing: -0.01em;
    line-height: 1.12;
    margin: 0;
    color: var(--ink);
  }
  h1{ font-size: clamp(36px, 4.4vw, 60px); letter-spacing: -0.02em; }
  h2{ font-size: clamp(28px, 3vw, 42px); letter-spacing: -0.015em; }
  h3{ font-size: clamp(20px, 1.7vw, 24px); }
  p{ margin: 0; color: var(--ink-2); }
  a{ color: inherit; text-decoration: none; }
  ::selection{ background: var(--teal); color: #fff; }

  .wrap{ max-width: var(--max); margin: 0 auto; padding: 0 var(--pad-x); }
  .eyebrow{
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-3);
    font-weight: 500;
  }
  .divider{
    width: 32px; height: 2px; background: var(--ink);
    display: inline-block; vertical-align: middle;
  }

  /* ---------- BUTTONS ---------- */
  .btn{
    display: inline-flex; align-items: center; justify-content: center; gap: 10px;
    height: 52px; padding: 0 24px;
    font-family: 'Inter', sans-serif; font-size: 15px; font-weight: 500;
    border-radius: var(--rad); border: 1px solid transparent;
    cursor: pointer; transition: all .18s ease;
    background: var(--ink); color: #fff; letter-spacing: 0;
  }
  .btn:hover{ transform: translateY(-1px); box-shadow: 0 8px 24px -12px rgba(0,0,0,.35); }
  .btn--deep{ background: var(--deep); }
  .btn--red{ background: var(--red); }
  .btn--red:hover{ background: #C9281F; }
  .btn--outline{
    background: transparent; color: var(--ink);
    border-color: var(--ink); 
  }
  .btn--outline:hover{ background: var(--ink); color: var(--bg); }
  .btn--ghost{
    background: transparent; color: var(--ink);
    border-color: var(--line); height: 48px; padding: 0 18px; font-size: 14px;
  }
  .btn--ghost:hover{ border-color: var(--ink); }
  .btn--lg{ height: 60px; padding: 0 32px; font-size: 16px; }
  .btn .arrow{ width: 16px; height: 10px; }
  .arrow{ width: 16px; height: 10px; flex-shrink: 0; }

  /* ---------- HEADER ---------- */
  .site-header{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    background: rgba(198,224,228,0.88);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid transparent;
    transition: background .2s, border-color .2s;
  }
  .site-header.scrolled{
    background: rgba(198,224,228,0.96);
    border-bottom-color: rgba(18,65,135,0.08);
    box-shadow: 0 1px 0 rgba(0,0,0,0.04);
  }
  .site-header .nav a{ color: var(--ink); }
  .site-header .nav a:hover{ color: var(--deep); }
  .site-header .nav a::after{ background: var(--deep); }
  .site-header .btn--outline{
    color: var(--ink); border-color: rgba(18,65,135,0.35);
  }
  .site-header .btn--outline:hover{
    background: var(--deep); color: #fff; border-color: var(--deep);
  }
  .header-inner{
    display: flex; align-items: center; justify-content: space-between;
    height: 76px;
  }
  .logo{
    display: flex; align-items: center; gap: 12px;
    font-family: 'Golos Text'; font-weight: 600; font-size: 18px;
    letter-spacing: -0.01em;
  }
  .logo-mark{ height: 44px; width: auto; display: block; }
  .nav{
    display: flex; gap: 36px; align-items: center;
    font-size: 14px; font-weight: 500;
  }
  .nav a{
    position: relative; padding: 6px 0;
    color: var(--ink-2); transition: color .15s;
  }
  .nav a:hover{ color: var(--ink); }
  .nav a::after{
    content:''; position: absolute; left: 0; right: 0; bottom: 0;
    height: 1px; background: var(--ink); transform: scaleX(0);
    transform-origin: left; transition: transform .2s;
  }
  .nav a:hover::after{ transform: scaleX(1); }
  .burger{ display: none; }
  .burger.is-open span:nth-child(1){ transform: translateY(5.5px) rotate(45deg); }
  .burger.is-open span:nth-child(2){ opacity: 0; }
  .burger.is-open span:nth-child(3){ transform: translateY(-5.5px) rotate(-45deg); }

  /* ---------- MOBILE MENU ---------- */
  .mobile-menu{
    position: fixed; inset: 0; z-index: 95;
    background: #C6E0E4;
    display: none;
    flex-direction: column;
    padding: 96px var(--pad-x) 40px;
    overflow-y: auto;
    opacity: 0;
    transition: opacity .25s ease;
  }
  .mobile-menu.is-open{ display: flex; opacity: 1; }
  .mobile-menu nav{
    display: flex; flex-direction: column;
    border-top: 1px solid rgba(18,65,135,0.18);
  }
  .mobile-menu nav a{
    display: flex; justify-content: space-between; align-items: center;
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 32px; font-weight: 500;
    color: var(--ink); letter-spacing: -0.01em;
    padding: 22px 0;
    border-bottom: 1px solid rgba(18,65,135,0.18);
    transition: color .15s;
  }
  .mobile-menu nav a:hover{ color: var(--deep); }
  .mobile-menu nav a::after{
    content: '→';
    font-family: 'Inter', sans-serif;
    font-size: 22px; color: var(--ink-3); font-weight: 400;
    transition: transform .2s, color .15s;
  }
  .mobile-menu nav a:hover::after{ transform: translateX(4px); color: var(--deep); }
  .mobile-menu-cta{
    margin-top: 36px;
    height: 56px;
    background: var(--deep); color: #fff;
    border-radius: var(--rad);
    display: flex; align-items: center; justify-content: center; gap: 10px;
    font-size: 15px; font-weight: 500;
  }
  .mobile-menu-cta:hover{ background: #0E3573; }
  .mobile-menu .mm-meta{
    margin-top: auto;
    padding-top: 32px;
    font-size: 13px;
    color: var(--ink-3);
    letter-spacing: 0.04em;
  }

  /* ---------- HERO ---------- */
  .hero{
    padding-top: 140px;
    padding-bottom: var(--section-y);
    position: relative; overflow: hidden;
  }
  .hero-grid{
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 64px;
    align-items: center;
  }
  .hero-left{ position: relative; z-index: 2; }
  .hero-meta{
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 28px;
  }
  .hero h1{
    margin-bottom: 28px;
    text-wrap: balance;
  }
  .hero h1 em{
    font-style: normal; color: var(--deep);
    font-family: 'Golos Text';
  }
  .hero-sub{
    font-size: 18px; line-height: 1.55;
    color: var(--ink-2); max-width: 560px;
    margin-bottom: 40px;
    text-wrap: pretty;
  }
  .hero-cta{
    display: flex; flex-wrap: wrap; gap: 12px;
    align-items: center;
  }
  .hero-cta .btn--red{ padding-right: 26px; }
  .hero-cta .pdf-buttons{
    display: flex; gap: 10px; flex-wrap: wrap;
  }
  .pdf-btn{
    display: inline-flex; align-items: center; gap: 10px;
    height: 52px; padding: 0 18px;
    font-size: 14px; color: var(--ink); border: 1px solid var(--line);
    border-radius: var(--rad); background: transparent;
    cursor: pointer; transition: all .15s;
  }
  .pdf-btn:hover{ border-color: var(--ink); background: rgba(0,0,0,0.02); }
  .pdf-btn .pdf-ico{ color: var(--deep); }
  .pdf-btn small{
    display: block; font-size: 11px; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--ink-3); font-weight: 500;
    margin-bottom: 2px;
  }

  .hero-right{
    position: relative;
    aspect-ratio: 1 / 1;
    display: flex; align-items: center; justify-content: center;
  }
  .hero-lattice{
    width: 100%; height: 100%;
    object-fit: contain;
    mix-blend-mode: multiply;
    filter: contrast(1.05);
  }
  .hero-caption{
    position: absolute;
    bottom: -8px; left: 50%; transform: translateX(-50%);
    font-family: 'Golos Text'; font-size: 15px;
    color: var(--ink-2); white-space: nowrap;
    letter-spacing: 0.02em;
  }
  .hero-caption::before{
    content:''; display: inline-block; width: 16px; height: 1px;
    background: var(--ink-2); vertical-align: middle; margin-right: 10px;
  }
  .hero-corner-tl, .hero-corner-br{
    position: absolute; width: 80px; height: 80px;
    border-color: var(--line-2);
    pointer-events: none;
  }
  .hero-corner-tl{ top: 0; left: 0; border-top: 1px solid; border-left: 1px solid; }
  .hero-corner-br{ bottom: 0; right: 0; border-bottom: 1px solid; border-right: 1px solid; }

  /* ---------- SECTION SHELL ---------- */
  .section{ padding: var(--section-y) 0; position: relative; }
  .section--alt{ background: var(--bg-2); }
  .section-head{
    display: grid; grid-template-columns: 280px 1fr; gap: 80px;
    margin-bottom: 64px;
    align-items: start;
  }
  .section-head .label{
    font-size: 12px; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--ink-3);
    font-weight: 500;
  }
  .section-head .lead{
    font-size: 18px; line-height: 1.55; color: var(--ink-2);
    max-width: 720px; margin-top: 22px;
    text-wrap: pretty;
  }
  .section-head h2{ text-wrap: balance; }

  /* ---------- METHOD (hexagram-diagram) ---------- */
  .method-grid{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 80px; align-items: center;
  }
  .method-text p + p{ margin-top: 18px; }
  .method-text strong{ color: var(--ink); font-weight: 600; }
  .stat-row{
    display: flex; gap: 48px; margin-top: 48px;
    padding-top: 32px; border-top: 1px solid var(--line);
  }
  .stat .num{
    font-family: 'Golos Text'; font-size: 40px;
    font-weight: 600; line-height: 1; letter-spacing: -0.02em;
    color: var(--ink);
  }
  .stat .lbl{
    font-size: 13px; color: var(--ink-3); margin-top: 8px;
    line-height: 1.4;
  }

  .hex-board{
    position: relative;
    padding: 56px 40px 56px;
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 8px;
  }
  .hex-board::before, .hex-board::after{
    content: ''; position: absolute; width: 16px; height: 16px;
    border: 1px solid var(--ink-3);
  }
  .hex-board::before{ top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
  .hex-board::after{ bottom: -1px; right: -1px; border-left: 0; border-top: 0; }
  .hex-rows{
    display: flex; flex-direction: column-reverse;
    gap: 16px;
    max-width: 100%;
  }
  .hex-row{
    display: grid;
    grid-template-columns: minmax(100px, 1fr) minmax(140px, 240px) minmax(100px, 1fr);
    gap: 20px; align-items: center;
  }
  .hex-line{
    height: 14px; position: relative;
  }
  .hex-line.solid{ background: var(--ink); }
  .hex-line.broken{
    background: linear-gradient(to right, var(--ink) 0%, var(--ink) 44%, transparent 44%, transparent 56%, var(--ink) 56%, var(--ink) 100%);
  }
  .hex-line.accent.solid{ background: var(--teal); }
  .hex-line.accent.broken{
    background: linear-gradient(to right, var(--teal) 0%, var(--teal) 44%, transparent 44%, transparent 56%, var(--teal) 56%, var(--teal) 100%);
  }
  .hex-label{
    font-size: 13.5px;
    color: var(--ink-2);
    display: flex; align-items: center;
    gap: 12px;
    min-width: 0;
  }
  .hex-label.left{ justify-content: flex-end; text-align: right; }
  .hex-label .num{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 14px;
    color: var(--ink-3); letter-spacing: 0.02em;
    font-style: italic;
  }
  .hex-tag{
    position: absolute;
    font-size: 11px; letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-3); font-weight: 500;
    padding: 6px 14px;
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 2px;
  }
  .hex-tag.external{ top: -13px; left: 50%; transform: translateX(-50%); }
  .hex-tag.internal{ bottom: -13px; left: 50%; transform: translateX(-50%); }
  .hex-divider-row{
    display: grid;
    grid-template-columns: minmax(100px, 1fr) minmax(140px, 240px) minmax(100px, 1fr);
    gap: 20px; align-items: center;
    margin: 2px 0;
  }
  .hex-divider-row .hex-divider{
    height: 1px; background: var(--line-2);
  }

  /* ---------- PROCESS ---------- */
  .steps{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 32px;
    margin-bottom: 56px;
  }
  .step{
    background: var(--bg);
    border: 1px solid var(--line);
    padding: 36px 32px;
    position: relative;
    transition: border-color .2s, transform .2s;
  }
  .step:hover{
    border-color: var(--ink);
    transform: translateY(-2px);
  }
  .step-top{
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 32px;
  }
  .step-num{
    font-family: 'Golos Text'; font-size: 14px;
    color: var(--ink-3); letter-spacing: 0.1em;
  }
  .step-hex{
    display: flex; flex-direction: column; gap: 4px;
    width: 44px;
  }
  .step-hex .l{ height: 5px; background: var(--ink); }
  .step-hex .l.b{
    background: linear-gradient(to right, var(--ink) 0%, var(--ink) 40%, transparent 40%, transparent 60%, var(--ink) 60%, var(--ink) 100%);
  }
  .step-hex.t .l{ background: var(--teal); }
  .step-hex.t .l.b{
    background: linear-gradient(to right, var(--teal) 0%, var(--teal) 40%, transparent 40%, transparent 60%, var(--teal) 60%, var(--teal) 100%);
  }
  .step h3{ margin-bottom: 14px; }
  .step p{ font-size: 15px; line-height: 1.5; color: var(--ink-2); }
  .process-cta{ display: flex; justify-content: center; }

  /* ---------- AUDIENCE ---------- */
  .audience-grid{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 24px;
    margin-bottom: 56px;
  }
  .aud-card{
    padding: 40px 32px;
    background: var(--bg);
    border: 1px solid var(--line);
    display: flex; flex-direction: column;
    transition: border-color .2s, transform .2s;
  }
  .aud-card:hover{ border-color: var(--deep); transform: translateY(-2px); }
  .aud-hex{
    display: flex; flex-direction: column; gap: 4px;
    width: 44px; margin-bottom: 28px;
  }
  .aud-hex .l{ height: 4px; background: var(--deep); border-radius: 1px; }
  .aud-hex .l.b{
    background: linear-gradient(to right, var(--deep) 0%, var(--deep) 42%, transparent 42%, transparent 58%, var(--deep) 58%, var(--deep) 100%);
  }
  .aud-num{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 15px; font-style: italic;
    color: var(--ink-3); letter-spacing: 0.02em;
    margin-bottom: 14px;
  }
  .aud-title{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 26px; font-weight: 500; letter-spacing: -0.005em;
    margin-bottom: 24px;
    line-height: 1.15;
    color: var(--ink);
  }
  .aud-sub{
    font-size: 13.5px; letter-spacing: 0.04em;
    color: var(--red);
    font-weight: 500; margin-bottom: 14px;
  }
  .aud-list{
    list-style: none; padding: 0; margin: 0;
    font-size: 15px; color: var(--ink-2); line-height: 1.5;
  }
  .aud-list li{
    padding: 10px 0;
    display: flex; gap: 14px; align-items: flex-start;
  }
  .aud-list li::before{
    content: ''; flex-shrink: 0; margin-top: 8px;
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--red);
  }
  .audience-cta{ display: flex; justify-content: center; }

  /* ---------- METHOD 2 ---------- */
  .m2-grid{
    display: grid; grid-template-columns: 1fr 1.1fr;
    gap: 80px; align-items: center;
  }
  .m2-grid > *, .method-grid > *, .hero-grid > *{ min-width: 0; }
  .m2-text .eyebrow{ display: inline-block; margin-bottom: 20px; }
  .m2-text h2{ margin-bottom: 24px; text-wrap: balance; }
  .m2-text p{ font-size: 17px; line-height: 1.6; margin-bottom: 16px; max-width: 540px; }
  .m2-warn{
    margin-top: 28px;
    padding: 20px 24px;
    background: var(--bg);
    border-left: 3px solid var(--red);
    font-size: 14px; line-height: 1.5;
    color: var(--ink-2);
  }
  .m2-warn strong{ color: var(--ink); font-weight: 600; }

  .m2-canvas-title{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 28px; font-weight: 500;
    color: var(--ink); letter-spacing: -0.01em;
    margin-bottom: 22px;
    line-height: 1.2;
  }
  .canvas{
    background: transparent;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  .canvas-cell{
    padding: 22px 22px 24px;
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 4px;
    display: flex; flex-direction: column;
    gap: 14px;
    transition: border-color .2s, transform .2s;
    position: relative;
  }
  .canvas-cell:hover{ border-color: var(--deep); transform: translateY(-1px); }
  .canvas-cell.active{ border-color: var(--deep); box-shadow: inset 0 0 0 1px var(--deep); }
  .canvas-cell .cn{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 18px; font-style: italic;
    color: var(--red); letter-spacing: 0.01em;
    line-height: 1;
  }
  .canvas-cell .ct{
    font-family: 'Golos Text', 'Inter', sans-serif;
    font-size: 15.5px; font-weight: 600;
    color: var(--ink); letter-spacing: -0.005em;
    line-height: 1.3;
    text-transform: none;
  }
  .canvas-cell .clines{
    display: flex; flex-direction: column; gap: 6px;
    margin-top: auto;
  }
  .canvas-cell .clines span{
    display: block; height: 2px;
    background: var(--line-2); border-radius: 1px;
    opacity: 0.7;
  }
  .canvas-cell .clines span:nth-child(1){ width: 100%; }
  .canvas-cell .clines span:nth-child(2){ width: 78%; }
  .canvas-cell .clines span:nth-child(3){ width: 88%; }

  /* ---------- PRICING ---------- */
  .pricing-wrap{
    display: flex; justify-content: center;
  }
  .price-card{
    width: 100%; max-width: 620px;
    background: var(--bg);
    border: 1px solid var(--line);
    padding: 48px 56px 40px;
    position: relative;
    text-align: center;
  }
  .price-eyebrow{
    font-size: 12px; letter-spacing: 0.2em;
    text-transform: uppercase; color: var(--red);
    font-weight: 600;
    margin-bottom: 18px;
  }
  .price-card h3{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 36px; font-weight: 500;
    letter-spacing: -0.01em;
    line-height: 1.15;
    margin: 0 auto 36px;
    max-width: 460px;
    text-wrap: balance;
    color: var(--ink);
  }
  .price-amount-wrap{ margin: 0 0 36px; }
  .price-amount{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-weight: 500;
    font-size: clamp(64px, 7vw, 84px);
    line-height: 1;
    letter-spacing: -0.025em;
    color: var(--ink);
    display: inline-flex; align-items: baseline; gap: 14px;
  }
  .price-amount small{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 28px; color: var(--ink-3); font-weight: 500;
    letter-spacing: 0;
  }
  .price-note{
    font-size: 13px; color: var(--ink-3);
    margin-top: 14px;
    letter-spacing: 0.02em;
  }
  .price-list{
    list-style: none; padding: 0; margin: 0 0 36px;
    border-top: 1px solid var(--line);
    text-align: left;
  }
  .price-list li{
    padding: 16px 0;
    border-bottom: 1px solid var(--line);
    display: flex; gap: 24px; align-items: baseline;
    font-size: 15px; color: var(--ink-2);
    justify-content: space-between;
  }
  .price-list li .k{ color: var(--ink-3); }
  .price-list li .v{ color: var(--ink); font-weight: 500; text-align: right; }
  .price-cta{
    display: flex; width: 100%;
    background: var(--lav); color: #fff;
    height: 60px;
    border: 0; border-radius: var(--rad);
    font-family: 'Inter', sans-serif; font-size: 16px; font-weight: 500;
    cursor: pointer; transition: all .18s ease;
    align-items: center; justify-content: center; gap: 10px;
    text-decoration: none;
  }
  .price-cta:hover{
    background: var(--deep);
    transform: translateY(-1px);
    box-shadow: 0 12px 28px -14px rgba(18,65,135,0.6);
  }

  /* ---------- CONTACT ---------- */
  .contact-section{
    background: #C6E0E4;
    padding: var(--section-y) 0;
  }
  .contact-grid{
    display: grid; grid-template-columns: 1fr 1.1fr;
    gap: 24px; align-items: stretch;
  }
  .contact-grid > *{ min-width: 0; }
  .contact-card{
    background: var(--bg);
    padding: 48px 48px 44px;
    border-radius: 6px;
    display: flex; flex-direction: column;
  }
  .contact-eyebrow{
    font-size: 12px; letter-spacing: 0.2em;
    text-transform: uppercase; color: var(--red);
    font-weight: 600; margin-bottom: 24px;
  }
  .contact-title{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: clamp(36px, 4vw, 52px);
    font-weight: 500; letter-spacing: -0.015em;
    line-height: 1.05;
    color: var(--ink);
    margin: 0 0 24px;
    text-wrap: balance;
  }
  .contact-lead{
    font-size: 16px; line-height: 1.55;
    color: var(--ink-2);
    margin: 0 0 32px;
    max-width: 440px;
  }
  .contact-meta{ margin-top: auto; }
  .contact-meta .row{
    padding: 20px 0;
    border-top: 1px solid var(--line);
  }
  .contact-meta .row:last-child{ border-bottom: 1px solid var(--line); }
  .contact-meta .row .h{
    font-family: 'EB Garamond', 'PT Serif', Georgia, serif;
    font-size: 20px; font-weight: 500; color: var(--ink);
    margin-bottom: 4px; line-height: 1.2;
  }
  .contact-meta .row .d{
    font-size: 14px; color: var(--ink-3); line-height: 1.5;
  }
  .contact-form{
    background: rgba(255,255,255,0.85);
    padding: 40px 40px 36px;
    border-radius: 6px;
    display: flex; flex-direction: column; gap: 20px;
  }
  .field label{
    display: block;
    font-size: 13.5px; color: var(--ink-2);
    font-weight: 500; margin-bottom: 8px;
  }
  .field input, .field textarea{
    width: 100%;
    background: #fff;
    border: 1px solid rgba(18,65,135,0.18);
    border-radius: var(--rad);
    padding: 14px 16px;
    font-family: 'Inter', sans-serif; font-size: 15px;
    color: var(--ink);
    transition: border-color .15s, box-shadow .15s;
    outline: none;
  }
  .field textarea{ min-height: 110px; resize: vertical; }
  .field input:focus, .field textarea:focus{
    border-color: var(--deep);
    box-shadow: 0 0 0 3px rgba(18,65,135,0.08);
  }
  .field input::placeholder, .field textarea::placeholder{ color: #9FA9B5; }
  .form-submit{
    width: 100%; height: 56px;
    background: var(--deep); color: #fff;
    border: 0; border-radius: var(--rad);
    font-family: 'Inter', sans-serif; font-size: 15px; font-weight: 500;
    cursor: pointer; transition: all .18s;
    margin-top: 4px;
  }
  .form-submit:hover{
    background: #0E3573;
    box-shadow: 0 12px 28px -14px rgba(18,65,135,0.55);
  }
  .form-submit:disabled{ opacity: 0.7; cursor: progress; }

  /* ---------- FOOTER ---------- */
  .site-footer{
    background: var(--deep); color: rgba(255,255,255,0.78);
    padding: 80px 0 32px;
  }
  .site-footer a{ color: rgba(255,255,255,0.78); transition: color .15s; }
  .site-footer a:hover{ color: #fff; }
  .footer-grid{
    display: grid;
    grid-template-columns: 2.2fr 1fr 1.4fr 1fr;
    gap: 48px;
    padding-bottom: 56px;
    border-bottom: 1px solid rgba(255,255,255,0.16);
  }
  .footer-brand .logo{ color: #fff; margin-bottom: 16px; }
  .footer-tag{ font-size: 14px; line-height: 1.5; color: rgba(255,255,255,0.6); max-width: 320px; }
  .footer-col h4{
    color: #fff; font-size: 13px; letter-spacing: 0.12em;
    text-transform: uppercase; font-weight: 500; margin-bottom: 20px;
  }
  .footer-list{
    list-style: none; padding: 0; margin: 0;
    display: flex; flex-direction: column; gap: 12px;
    font-size: 14px;
  }
  .footer-bottom{
    padding-top: 28px;
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 20px;
    font-size: 13px; color: rgba(255,255,255,0.5);
  }
  .footer-socials{ display: flex; gap: 12px; }
  .soc{
    width: 40px; height: 40px;
    border: 1px solid rgba(255,255,255,0.22); border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    transition: all .15s; color: rgba(255,255,255,0.85);
  }
  .soc:hover{ border-color: #fff; color: #fff; background: rgba(255,255,255,0.06); }

  /* ---------- COOKIE ---------- */
  .cookie{
    position: fixed; left: 24px; right: 24px; bottom: 24px;
    z-index: 200; max-width: 760px; margin: 0 auto;
    background: rgba(32,32,32,0.92);
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    color: #E9E9E5;
    padding: 22px 24px 22px 28px;
    border-radius: 6px;
    display: flex; gap: 28px; align-items: center;
    box-shadow: 0 20px 60px -16px rgba(0,0,0,0.4);
    transform: translateY(140%);
    transition: transform .35s cubic-bezier(.2,.7,.2,1);
  }
  .cookie.visible{ transform: translateY(0); }
  .cookie p{ font-size: 13.5px; color: #C9C9C5; line-height: 1.5; flex: 1; margin: 0; }
  .cookie-close{
    position: absolute; top: 8px; right: 8px;
    background: transparent; border: 0; color: #8C8C88;
    cursor: pointer; padding: 6px;
  }
  .cookie-close:hover{ color: #fff; }
  .cookie .btn{
    height: 42px; background: #fff; color: #202020;
    flex-shrink: 0;
    padding: 0 22px; font-size: 14px;
  }
  .cookie .btn:hover{ background: var(--bg); }

  /* ---------- RESPONSIVE ---------- */
  @media (max-width: 1024px){
    .hero-grid, .method-grid, .m2-grid{ gap: 48px; }
    .section-head{ grid-template-columns: 220px 1fr; gap: 48px; margin-bottom: 48px; }
    .audience-grid{ grid-template-columns: 1fr 1fr; }
    .footer-grid{ grid-template-columns: 1.4fr 1fr 1.4fr 1fr; gap: 32px; }
    .contact-grid{ grid-template-columns: 1fr; }
    .contact-card{ padding: 36px; }
  }
  @media (max-width: 760px){
    .nav{ display: none; }
    .header-login{ display: none; }
    .burger{
      display: flex; flex-direction: column; gap: 4px;
      background: transparent; border: 0; padding: 8px; cursor: pointer;
      position: relative; z-index: 110;
    }
    .burger span{ display: block; width: 22px; height: 1.5px; background: var(--ink); transition: transform .25s ease, opacity .15s ease; transform-origin: center; }
    .hero{ padding-top: 110px; }
    .hero-grid, .method-grid, .m2-grid{ grid-template-columns: 1fr; }
    .hero-right{ aspect-ratio: 1/1; max-width: 420px; margin: 0 auto; }
    .section-head{ grid-template-columns: 1fr; gap: 16px; margin-bottom: 40px; }
    .steps, .audience-grid{ grid-template-columns: 1fr; }
    .canvas{ grid-template-columns: 1fr 1fr; }
    .price-card{ padding: 36px 24px; }
    .price-amount{ font-size: 56px; }
    .price-amount small{ font-size: 22px; }
    .price-list li{ flex-direction: column; gap: 2px; align-items: flex-start; }
    .price-list li .v{ text-align: left; }
    .hero-cta{ width: 100%; }
    .hero-cta .pdf-buttons{ width: 100%; }
    .pdf-btn{ flex: 1; min-width: 0; }
    .footer-grid{ grid-template-columns: 1fr 1fr; gap: 32px; }
    .footer-brand{ grid-column: 1 / -1; }
    .footer-bottom{ flex-direction: column; align-items: flex-start; }
    .stat-row{ flex-direction: column; gap: 24px; }
    .cookie{ flex-direction: column; align-items: stretch; gap: 16px; }
    .contact-card, .contact-form{ padding: 32px 24px; }
    .hex-row, .hex-divider-row{ grid-template-columns: 1fr 60% 1fr; gap: 10px; }
    .hex-label{ font-size: 12px; }
  }
      `}</style>
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

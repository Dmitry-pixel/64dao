'use client'

import Link from 'next/link'
import { useState } from 'react'

/**
 * SiteNav — липкая шапка сайта.
 * 'use client' — требование Next.js App Router для компонентов с браузерными
 * событиями. Плавная прокрутка к якорям реализована через CSS (globals.css:
 * scroll-behavior: smooth + scroll-padding-top), поэтому обычные <a href="#id">
 * работают корректно без JavaScript.
 *
 * Адаптив: ниже 880px навигация и CTA скрываются за бургер-кнопкой.
 * Брейкпоинт и стили — через <style jsx>, так как остальная часть компонента
 * использует inline style={{}} (медиа-запросы в inline-стилях не работают).
 */
export default function SiteNav() {
  const [open, setOpen] = useState(false)

  return (
    <header
      className="site-nav"
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
        className="site-nav__bar"
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
        {/* Логотип */}
        <a href="#top" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
          <img src="/assets/logo.svg" alt="64 ДАО" style={{ height: 52, width: 'auto', display: 'block' }} />
        </a>

        {/* Навигация (desktop) */}
        <nav
          className="site-nav__links"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 28,
            fontSize: 12,
            textTransform: 'uppercase',
            letterSpacing: '0.18em',
          }}
        >
          <a href="#how"     style={{ color: '#1f3a52', textDecoration: 'none' }}>Как это работает</a>
          <a href="#report"  style={{ color: '#1f3a52', textDecoration: 'none' }}>Что в отчёте</a>
          <a href="#price"   style={{ color: '#1f3a52', textDecoration: 'none' }}>Стоимость</a>
          <Link href="/about" style={{ color: '#1f3a52', textDecoration: 'none' }}>О нас</Link>
          <a href="#contact" style={{ color: '#1f3a52', textDecoration: 'none' }}>Контакты</a>
          <Link href="/login" style={{ color: '#1f3a52', textDecoration: 'none' }}>Вход / Регистрация</Link>
        </nav>

        {/* CTA (desktop) */}
        <a href="/login"
          className="site-nav__cta"
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
        </a>

        {/* Бургер-кнопка (mobile) */}
        <button
          type="button"
          className="site-nav__burger"
          aria-label={open ? 'Закрыть меню' : 'Открыть меню'}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          style={{
            display: 'none',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: 5,
            width: 32,
            height: 32,
            padding: 0,
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          <span className="site-nav__burger-bar" style={{ background: '#1f3a52' }} />
          <span className="site-nav__burger-bar" style={{ background: '#1f3a52' }} />
          <span className="site-nav__burger-bar" style={{ background: '#1f3a52' }} />
        </button>
      </div>

      {/* Мобильное выпадающее меню */}
      <nav
        className="site-nav__mobile-panel"
        style={{
          display: open ? 'flex' : 'none',
          flexDirection: 'column',
          gap: 4,
          padding: '8px 20px 20px',
          fontSize: 13,
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
        }}
      >
        <a href="#how"     onClick={() => setOpen(false)} style={{ color: '#1f3a52', textDecoration: 'none', padding: '10px 0' }}>Как это работает</a>
        <a href="#report"  onClick={() => setOpen(false)} style={{ color: '#1f3a52', textDecoration: 'none', padding: '10px 0' }}>Что в отчёте</a>
        <a href="#price"   onClick={() => setOpen(false)} style={{ color: '#1f3a52', textDecoration: 'none', padding: '10px 0' }}>Стоимость</a>
        <Link href="/about" onClick={() => setOpen(false)} style={{ color: '#1f3a52', textDecoration: 'none', padding: '10px 0' }}>О нас</Link>
        <a href="#contact" onClick={() => setOpen(false)} style={{ color: '#1f3a52', textDecoration: 'none', padding: '10px 0' }}>Контакты</a>
        <Link href="/login" onClick={() => setOpen(false)} style={{ color: '#1f3a52', textDecoration: 'none', padding: '10px 0' }}>Вход / Регистрация</Link>
        <a href="/login"
          onClick={() => setOpen(false)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 2,
            background: 'var(--accent)',
            padding: '12px 20px',
            marginTop: 8,
            fontSize: 13,
            fontWeight: 500,
            color: 'var(--accent-foreground)',
            textDecoration: 'none',
          }}
        >
          Пройти диагностику
        </a>
      </nav>

      <style jsx>{`
        @media (max-width: 880px) {
          .site-nav__bar {
            padding: 12px 20px !important;
          }
          .site-nav__links {
            display: none !important;
          }
          .site-nav__cta {
            display: none !important;
          }
          .site-nav__burger {
            display: flex !important;
          }
        }
        @media (min-width: 881px) {
          .site-nav__mobile-panel {
            display: none !important;
          }
        }
        .site-nav__burger-bar {
          display: block;
          width: 100%;
          height: 2px;
          border-radius: 1px;
        }
      `}</style>
    </header>
  )
}

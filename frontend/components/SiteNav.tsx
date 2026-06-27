'use client'

import Link from 'next/link'

/**
 * SiteNav — липкая шапка сайта.
 * 'use client' — требование Next.js App Router для компонентов с браузерными
 * событиями. Плавная прокрутка к якорям реализована через CSS (globals.css:
 * scroll-behavior: smooth + scroll-padding-top), поэтому обычные <a href="#id">
 * работают корректно без JavaScript.
 */
export default function SiteNav() {
  return (
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
        {/* Логотип */}
        <a href="#top" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
          <img src="/assets/logo.svg" alt="64 ДАО" style={{ height: 52, width: 'auto', display: 'block' }} />
        </a>

        {/* Навигация */}
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
          <a href="#how"     style={{ color: '#1f3a52', textDecoration: 'none' }}>Как это работает</a>
          <a href="#report"  style={{ color: '#1f3a52', textDecoration: 'none' }}>Что в отчёте</a>
          <a href="#price"   style={{ color: '#1f3a52', textDecoration: 'none' }}>Стоимость</a>
          {/* next/link для маршрутов App Router */}
          <Link href="/about" style={{ color: '#1f3a52', textDecoration: 'none' }}>О нас</Link>
          <a href="#contact" style={{ color: '#1f3a52', textDecoration: 'none' }}>Контакты</a>
          <Link href="/login" style={{ color: '#1f3a52', textDecoration: 'none' }}>Вход / Регистрация</Link>
        </nav>

        {/* CTA */}
        <a href="/login"
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
      </div>
    </header>
  )
}

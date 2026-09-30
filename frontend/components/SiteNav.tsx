'use client'

import Link from 'next/link'
import { useState } from 'react'
import SampleReportModal from '@/components/SampleReportModal'

/**
 * SiteNav: липкая шапка сайта, вариант B (тёмно-синяя).
 * 'use client' нужен для бургер-меню и модалки «Методика 64DAO».
 *
 * Ссылки на разделы главной даны как /#id: шапка стоит и на других страницах
 * (/methods, /help/...), и голый #id там никуда не ведёт.
 *
 * Адаптив: ниже 1080px навигация и кнопки уходят в бургер.
 */
const NAV = [
  { href: '/#how', label: 'Как это работает' },
  { href: '/#report', label: 'Что в отчёте' },
  { href: '/#price', label: 'Стоимость' },
  { href: '/about', label: 'О нас' },
  { href: '/#contact', label: 'Контакты' },
]

const INK = '#F8F4EC'

export default function SiteNav() {
  const [open, setOpen] = useState(false)
  // Методика отдаётся через ту же форму сбора контактов, что и примеры
  // отчётов: отдельная страница-скачивание дублировала бы и форму, и лид.
  const [methodOpen, setMethodOpen] = useState(false)

  return (
    <>
      <header className="site-nav">
        <div className="site-nav__bar">
          <Link href="/" className="site-nav__logo" aria-label="64 ДАО, на главную">
            <img src="/assets/logo.svg" alt="64 ДАО" />
          </Link>

          <nav className="site-nav__links" aria-label="Разделы">
            {NAV.map((i) => (
              <Link key={i.href} href={i.href}>{i.label}</Link>
            ))}
          </nav>

          <div className="site-nav__cta-group">
            <button type="button" className="site-nav__method" onClick={() => setMethodOpen(true)}>
              Методика 64DAO
            </button>
            <Link href="/login" className="site-nav__login">Войти</Link>
            <a href="/login" className="site-nav__cta">Пройти диагностику</a>
          </div>

          <button
            type="button"
            className="site-nav__burger"
            aria-label={open ? 'Закрыть меню' : 'Открыть меню'}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <span /><span /><span />
          </button>
        </div>

        {open && (
          <nav className="site-nav__mobile-panel" aria-label="Меню">
            {NAV.map((i) => (
              <Link key={i.href} href={i.href} onClick={() => setOpen(false)}>{i.label}</Link>
            ))}
            <Link href="/login" onClick={() => setOpen(false)}>Вход / Регистрация</Link>
            <button type="button" className="site-nav__method" onClick={() => { setOpen(false); setMethodOpen(true) }}>
              Методика 64DAO
            </button>
            <a href="/login" className="site-nav__cta" onClick={() => setOpen(false)}>Пройти диагностику</a>
          </nav>
        )}

        <style jsx>{`
          .site-nav {
            position: sticky;
            top: 0;
            z-index: 40;
            background: #1E2A44;
            border-bottom: 1px solid rgba(248, 244, 236, 0.12);
            font-family: 'Golos Text', system-ui, sans-serif;
          }
          .site-nav__bar {
            max-width: 1200px;
            margin: 0 auto;
            height: 80px;
            padding: 0 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
          }
          .site-nav :global(.site-nav__logo) { display: flex; align-items: center; }
          .site-nav :global(.site-nav__logo img) { height: 52px; width: auto; display: block; }
          .site-nav__links { display: flex; align-items: center; gap: 28px; font-size: 15px; }
          .site-nav__links :global(a),
          .site-nav__mobile-panel :global(a) { color: ${INK}; text-decoration: none; }
          .site-nav__links :global(a:hover) { color: #5B9EA6; }
          .site-nav__cta-group { display: flex; align-items: center; gap: 16px; }
          .site-nav__method {
            background: transparent;
            border: 1px solid rgba(248, 244, 236, 0.35);
            border-radius: 999px;
            padding: 10px 16px;
            font: inherit;
            font-size: 14px;
            color: ${INK};
            cursor: pointer;
            white-space: nowrap;
          }
          .site-nav__method:hover { border-color: ${INK}; }
          .site-nav :global(.site-nav__login) { font-size: 15px; color: ${INK}; text-decoration: none; white-space: nowrap; }
          .site-nav :global(.site-nav__cta) {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: #C0392B;
            color: #FFFFFF;
            font-size: 15px;
            font-weight: 600;
            padding: 12px 20px;
            border-radius: 999px;
            text-decoration: none;
            white-space: nowrap;
          }
          .site-nav :global(.site-nav__cta:hover) { background: #A93226; }
          .site-nav__burger {
            display: none;
            flex-direction: column;
            justify-content: center;
            gap: 5px;
            width: 44px;
            height: 44px;
            padding: 10px;
            background: transparent;
            border: none;
            cursor: pointer;
          }
          .site-nav__burger span { display: block; height: 2px; border-radius: 1px; background: ${INK}; }
          .site-nav__mobile-panel {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 8px 20px 24px;
            font-size: 16px;
          }
          .site-nav__mobile-panel :global(a) { padding: 12px 0; }
          .site-nav__mobile-panel .site-nav__method { margin-top: 8px; padding: 14px 20px; }
          .site-nav__mobile-panel :global(.site-nav__cta) { margin-top: 8px; padding: 14px 20px; }
          @media (max-width: 1080px) {
            .site-nav__bar { padding: 0 20px; height: 68px; }
            .site-nav :global(.site-nav__logo img) { height: 44px; }
            .site-nav__links,
            .site-nav__cta-group { display: none; }
            .site-nav__burger { display: flex; }
          }
        `}</style>
      </header>

      {/* Модалка вынесена из <header>: sticky-шапка не должна быть
          containing block для position:fixed оверлея. */}
      <SampleReportModal open={methodOpen} onClose={() => setMethodOpen(false)} method="methodology" />
    </>
  )
}

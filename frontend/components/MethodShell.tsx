import SiteFooter from '@/components/SiteFooter'

/**
 * Обёртка страниц раздела /method: шапка, контейнер, подвал.
 *
 * Server Component — никаких хуков и никакого 'use client'. Это обязательно:
 * контент раздела должен целиком попадать в SSR-HTML, иначе краулеры и
 * цитирующие ИИ-агенты увидят пустую страницу.
 *
 * Стили — классами .method-* из globals.css. styled-jsx в серверных
 * компонентах не работает, инлайн-стили не умеют @media.
 */
export default function MethodShell({ children }: { children: React.ReactNode }) {
  const year = new Date().getFullYear()

  return (
    <div className="landing-scope method-root">
      <header className="method-header">
        <div className="method-header-inner">
          <a href="/" className="method-logo" aria-label="64 ДАО — на главную">
            <img src="/assets/logo.svg" alt="64 ДАО" />
          </a>
          <nav className="method-topnav">
            <a href="/method">Методика</a>
            <a href="/about">О проекте</a>
            <a href="/login" className="method-topcta">Пройти диагностику</a>
          </nav>
        </div>
      </header>

      <main className="method-main">{children}</main>

      <SiteFooter year={year} />
    </div>
  )
}

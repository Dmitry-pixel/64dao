import Link from 'next/link'

interface AboutShellProps {
  /** HTML-контент из GET /api/documents/about */
  htmlContent: string
}

/**
 * AboutShell — визуальная обёртка страницы «О нас».
 * Server Component: не содержит хуков или обработчиков событий.
 * Контент (HTML) приходит как проп из app/about/page.tsx.
 */
export default function AboutShell({ htmlContent }: AboutShellProps) {
  return (
    <div
      className="landing-scope"
      style={{
        fontFamily: 'Inter, sans-serif',
        color: 'var(--foreground)',
        background: 'var(--background)',
        minHeight: '100vh',
      }}
    >
      {/* ── Шапка ── */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          background: 'var(--brand-teal)',
          borderBottom: '1px solid rgba(255,255,255,0.25)',
        }}
      >
        <div
          style={{
            maxWidth: 920,
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 24,
            padding: '12px 40px',
          }}
        >
          <Link href="/" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
            <img src="/assets/logo.svg" alt="64 ДАО" style={{ height: 48, width: 'auto', display: 'block' }} />
          </Link>
          <Link
            href="/"
            style={{
              fontSize: 12,
              textTransform: 'uppercase',
              letterSpacing: '0.16em',
              color: '#1f3a52',
              textDecoration: 'none',
            }}
          >
            ← На главную
          </Link>
        </div>
      </header>

      {/* ── Заголовок ── */}
      <div style={{ maxWidth: 880, margin: '0 auto', padding: '64px 40px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <span style={{ display: 'inline-block', width: 32, height: 2, background: 'var(--accent)' }} />
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: 2,
              color: '#888888',
            }}
          >
            О проекте 64 ДАО
          </span>
        </div>
        <h1
          style={{
            margin: 0,
            fontFamily: "'Golos Text',sans-serif",
            fontWeight: 700,
            fontSize: 'clamp(34px,5vw,52px)',
            lineHeight: 1.1,
            color: 'var(--foreground)',
          }}
        >
          О нас
        </h1>
      </div>

      {/* ── Карточка с контентом ── */}
      <div style={{ maxWidth: 880, margin: '0 auto 80px', padding: '0 40px' }}>
        <div
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            boxShadow: '0 30px 80px -55px rgba(20,30,60,0.4)',
            padding: 'clamp(28px,5vw,56px)',
          }}
        >
          {htmlContent ? (
            <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
          ) : (
            /* Заглушка до получения контента из API */
            <div style={{ minHeight: 240, color: 'var(--muted-foreground)', fontSize: 14 }}>
              Контент загружается…
            </div>
          )}
        </div>
      </div>

      {/* ── Подвал ── */}
      <footer style={{ background: 'var(--brand-teal)' }}>
        <div
          style={{
            maxWidth: 920,
            margin: '0 auto',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 24,
            padding: '32px 40px',
          }}
        >
          <Link href="/" style={{ display: 'inline-flex', textDecoration: 'none' }}>
            <img src="/assets/logo.svg" alt="64 ДАО" style={{ height: 48, width: 'auto', display: 'block' }} />
          </Link>
          <nav style={{ display: 'flex', flexWrap: 'wrap', gap: 20, fontSize: 13 }}>
            <Link href="/documents/privacy-policy"        style={{ color: 'rgba(255,255,255,0.85)', textDecoration: 'none' }}>Политика обработки ПДн</Link>
            <Link href="/documents/user-agreement"        style={{ color: 'rgba(255,255,255,0.85)', textDecoration: 'none' }}>Пользовательское соглашение</Link>
            <Link href="/documents/personal-data-consent" style={{ color: 'rgba(255,255,255,0.85)', textDecoration: 'none' }}>Согласие на обработку ПДн</Link>
          </nav>
        </div>
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.2)' }}>
          <div
            style={{
              maxWidth: 920,
              margin: '0 auto',
              padding: '18px 40px',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 16,
            }}
          >
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>
              © {new Date().getFullYear()} 64 ДАО — все права защищены
            </span>
            <div style={{ display: 'flex', gap: 10 }}>
              <a href="https://t.me/" target="_blank" rel="noreferrer" aria-label="Telegram"
                style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 36, width: 36, borderRadius: '9999px', background: 'rgba(255,255,255,0.18)', color: '#1f3a52', textDecoration: 'none' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71l-4.07-3.04-1.95 1.9c-.21.21-.39.4-.78.4z" />
                </svg>
              </a>
              <a href="https://vk.com/" target="_blank" rel="noreferrer" aria-label="ВКонтакте"
                style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 36, width: 36, borderRadius: '9999px', background: 'rgba(255,255,255,0.18)', color: '#1f3a52', textDecoration: 'none', fontFamily: 'Inter,sans-serif', fontWeight: 800, fontSize: 13, letterSpacing: '-0.02em' }}>
                VK
              </a>
              <a href="https://max.ru/" target="_blank" rel="noreferrer" aria-label="MAX"
                style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 36, width: 36, borderRadius: '9999px', background: 'rgba(255,255,255,0.18)', color: '#1f3a52', textDecoration: 'none', fontFamily: 'Inter,sans-serif', fontWeight: 800, fontSize: 10 }}>
                MAX
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

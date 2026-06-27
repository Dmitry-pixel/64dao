import Link from 'next/link'

/** Подвал главной страницы — Server Component. */
export default function SiteFooter({ year }: { year: number }) {
  return (
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
        {/* Логотип + соцсети */}
        <div>
          <a href="#top" style={{ display: 'inline-flex', textDecoration: 'none' }}>
            <img src="/assets/logo.svg" alt="64 ДАО" style={{ height: 64, width: 'auto', display: 'block' }} />
          </a>
          <p style={{ margin: '16px 0 0', maxWidth: 260, fontSize: 14, color: 'rgba(255,255,255,0.8)' }}>
            Стратегическая диагностика компании на основе «И-цзин».
          </p>
          <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
            <a href="https://t.me/" target="_blank" rel="noreferrer" aria-label="Telegram"
              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 40, width: 40, borderRadius: '9999px', background: 'rgba(255,255,255,0.18)', color: '#1f3a52', textDecoration: 'none' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71l-4.07-3.04-1.95 1.9c-.21.21-.39.4-.78.4z" />
              </svg>
            </a>
            <a href="https://vk.com/" target="_blank" rel="noreferrer" aria-label="ВКонтакте"
              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 40, width: 40, borderRadius: '9999px', background: 'rgba(255,255,255,0.18)', color: '#1f3a52', textDecoration: 'none', fontFamily: 'Inter,sans-serif', fontWeight: 800, fontSize: 14, letterSpacing: '-0.02em' }}>
              VK
            </a>
            <a href="https://max.ru/" target="_blank" rel="noreferrer" aria-label="MAX"
              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 40, width: 40, borderRadius: '9999px', background: 'rgba(255,255,255,0.18)', color: '#1f3a52', textDecoration: 'none', fontFamily: 'Inter,sans-serif', fontWeight: 800, fontSize: 11, letterSpacing: '-0.01em' }}>
              MAX
            </a>
          </div>
        </div>

        {/* Разделы */}
        <div>
          <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.7)' }}>Разделы</div>
          <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
            <li><a href="#how"     style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Как это работает</a></li>
            <li><a href="#report"  style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Что в отчёте</a></li>
            <li><a href="#price"   style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Стоимость</a></li>
            <li><Link href="/about" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>О нас</Link></li>
            <li><a href="#contact" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>Контакты</a></li>
          </ul>
        </div>

        {/* Правовая информация */}
        <div>
          <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.7)' }}>Правовая информация</div>
          <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
            <li>
              <Link href="/documents/privacy-policy" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>
                Политика обработки персональных данных
              </Link>
            </li>
            <li>
              <Link href="/documents/user-agreement" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>
                Пользовательское соглашение
              </Link>
            </li>
            <li>
              <Link href="/documents/personal-data-consent" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>
                Согласие на обработку персональных данных
              </Link>
            </li>
          </ul>
        </div>

        {/* Партнёры */}
        <div>
          <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.22em', color: 'rgba(255,255,255,0.7)' }}>Партнёры</div>
          <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
            <li>
              <a href="https://taoteam.ru" target="_blank" rel="noreferrer" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none' }}>
                taoteam.ru
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div style={{ borderTop: '1px solid rgba(255,255,255,0.2)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 40px', fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>
          © {year} 64 ДАО — все права защищены
        </div>
      </div>
    </footer>
  )
}

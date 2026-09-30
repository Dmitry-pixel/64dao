import Link from 'next/link'

/**
 * Подвал сайта, вариант B (тёмно-синий). Server Component.
 *
 * Стоит на главной, /methods, /method и /help, поэтому стили inline и не
 * зависят от landing-b.css. Адаптив без media-запросов: сетка auto-fit.
 * Адреса соцсетей редактируются в админке (/admin/social-links) и приходят
 * из /api/social-links.
 */
async function getSocialLinks() {
  const API = process.env.NEXT_PUBLIC_API_URL || ''
  try {
    const res = await fetch(`${API}/api/social-links`, { next: { revalidate: 60 } })
    if (res.ok) return await res.json()
  } catch {}
  return { telegram: 'https://t.me/64dao_blog', vk: 'https://vk.com/64dao', max: 'https://max.ru/64dao_max' }
}

const NAVY = '#1E2A44'
const INK = '#F8F4EC'
const DIM = '#B9C2CE'
const TEAL = '#5B9EA6'

const heading: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: TEAL,
}
const list: React.CSSProperties = {
  margin: '14px 0 0',
  padding: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  fontSize: 15,
  lineHeight: 1.4,
}
const link: React.CSSProperties = { color: INK, textDecoration: 'none' }
const socialBtn: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: 44,
  width: 44,
  borderRadius: '9999px',
  background: 'rgba(248,244,236,0.1)',
  color: INK,
  textDecoration: 'none',
  fontFamily: "Manrope, 'Golos Text', sans-serif",
  fontWeight: 800,
}

export default async function SiteFooter({ year }: { year: number }) {
  const social = await getSocialLinks()
  return (
    <footer style={{ background: NAVY, color: INK, fontFamily: "'Golos Text', system-ui, sans-serif" }}>
      <div
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: 40,
          padding: '64px clamp(20px, 4vw, 40px) 48px',
          boxSizing: 'border-box',
        }}
      >
        {/* Логотип + соцсети */}
        <div>
          <Link href="/" aria-label="64 ДАО, на главную" style={{ display: 'inline-flex', textDecoration: 'none' }}>
            <img src="/assets/logo.svg" alt="64 ДАО" style={{ height: 64, width: 'auto', display: 'block' }} />
          </Link>
          <p style={{ margin: '18px 0 0', maxWidth: 260, fontSize: 15, lineHeight: 1.5, color: DIM }}>
            Стратегическая диагностика компании на основе «И-цзин».
          </p>
          <div style={{ marginTop: 22, display: 'flex', gap: 10 }}>
            <a href={social.telegram} target="_blank" rel="noreferrer" aria-label="Telegram" style={socialBtn}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71l-4.07-3.04-1.95 1.9c-.21.21-.39.4-.78.4z" />
              </svg>
            </a>
            <a href={social.vk} target="_blank" rel="noreferrer" aria-label="ВКонтакте" style={{ ...socialBtn, fontSize: 14 }}>
              VK
            </a>
            <a href={social.max} target="_blank" rel="noreferrer" aria-label="MAX" style={{ ...socialBtn, fontSize: 11 }}>
              MAX
            </a>
          </div>
        </div>

        {/* Разделы */}
        <div>
          <div style={heading}>Разделы</div>
          <ul style={list}>
            <li><a href="/#how" style={link}>Как это работает</a></li>
            <li><a href="/#report" style={link}>Что в отчёте</a></li>
            <li><a href="/#price" style={link}>Стоимость</a></li>
            <li><Link href="/method" style={link}>Методика</Link></li>
            <li><Link href="/about" style={link}>О нас</Link></li>
            <li><a href="/#contact" style={link}>Контакты</a></li>
          </ul>
        </div>

        {/* Правовая информация */}
        <div>
          <div style={heading}>Правовая информация</div>
          <ul style={list}>
            <li><Link href="/documents/privacy-policy" style={link}>Политика обработки персональных данных</Link></li>
            <li><Link href="/documents/user-agreement" style={link}>Пользовательское соглашение</Link></li>
            <li><Link href="/documents/personal-data-consent" style={link}>Согласие на обработку персональных данных</Link></li>
          </ul>
        </div>

        {/* Партнёры */}
        <div>
          <div style={heading}>Партнёры</div>
          <ul style={list}>
            <li>
              <a href="https://taoteam.ru" target="_blank" rel="noreferrer" style={link}>
                taoteam.ru
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div style={{ borderTop: '1px solid rgba(248,244,236,0.12)' }}>
        <div
          style={{
            maxWidth: 1200,
            margin: '0 auto',
            padding: '22px clamp(20px, 4vw, 40px) 28px',
            boxSizing: 'border-box',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            gap: '6px 24px',
            fontSize: 13,
            color: DIM,
          }}
        >
          <span>© {year} 64 ДАО — все права защищены</span>
          <span>ИНН: 770402717024 · ОГРНИП: 326774600327837</span>
        </div>
      </div>
    </footer>
  )
}

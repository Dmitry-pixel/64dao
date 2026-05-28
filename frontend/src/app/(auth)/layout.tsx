'use client'
'use client'
// Лейаут для auth-страниц: без навигации и футера сайта
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#e8e4db',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'DM Sans', Arial, sans-serif",
      padding: '20px',
    }}>
      {/* Декоративные иероглифы */}
      <div style={{
        position: 'fixed', inset: 0, overflow: 'hidden',
        pointerEvents: 'none', opacity: 0.05,
      }}>
        {['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇'].map((s, i) => (
          <span key={i} style={{
            position: 'absolute', fontSize: '100px', color: '#1a2540',
            top: `${10 + i * 11}%`,
            left: i % 2 === 0 ? '3%' : 'auto',
            right: i % 2 !== 0 ? '3%' : 'auto',
          }}>{s}</span>
        ))}
      </div>

      {/* Card */}
      <div style={{ width: '100%', maxWidth: '420px', position: 'relative', zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <a href="/" style={{ textDecoration: 'none', display: 'inline-block' }}>
            <div style={{
              width: '48px', height: '48px',
              border: '2px solid #c0392b', borderRadius: '5px',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              fontSize: '12px', fontWeight: '700', color: '#c0392b',
              lineHeight: 1.1, margin: '0 auto',
            }}>
              <span>64</span>
              <span style={{ letterSpacing: '2px' }}>DAO</span>
            </div>
          </a>
        </div>

        {children}
      </div>
    </div>
  )
}

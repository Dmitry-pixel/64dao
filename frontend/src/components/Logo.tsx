// frontend/src/components/Logo.tsx

export function Logo() {
  return (
    <div className="logo-box">
      <div className="logo-sq">
        <span>64</span>
        <span>DAO</span>
      </div>
      <span className="logo-name">64 ДАО</span>
    </div>
  )
}

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

export function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

interface AuthSideProps {
  eyebrow: string
  title: string
}

export function AuthSide({ eyebrow, title }: AuthSideProps) {
  return (
    <div className="auth-side">
      <div className="hex-bg">
        {Array.from({ length: 16 }).map((_, i) => (
          <span key={i}>{HEX_TRIGRAMS[i * 5 % 64]}</span>
        ))}
      </div>
      <div className="auth-side-content">
        <Logo />
        <div style={{ marginTop: 48 }}>
          <span className="label-red">{eyebrow}</span>
          <h2 className="auth-tagline" style={{ marginTop: 14 }}>{title}</h2>
        </div>
      </div>
      <p className="auth-quote">
        «Перемены — единственное, что неизменно. Стратегия — это не план, а ответ на момент».
      </p>
    </div>
  )
}

export function SocialRow() {
  return (
    <>
      <div className="social-divider">или войти через</div>
      <div className="social-row">
        <button className="social-btn social-tg">
          <span className="social-mark">✈</span>Telegram
        </button>
        <button className="social-btn social-vk">
          <span className="social-mark">VK</span>ВКонтакте
        </button>
        <button className="social-btn social-mx">
          <span className="social-mark">M</span>Max
        </button>
      </div>
    </>
  )
}

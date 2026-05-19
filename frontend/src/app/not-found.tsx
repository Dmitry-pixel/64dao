'use client'
import { useRouter } from 'next/navigation'

const HEX = ['䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

export default function NotFound() {
  const router = useRouter()

  return (
    <div style={S.root}>
      {/* Фоновая сетка гексаграмм */}
      <div style={S.hexGrid} aria-hidden>
        {HEX.map((h, i) => (
          <span key={i} style={S.hexItem}>{h}</span>
        ))}
      </div>

      {/* Центральный блок */}
      <div style={S.card}>
        <div style={S.num404}>404</div>
        <div style={S.hexBig}>䷿</div>
        <h1 style={S.title}>Страница не найдена</h1>
        <p style={S.sub}>Потерялись в гексаграммах?</p>
        <button style={S.btn} onClick={() => router.push('/')}>
          Идём назад
        </button>
      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  root: {
    minHeight: '100vh',
    background: '#e8e4db',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    overflow: 'hidden',
  },
  hexGrid: {
    position: 'absolute',
    inset: 0,
    display: 'grid',
    gridTemplateColumns: 'repeat(10, 1fr)',
    gap: 0,
    padding: 16,
    pointerEvents: 'none',
  },
  hexItem: {
    fontFamily: 'Georgia, serif',
    fontSize: 42,
    color: '#1e3a8a',
    opacity: 0.05,
    textAlign: 'center',
    lineHeight: 1.4,
    userSelect: 'none',
  },
  card: {
    position: 'relative',
    zIndex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    padding: '56px 64px',
    background: 'rgba(255,255,255,0.7)',
    border: '1px solid rgba(26,37,64,0.1)',
    borderRadius: 16,
    backdropFilter: 'blur(6px)',
    maxWidth: 440,
    width: '90%',
    boxShadow: '0 8px 48px rgba(26,37,64,0.08)',
  },
  num404: {
    fontFamily: 'Georgia, serif',
    fontSize: 96,
    fontWeight: 400,
    color: '#c0392b',
    lineHeight: 1,
    letterSpacing: -4,
    marginBottom: 0,
  },
  hexBig: {
    fontFamily: 'Georgia, serif',
    fontSize: 64,
    color: '#1e3a8a',
    lineHeight: 1,
    marginBottom: 20,
    opacity: 0.6,
  },
  title: {
    fontFamily: 'Georgia, serif',
    fontSize: 26,
    fontWeight: 400,
    color: '#1a2540',
    margin: '0 0 10px',
  },
  sub: {
    fontFamily: 'sans-serif',
    fontSize: 14,
    color: 'rgba(26,37,64,0.55)',
    margin: '0 0 32px',
    lineHeight: 1.6,
  },
  btn: {
    background: '#1a2540',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '13px 36px',
    fontFamily: 'sans-serif',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    letterSpacing: 0.3,
  },
}

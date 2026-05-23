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

// [номер по Вэнь-вану, ...] — единый источник истины для символа
const HEX_INFO_LOGO: Record<string, number> = {
  'AAAAAA':1,'BBBBBB':2,'ABBBAB':3,'BABBBA':4,'AAABAB':5,'BABAAA':6,
  'BABBBB':7,'BBBBAB':8,'AAABAA':9,'AABAAA':10,'AAABBB':11,'BBBAAA':12,
  'ABAAAA':13,'AAAABA':14,'BBABBB':15,'BBBABB':16,'ABBAAB':17,'BAABBA':18,
  'AABBBB':19,'BBBBAA':20,'ABBABA':21,'ABABBA':22,'BBBBBA':23,'ABBBBB':24,
  'ABBAAA':25,'AAABBA':26,'ABBBBA':27,'BAAAAB':28,'BABBAB':29,'ABAABA':30,
  'BBAAAB':31,'BAAABB':32,'BBAAAA':33,'AAAABB':34,'BBBABA':35,'ABABBB':36,
  'ABABAA':37,'AABABA':38,'BBABAB':39,'BABABB':40,'AABBBA':41,'ABBBAA':42,
  'AAAAAB':43,'BAAAAA':44,'BBBAAB':45,'BAABBB':46,'BABAAB':47,'BAABAB':48,
  'ABAAAB':49,'BAAABA':50,'ABBABB':51,'BBABBA':52,'BBABAA':53,'AABABB':54,
  'ABAABB':55,'BBAABA':56,'BABBAA':57,'AABAAB':58,'BAABAA':59,'AABBAB':60,
  'AABBAA':61,'BBAABB':62,'ABABAB':63,'BABABA':64,
}

export function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const n = HEX_INFO_LOGO[combo]
  if (!n) return '䷀'
  return String.fromCodePoint(0x4DC0 + n - 1)
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

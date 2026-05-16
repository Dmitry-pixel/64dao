'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { AppNav } from '@/components/AppNav'

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

function WaitingContent() {
  const router = useRouter()
  const params = useSearchParams()
  const assessmentId = params.get('id')
  const combo = params.get('combo') ?? 'AAAAAA'

  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds(s => {
        if (s >= 4) {
          clearInterval(timer)
          if (assessmentId) router.push(`/report/${assessmentId}`)
          return s
        }
        return s + 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [assessmentId])

  return (
    <>
      <AppNav />
      <div className="wait-stage">
        <div className="wait-hex">{hexFor(combo)}</div>
        <h2>Формируем отчёт</h2>
        <p>
          Анализируем вашу комбинацию {combo} и подбираем стратегические рекомендации.
          Обычно это занимает меньше минуты.
        </p>
        <div className="wait-bar"><i /></div>
        <p className="faint" style={{ marginTop: 12 }}>
          {seconds < 2 ? 'Подбираем стратегию…' : seconds < 4 ? 'Формируем рекомендации…' : 'Почти готово…'}
        </p>
      </div>
    </>
  )
}

export default function WaitingPage() {
  return (
    <Suspense fallback={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>Загрузка…</div>}>
      <WaitingContent />
    </Suspense>
  )
}

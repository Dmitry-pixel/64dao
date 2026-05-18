'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { getAssessment } from '@/lib/api'
import { AppNav } from '@/components/AppNav'

const HEXAGRAM_DATA: { n: number; combo: string }[] = [
  {n:1,combo:'AAAAAA'},{n:2,combo:'BBBBBB'},{n:3,combo:'ABBBAB'},{n:4,combo:'BABBBA'},
  {n:5,combo:'AAABAB'},{n:6,combo:'BABAAA'},{n:7,combo:'BABBBB'},{n:8,combo:'BBBBAB'},
  {n:9,combo:'AAABAA'},{n:10,combo:'AABAAA'},{n:11,combo:'AAABBB'},{n:12,combo:'BBBAAA'},
  {n:13,combo:'ABAAAA'},{n:14,combo:'AAAABA'},{n:15,combo:'BBABBB'},{n:16,combo:'BBBABB'},
  {n:17,combo:'ABBAAB'},{n:18,combo:'BAABBA'},{n:19,combo:'AABBBB'},{n:20,combo:'BBBBAA'},
  {n:21,combo:'ABBABA'},{n:22,combo:'ABABBA'},{n:23,combo:'BBBBBA'},{n:24,combo:'ABBBBB'},
  {n:25,combo:'ABBAAA'},{n:26,combo:'AAABBA'},{n:27,combo:'ABBBBA'},{n:28,combo:'BAAAAB'},
  {n:29,combo:'BABBAB'},{n:30,combo:'ABAABA'},{n:31,combo:'BBAAAB'},{n:32,combo:'BAAABB'},
  {n:33,combo:'BBAAAA'},{n:34,combo:'AAAABB'},{n:35,combo:'BBBABA'},{n:36,combo:'ABABBB'},
  {n:37,combo:'ABABAA'},{n:38,combo:'AABABA'},{n:39,combo:'BBABAB'},{n:40,combo:'BABABB'},
  {n:41,combo:'AABBBA'},{n:42,combo:'ABBBAA'},{n:43,combo:'AAAAAB'},{n:44,combo:'BAAAAA'},
  {n:45,combo:'BBBAAB'},{n:46,combo:'BAABBB'},{n:47,combo:'BABAAB'},{n:48,combo:'BAABAB'},
  {n:49,combo:'ABAAAB'},{n:50,combo:'BAAABA'},{n:51,combo:'ABBABB'},{n:52,combo:'BBABBA'},
  {n:53,combo:'BBABAA'},{n:54,combo:'AABABB'},{n:55,combo:'ABAABB'},{n:56,combo:'BBAABA'},
  {n:57,combo:'BABBAA'},{n:58,combo:'AABAAB'},{n:59,combo:'BAABAA'},{n:60,combo:'AABBAB'},
  {n:61,combo:'AABBAA'},{n:62,combo:'BBAABB'},{n:63,combo:'ABABAB'},{n:64,combo:'BABABA'},
]
const COMBO_TO_N: Record<string, number> = Object.fromEntries(
  HEXAGRAM_DATA.map(h => [h.combo, h.n])
)

function hexFor(combo: string): string {
  const n = COMBO_TO_N[combo]
  if (!n) return '䷀'
  return String.fromCodePoint(0x4DC0 + n - 1)
}

const LABELS = [
  'Подбираем стратегию…',
  'Анализируем комбинацию…',
  'Формируем рекомендации…',
  'Готовим PDF-отчёт…',
  'Финальная проверка…',
  'Почти готово…',
]

function WaitingContent() {
  const router = useRouter()
  const params = useSearchParams()
  const assessmentId = params.get('id')
  const combo = params.get('combo') ?? 'AAAAAA'

  const [tick, setTick] = useState(0)
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    if (!assessmentId) return

    let attempts = 0
    const MAX_ATTEMPTS = 40   // 40 × 3 с = 2 минуты

    const poll = async () => {
      try {
        const data = await getAssessment(assessmentId)
        if (data.reports && data.reports.length > 0) {
          router.push(`/report/${assessmentId}`)
          return
        }
      } catch {
        // игнорируем ошибки поллинга
      }

      attempts++
      if (attempts >= MAX_ATTEMPTS) {
        setTimedOut(true)
        return
      }

      setTimeout(poll, 3000)
    }

    // Первый запрос через 2 секунды, затем каждые 3 секунды
    const initial = setTimeout(poll, 2000)
    return () => clearTimeout(initial)
  }, [assessmentId, router])

  // Анимация метки (меняется каждые 4 секунды)
  useEffect(() => {
    const t = setInterval(() => setTick(p => p + 1), 4000)
    return () => clearInterval(t)
  }, [])

  const label = LABELS[tick % LABELS.length]

  if (timedOut) {
    return (
      <>
        <AppNav />
        <div className="wait-stage">
          <div className="wait-hex">{hexFor(combo)}</div>
          <h2>Отчёт формируется</h2>
          <p>Генерация заняла больше обычного. Перейдите в «Мои отчёты» — отчёт появится там.</p>
          <button
            className="btn btn-primary"
            style={{ marginTop: 24 }}
            onClick={() => router.push('/reports')}
          >
            Мои отчёты →
          </button>
        </div>
      </>
    )
  }

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
        <p className="faint" style={{ marginTop: 12 }}>{label}</p>
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

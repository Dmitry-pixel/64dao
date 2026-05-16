'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createAssessment } from '@/lib/api'
import { AppNav } from '@/components/AppNav'

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

const QUESTIONS = [
  {
    eyebrow: 'Вопрос 01 / 06',
    h: 'Где сейчас фокус усилий компании?',
    help: 'Подумайте, какой тип задач занимает больше времени у руководства последние 3–6 месяцев.',
    a: 'Стабилизация и удержание текущих позиций',
    b: 'Поиск новых возможностей и направлений роста',
  },
  {
    eyebrow: 'Вопрос 02 / 06',
    h: 'Как принимаются ключевые решения?',
    help: 'Учитывайте именно практику, а не формальные регламенты.',
    a: 'Централизованно, на уровне собственника или директора',
    b: 'Распределённо, командами и руководителями подразделений',
  },
  {
    eyebrow: 'Вопрос 03 / 06',
    h: 'Какова ситуация с денежным потоком?',
    help: 'Оцените баланс поступлений и расходов за последние 3 месяца.',
    a: 'Стабильный или профицитный — средств достаточно',
    b: 'Напряжённый или дефицитный — нужны дополнительные ресурсы',
  },
  {
    eyebrow: 'Вопрос 04 / 06',
    h: 'Как компания воспринимает конкурентов?',
    help: 'Какая реакция типична при появлении нового конкурента или угрозы?',
    a: 'Защищаемся — укрепляем то, что уже есть',
    b: 'Атакуем — ищем способ выйти вперёд',
  },
  {
    eyebrow: 'Вопрос 05 / 06',
    h: 'Насколько стандартизированы процессы?',
    help: 'Подумайте о ключевых операционных процессах компании.',
    a: 'Высокая стандартизация — процессы описаны и повторяемы',
    b: 'Низкая стандартизация — многое держится на людях и интуиции',
  },
  {
    eyebrow: 'Вопрос 06 / 06',
    h: 'Каков основной драйвер роста последних 12 месяцев?',
    help: 'Что фактически принесло компании рост или позволило удержаться?',
    a: 'Эффективность — снижение издержек, оптимизация',
    b: 'Инновации — новые продукты, рынки, подходы',
  },
]

function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

export default function Method1Page() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<number, 'A' | 'B'>>({})
  const [picked, setPicked] = useState<'A' | 'B'>('A')
  const [saving, setSaving] = useState(false)

  const q = QUESTIONS[step]
  const progress = ((step) / QUESTIONS.length) * 100
  const combination = Object.values(answers).join('')

  const next = () => {
    const newAnswers = { ...answers, [step]: picked }
    setAnswers(newAnswers)

    if (step < QUESTIONS.length - 1) {
      setStep(step + 1)
      setPicked(newAnswers[step + 1] ?? 'A')
    } else {
      // Последний вопрос — сохраняем
      submit(newAnswers)
    }
  }

  const back = () => {
    if (step > 0) {
      setStep(step - 1)
      setPicked(answers[step - 1] ?? 'A')
    }
  }

  const submit = async (finalAnswers: Record<number, 'A' | 'B'>) => {
    setSaving(true)
    const combo = Object.values(finalAnswers).join('')
    try {
      const assessment = await createAssessment({
        method1_answers: Object.fromEntries(
          Object.entries(finalAnswers).map(([k, v]) => [String(Number(k) + 1), v])
        ),
        method1_combination: combo,
        status: 'completed',
      })
      router.push(`/assessment/waiting?id=${assessment.id}&combo=${combo}`)
    } catch {
      alert('Ошибка сохранения. Попробуйте ещё раз.')
      setSaving(false)
    }
  }

  const currentCombo = Object.entries({ ...answers, [step]: picked })
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([, v]) => v).join('')

  return (
    <>
      <AppNav />
      <div className="q-stage">
        {/* Прогресс */}
        <div className="q-progress">
          <span>{q.eyebrow}</span>
          <div className="q-progress-bar">
            <i style={{ width: `${progress}%` }} />
          </div>
          <div className="q-progress-dots">
            {QUESTIONS.map((_, i) => (
              <span
                key={i}
                className={i < step ? 'done' : i === step ? 'now' : ''}
              />
            ))}
          </div>
        </div>

        <div className="q-body">
          <div>
            <p className="q-text-eyebrow">{q.eyebrow}</p>
            <h2 className="q-text-h">{q.h}</h2>
            <p className="q-text-help">{q.help}</p>

            <div className="q-options">
              {(['A', 'B'] as const).map(letter => (
                <button
                  key={letter}
                  className={`q-option${picked === letter ? ' on' : ''}`}
                  onClick={() => setPicked(letter)}
                >
                  <div className="q-letter">{letter}</div>
                  <div className="q-text">{letter === 'A' ? q.a : q.b}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Визуализация гексаграммы */}
          <div className="q-visual">
            <div style={{ fontSize: 96, fontFamily: 'Georgia, serif', color: 'var(--blue)', lineHeight: 1, marginBottom: 16 }}>
              {hexFor(currentCombo.padEnd(6, 'A'))}
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-faint)', letterSpacing: 3 }}>
              {currentCombo.padEnd(6, '·')}
            </div>
          </div>
        </div>

        <div className="q-foot">
          <button className="btn btn-ghost" onClick={back} disabled={step === 0}>← Назад</button>
          <button
            className="btn btn-primary"
            onClick={next}
            disabled={saving}
            style={{ minWidth: 160, justifyContent: 'center' }}
          >
            {saving ? 'Сохраняем…' : step === QUESTIONS.length - 1 ? 'Завершить →' : 'Далее →'}
          </button>
        </div>
      </div>
    </>
  )
}

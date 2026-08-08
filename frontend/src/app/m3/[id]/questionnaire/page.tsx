'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import M3Survey from '@/components/m3/M3Survey'
import {
  calculate, getArbiterRequired, getPortfolio, getQuestionnaire,
  putOwnerRanks, saveAnswers,
  type M3AnswerIn, type M3Questionnaire,
} from '@/lib/m3'

const P = {
  page: { minHeight: '100vh', background: '#e8e4db' } as React.CSSProperties,
  stage: { maxWidth: 860, margin: '0 auto', padding: '56px 40px' } as React.CSSProperties,
  label: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2,
    textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600,
  } as React.CSSProperties,
  h1: {
    fontFamily: 'Georgia,serif', fontSize: 34, fontWeight: 400,
    color: '#1a2540', margin: '10px 0 12px',
  } as React.CSSProperties,
  text: {
    fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.65)',
    lineHeight: 1.7, marginBottom: 18, maxWidth: 620,
  } as React.CSSProperties,
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center', gap: 8, padding: '11px 22px',
    background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
  } as React.CSSProperties,
  btnGhost: {
    padding: '11px 18px', background: 'none', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
    color: '#1a2540',
  } as React.CSSProperties,
  warn: {
    fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', lineHeight: 1.6,
  } as React.CSSProperties,
}

export default function M3QuestionnairePage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = String(params?.id || '')

  const [data, setData] = useState<M3Questionnaire | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [started, setStarted] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    getPortfolio(id)
      .then(p => {
        if (p.status === 'calculated') {
          router.replace(`/report/m3/${id}`)
          return null
        }
        if (!p.objects.length) {
          // Не сообщение об ошибке, а недоделанный шаг: уводим туда, где его
          // доделывают. Кнопка «К портфелям» здесь замыкала круг.
          router.replace(`/m3/${id}/objects`)
          return null
        }
        return getQuestionnaire(id)
      })
      .then(q => { if (q) setData(q) })
      .catch((e: any) => setLoadError(
        e?.status === 404 ? 'Портфель не найден.' : e?.message || 'Не удалось загрузить анкету.',
      ))
  }, [id, router])

  // Ответы сохраняются пошагово, но незавершённый шаг теряется при уходе.
  useEffect(() => {
    if (!started || saving) return
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = '' }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [started, saving])

  async function handleSaveRanks(ranks: number[]) {
    setSaving(true)
    setError(null)
    try {
      await putOwnerRanks(id, ranks)
    } finally {
      setSaving(false)
    }
  }

  async function handleSave(answers: M3AnswerIn[]) {
    setSaving(true)
    setError(null)
    try {
      await saveAnswers(id, answers)
    } finally {
      setSaving(false)
    }
  }

  async function handleArbiters() {
    return getArbiterRequired(id)
  }

  async function handleCalculate() {
    setSaving(true)
    setError(null)
    try {
      await calculate(id)
      setStarted(false)
      router.push(`/report/m3/${id}`)
    } catch (e) {
      setSaving(false)
      throw e
    }
  }

  if (loadError) return (
    <div style={P.page}><div style={P.stage}>
      <p style={P.warn}>{loadError}</p>
      <button style={P.btnGhost} onClick={() => router.push('/m3')}>← К портфелям</button>
    </div></div>
  )

  if (!data) return (
    <div style={P.page}><div style={P.stage}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.6)' }}>Загрузка…</p>
    </div></div>
  )

  const objectCount = data.objects.length
  const overrideCount = data.objects.reduce((sum, o) => (
    sum + (o.screening_price ? 0 : 3) + (o.screening_market ? 3 : 0)
  ), 0)
  const baseCount = 6 + objectCount * 8 + overrideCount

  if (!started) return (
    <div style={P.page}><div style={P.stage}>
      <span style={P.label}>Метод 03 · шаг 2 из 2</span>
      <h1 style={P.h1}>Анкета</h1>
      <p style={P.text}>
        {baseCount} утверждений: шесть о рынке один раз на портфель и восемь
        по каждому из {objectCount} направлений
        {overrideCount > 0 && `, плюс ${overrideCount} уточняющих о рынке отдельных направлений`}.
        Около {Math.max(10, Math.round(baseCount / 3))} минут.
      </p>
      <p style={P.text}>
        Шкала от 1 до 4 без середины: «скорее да» и «скорее нет» — это уже выбор
        стороны. Если данных нет — «Не знаю»; такой ответ ничего не портит, он сам
        по себе диагноз и попадёт в отчёт оговоркой.
      </p>
      <p style={P.text}>
        По части линий может появиться третий вопрос — если два ответа разошлись
        или попали ровно на границу. Это не ошибка заполнения: там, где линия
        запускает пакет действий, опираться на два ответа нельзя.
      </p>
      <p style={P.text}>
        Ответы сохраняются после каждого шага. Вернуться и поправить можно до
        расчёта; после расчёта состав направлений фиксируется.
      </p>
      <div style={{ display: 'flex', gap: 12 }}>
        <button style={P.btnGhost} onClick={() => router.push('/m3')}>← К портфелям</button>
        <button style={P.btnPrimary} onClick={() => setStarted(true)}>Начать →</button>
      </div>
    </div></div>
  )

  return (
    <div style={P.page}><div style={P.stage}>
      <M3Survey
        questionnaire={data}
        saving={saving}
        error={error}
        onSaveRanks={handleSaveRanks}
        onSave={handleSave}
        onArbiters={handleArbiters}
        onCalculate={handleCalculate}
        onCancel={() => setStarted(false)}
      />
    </div></div>
  )
}

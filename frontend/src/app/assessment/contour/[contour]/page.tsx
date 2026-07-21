'use client'

import { Suspense, useEffect, useState } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import ContourSurvey from '@/components/ContourSurvey'
import { getContourItems, submitContour, type ContourItemsResponse } from '@/lib/api'

const P = {
  page: { minHeight: '100vh', background: '#e8e4db' } as React.CSSProperties,
  stage: { maxWidth: 720, margin: '0 auto', padding: '64px 40px' } as React.CSSProperties,
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
    lineHeight: 1.7, marginBottom: 20, maxWidth: 560,
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
  warn: { fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b' } as React.CSSProperties,
}


function ContourFlow() {
  const router = useRouter()
  const params = useParams<{ contour: string }>()
  const search = useSearchParams()

  const contour = String(params?.contour || '')
  const assessmentId = search.get('assessment') || ''

  const [data, setData] = useState<ContourItemsResponse | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [started, setStarted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!contour) return
    getContourItems(contour)
      .then(setData)
      .catch((e: any) => setLoadError(e?.message || 'Контур недоступен'))
  }, [contour])

  // Предупреждение о потере ответов при уходе со страницы
  useEffect(() => {
    if (!started || submitting) return
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = '' }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [started, submitting])

  async function handleSubmit(answers: Record<string, number | null>) {
    setSubmitting(true)
    setError(null)
    try {
      await submitContour(assessmentId, contour, answers)
      setStarted(false)
      router.push(`/assessment/continue?assessment=${assessmentId}`)
    } catch (e: any) {
      setError(e?.message || 'Не удалось сохранить контур. Попробуйте ещё раз.')
      setSubmitting(false)
    }
  }

  if (!assessmentId) return (
    <div style={P.page}><div style={P.stage}>
      <p style={P.warn}>Не указана диагностика. Откройте контур из карточки диагностики в кабинете.</p>
      <button style={P.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
    </div></div>
  )

  if (loadError) return (
    <div style={P.page}><div style={P.stage}>
      <p style={P.warn}>{loadError}</p>
      <button style={P.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
    </div></div>
  )

  if (!data) return (
    <div style={P.page}><div style={P.stage}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.6)' }}>Загрузка…</p>
    </div></div>
  )

  if (!started) return (
    <div style={P.page}><div style={P.stage}>
      <span style={P.label}>Метод 01 · дополнительный контур</span>
      <h1 style={P.h1}>{data.title}</h1>
      <p style={P.text}>{data.intro}</p>
      <p style={P.text}>
        {data.blocks.reduce((s, b) => s + b.items.length, 0)} утверждений в {data.blocks.length} блоках,
        около 10 минут. Оценивайте по фактическому состоянию компании, а не по планам.
        Если данных нет — «Не знаю», но не более {data.max_unknowns} на всю анкету
        и не более одного на блок.
      </p>
      <p style={P.text}>
        Пройти контур можно один раз: результат фиксируется снимком и используется в отчёте.
        Перед отправкой вы увидите все свои ответы и сможете их поправить.
      </p>
      <div style={{ display: 'flex', gap: 12 }}>
        <button style={P.btnGhost} onClick={() => router.push(`/report/${assessmentId}`)}>← К отчёту</button>
        <button style={P.btnPrimary} onClick={() => setStarted(true)}>Начать →</button>
      </div>
    </div></div>
  )

  return (
    <div style={P.page}>
      <ContourSurvey
        title={data.title}
        blocks={data.blocks}
        scaleLabels={data.scale_labels}
        maxUnknowns={data.max_unknowns}
        submitting={submitting}
        error={error}
        onSubmit={handleSubmit}
        onCancel={() => setStarted(false)}
      />
    </div>
  )
}


export default function ContourPage() {
  return (
    <Suspense fallback={<div style={P.page} />}>
      <ContourFlow />
    </Suspense>
  )
}

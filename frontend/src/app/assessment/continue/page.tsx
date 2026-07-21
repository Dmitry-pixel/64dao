'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { getAssessment, listContours, type Assessment, type ContourInfo } from '@/lib/api'

const P = {
  page: { minHeight: '100vh', background: '#e8e4db' } as React.CSSProperties,
  stage: { maxWidth: 720, margin: '0 auto', padding: '64px 40px' } as React.CSSProperties,
  label: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2,
    textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600,
  } as React.CSSProperties,
  h1: {
    fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400,
    color: '#1a2540', margin: '10px 0 14px',
  } as React.CSSProperties,
  text: {
    fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.65)',
    lineHeight: 1.7, marginBottom: 16, maxWidth: 560,
  } as React.CSSProperties,
  done: {
    display: 'inline-flex', alignItems: 'center', gap: 8,
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)',
    border: '1px solid rgba(26,37,64,0.12)', borderRadius: 4, padding: '4px 10px',
  } as React.CSSProperties,
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 24px',
    background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
  } as React.CSSProperties,
  btnGhost: {
    padding: '12px 20px', background: 'none', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
    color: '#1a2540',
  } as React.CSSProperties,
}


function ContinueFlow() {
  const router = useRouter()
  const search = useSearchParams()
  const id = search.get('assessment') || ''

  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [contours, setContours] = useState<ContourInfo[] | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([getAssessment(id), listContours()])
      .then(([a, c]) => { setAssessment(a); setContours(c.contours) })
      .catch(() => { setAssessment(null); setContours([]) })
  }, [id])

  if (!id) { router.replace('/dashboard'); return null }

  if (!assessment || !contours) return (
    <div style={P.page}><div style={P.stage}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.6)' }}>Загрузка…</p>
    </div></div>
  )

  const passed = new Set((assessment.passed_contours || []).map(p => p.contour))
  const enabled = contours.filter(c => c.enabled)
  const doneList = enabled.filter(c => passed.has(c.contour))
  const remaining = enabled.filter(c => !passed.has(c.contour))
  const next = remaining[0]

  const stepNo = doneList.length
  const total = enabled.length

  return (
    <div style={P.page}><div style={P.stage}>
      <span style={P.label}>
        {next ? `Диагностика · ${stepNo} из ${total} контуров` : 'Диагностика завершена'}
      </span>

      {next ? (
        <>
          <h1 style={P.h1}>Продолжим: {next.title}</h1>
          <p style={P.text}>{next.intro}</p>
          <p style={P.text}>
            24 утверждения, около 10 минут. Каждый контур оценивает свою функцию
            по одной шкале, поэтому их результаты сравнимы между собой —
            {stepNo >= 1
              ? ' сводная карта в отчёте уточнится с каждым следующим.'
              : ' со второго контура в отчёте появится сводная карта с указанием на то, какая функция сдерживает остальные.'}
          </p>
        </>
      ) : (
        <>
          <h1 style={P.h1}>{total > 1 ? 'Все контуры пройдены' : 'Диагностика завершена'}</h1>
          <p style={P.text}>
            {total > 1
              ? `Диагностика собрана полностью — ${total} контуров. Отчёт включает сводную карту и разбор каждой функции отдельно.`
              : 'Отчёт формируется, обычно это занимает несколько секунд.'}
          </p>
        </>
      )}

      {doneList.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 8, marginBottom: 24 }}>
          {doneList.map(c => (
            <span key={c.contour} style={P.done}>✓ {c.title}</span>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 12 }}>
        {next ? (
          <>
            <button style={P.btnPrimary}
              onClick={() => router.push(`/assessment/contour/${next.contour}?assessment=${id}`)}>
              Продолжить →
            </button>
            <button style={P.btnGhost} onClick={() => router.push(`/report/${id}`)}>
              Позже — смотреть отчёт
            </button>
          </>
        ) : (
          <>
            <button style={P.btnPrimary} onClick={() => router.push(`/report/${id}`)}>
              Смотреть отчёт →
            </button>
            <button style={P.btnGhost} onClick={() => router.push('/dashboard')}>
              В кабинет
            </button>
          </>
        )}
      </div>
    </div></div>
  )
}


export default function ContinuePage() {
  return (
    <Suspense fallback={<div style={P.page} />}>
      <ContinueFlow />
    </Suspense>
  )
}

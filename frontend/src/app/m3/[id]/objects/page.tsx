'use client'

/**
 * Шаг «направления» существующего портфеля.
 *
 * До появления этой страницы шаг жил внутри /m3 состоянием phase === 'objects'
 * и достигался ровно одним способом: сразу после создания портфеля. Черновик,
 * брошенный до ввода направлений, попасть в него больше не мог — «Продолжить»
 * вело в анкету, анкета говорила «нет направлений» и предлагала вернуться
 * в список, список снова вёл в анкету. Круг.
 *
 * Отдельный адрес его размыкает и попутно чинит то, что не чинилось состоянием:
 * F5 не теряет введённое, «Назад» работает, на шаг можно дать ссылку.
 */

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import PortfolioForm from '@/components/m3/PortfolioForm'
import {
  getPortfolio, listIndustries, putObjects,
  type M3Industry, type M3ObjectIn, type M3Portfolio,
} from '@/lib/m3'

const P = {
  page: { minHeight: '100vh', background: '#e8e4db' } as React.CSSProperties,
  stage: { maxWidth: 860, margin: '0 auto', padding: '64px 40px' } as React.CSSProperties,
  warn: {
    fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', lineHeight: 1.6,
  } as React.CSSProperties,
  btnGhost: {
    padding: '11px 18px', background: 'none', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
    color: '#1a2540',
  } as React.CSSProperties,
  muted: {
    fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)',
  } as React.CSSProperties,
}

/** Форма принимает M3ObjectIn; у сохранённого направления есть лишний id. */
function toInput(o: M3Portfolio['objects'][number]): M3ObjectIn {
  const { id, ...rest } = o
  return rest
}

export default function M3ObjectsPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = String(params?.id || '')

  const [portfolio, setPortfolio] = useState<M3Portfolio | null>(null)
  const [industries, setIndustries] = useState<M3Industry[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([getPortfolio(id), listIndustries()])
      .then(([p, inds]) => {
        // После расчёта состав направлений фиксируется — правило анкеты,
        // и здесь оно то же: иначе снимок расчёта разошёлся бы с портфелем.
        if (p.status === 'calculated') {
          router.replace(`/report/m3/${id}`)
          return
        }
        setPortfolio(p)
        setIndustries(inds)
      })
      .catch((e: any) => setLoadError(
        e?.status === 404 ? 'Портфель не найден.' : e?.message || 'Не удалось загрузить портфель.',
      ))
  }, [id, router])

  async function handleSubmit(objects: M3ObjectIn[]) {
    setBusy(true)
    setError(null)
    try {
      await putObjects(id, objects)
      router.push(`/m3/${id}/questionnaire`)
    } catch (e: any) {
      setError(e?.message || 'Не удалось сохранить направления.')
      setBusy(false)
    }
  }

  if (loadError) return (
    <div style={P.page}><div style={P.stage}>
      <p style={P.warn}>{loadError}</p>
      <div style={{ display: 'flex', gap: 12 }}>
        <button style={P.btnGhost} onClick={() => router.push('/m3')}>← К портфелям</button>
        <button style={P.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
      </div>
    </div></div>
  )

  if (!portfolio) return (
    <div style={P.page}><div style={P.stage}>
      <p style={P.muted}>Загрузка…</p>
    </div></div>
  )

  return (
    <div style={P.page}><div style={P.stage}>
      <PortfolioForm
        industries={industries}
        portfolioIndustryId={portfolio.industry_id}
        initial={portfolio.objects.map(toInput)}
        submitting={busy}
        error={error}
        onSubmit={handleSubmit}
        onCancel={() => router.push('/m3')}
      />
    </div></div>
  )
}

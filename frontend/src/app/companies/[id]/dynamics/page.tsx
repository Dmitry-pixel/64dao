'use client'
import React, { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import BackButton from '@/components/BackButton'
import { getMe, getCompanyDynamics } from '@/lib/api'

const fmt = (d?: string | null) => d ? new Date(d).toLocaleDateString('ru-RU') : '—'

export default function DynamicsPage() {
  const params = useParams()
  const cid = params.id as string
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<any>(null)
  const [compare, setCompare] = useState<'previous' | 'first'>('previous')

  const load = useCallback(async (mode: 'previous' | 'first') => {
    setLoading(true); setError('')
    try {
      await getMe()
      const d = await getCompanyDynamics(cid, mode)
      setData(d)
    } catch (e) {
      setError('Не удалось загрузить динамику')
    } finally {
      setLoading(false)
    }
  }, [cid])

  useEffect(() => { load(compare) }, [load, compare])

  const wrap = (inner: React.ReactNode) => (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: '32px 20px' }}>
      <div style={{ maxWidth: 820, margin: '0 auto' }}>
        <Link href="/companies" style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--red)', textDecoration: 'none' }}>← К компаниям</Link>
        {inner}
      </div>
    </div>
  )

  if (loading) return wrap(<p style={{ fontFamily: 'sans-serif', color: 'var(--text-mute)', marginTop: 20 }}>Загрузка…</p>)

  if (error) return wrap(<p style={{ color: '#c0392b', fontFamily: 'sans-serif', marginTop: 20 }}>{error}</p>)

  if (data && data.available === false) return wrap(
    <>
      <BackButton />
      <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400, color: 'var(--text)', margin: '10px 0 6px' }}>Динамика</h1>
      <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text-mute)' }}>
        Пока только {data.count} диагностик{data.count === 1 ? 'а' : ''}. Динамика появится после второй — повторите диагностику,
        чтобы увидеть изменения во времени.
      </p>
      <Link href={`/assessment?method=1&company=${cid}`}
        style={{ display: 'inline-block', marginTop: 16, background: 'var(--text)', color: '#fff', borderRadius: 6, padding: '10px 20px', fontFamily: 'sans-serif', fontSize: 14, textDecoration: 'none' }}>
        Повторить диагностику →
      </Link>
    </>
  )

  const S = {
    card: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, padding: '16px 20px', marginBottom: 14 } as React.CSSProperties,
    h2: { fontFamily: 'Georgia,serif', fontSize: 18, fontWeight: 400, color: 'var(--text)', margin: '0 0 10px' } as React.CSSProperties,
    faint: { fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)' } as React.CSSProperties,
  }
  const deltaColor = (d: number) => d > 0 ? '#166534' : d < 0 ? '#c0392b' : 'var(--text-mute)'
  const deltaStr = (d: number) => d > 0 ? `+${d}` : `${d}`
  // Названия контуров приходят с бэкенда (dynamics.contour_titles).
  const cTitle = (k?: string) => (k ? (data.contour_titles?.[k] || k) : '—')

  return wrap(
    <>
      <BackButton />
      <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400, color: 'var(--text)', margin: '10px 0 4px' }}>Динамика</h1>
      <p style={S.faint}>
        Сравнение: {fmt(data.compare_from?.created_at)} → {fmt(data.compare_to?.created_at)} · всего диагностик: {data.count}
      </p>

      <div style={{ display: 'flex', gap: 8, margin: '14px 0 20px' }}>
        {(['previous', 'first'] as const).map(m => (
          <button key={m} onClick={() => setCompare(m)}
            style={{ border: compare === m ? '1px solid var(--text)' : '1px solid rgba(26,37,64,0.2)', background: compare === m ? 'var(--text)' : 'transparent', color: compare === m ? '#fff' : 'var(--text)', borderRadius: 20, padding: '6px 14px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' }}>
            {m === 'previous' ? 'с предыдущей' : 'с первой'}
          </button>
        ))}
      </div>

      {/* Сводка */}
      <div style={S.card}>
        <h2 style={S.h2}>Сводка</h2>
        {['improved', 'degraded', 'unchanged'].map(k => {
          const list: string[] = (data.summary?.[k] || []).map((c: string) => cTitle(c))
          const label = k === 'improved' ? 'Улучшилось' : k === 'degraded' ? 'Деградировало' : 'Без изменений'
          const color = k === 'improved' ? '#166534' : k === 'degraded' ? '#c0392b' : 'var(--text-mute)'
          return (
            <div key={k} style={{ fontFamily: 'sans-serif', fontSize: 13, marginBottom: 4 }}>
              <span style={{ color, fontWeight: 600 }}>{label}:</span>{' '}
              <span style={{ color: 'var(--text)' }}>{list.length ? list.join(', ') : '—'}</span>
            </div>
          )
        })}
        {data.constraint?.changed && (
          <p style={{ ...S.faint, marginTop: 10 }}>
            Системное ограничение сместилось: {cTitle(data.constraint.from)} → {cTitle(data.constraint.to)}
          </p>
        )}
      </div>

      {/* Контуры */}
      {Object.entries(data.contours || {}).map(([key, d]: [string, any]) => (
        <div key={key} style={S.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <h2 style={{ ...S.h2, margin: 0 }}>{cTitle(key)}</h2>
            <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text)' }}>
              зрелость {d.maturity_from}/6 → {d.maturity_to}/6{' '}
              <span style={{ color: deltaColor(d.maturity_delta), fontWeight: 700 }}>({deltaStr(d.maturity_delta)})</span>
            </div>
          </div>
          {d.reached_prev_target && (
            <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: '#166534', margin: '6px 0 0' }}>✓ Достигнута целевая гексаграмма предыдущего прогона</p>
          )}
          {(d.line_changes?.length > 0) && (
            <div style={{ marginTop: 8 }}>
              {d.line_changes.map((ch: any, i: number) => (
                <div key={i} style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text)' }}>
                  Линия {ch.line} ({ch.line_title || ch.line_key}):{' '}
                  <span style={{ color: ch.direction === 'yin_to_yang' ? '#166534' : '#c0392b' }}>
                    {ch.direction === 'yin_to_yang' ? 'Инь → Ян (укрепление)' : 'Ян → Инь (ослабление)'}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div style={{ ...S.faint, marginTop: 8 }}>
            {d.moving_closed?.length > 0 && <>Закрытые точки роста: линии {d.moving_closed.join(', ')}. </>}
            {d.moving_new?.length > 0 && <>Новые: линии {d.moving_new.join(', ')}.</>}
            {(!d.moving_closed?.length && !d.moving_new?.length && !d.line_changes?.length) && <>Без изменений в линиях.</>}
          </div>
        </div>
      ))}
    </>
  )
}

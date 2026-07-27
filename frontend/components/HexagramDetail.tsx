'use client'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { HexagramSVG } from '@/components/HexagramSVG'

// Страница описания гексаграммы: содержимое, вынесенное из раздела 04 отчёта
// (Маркетинг, Управление, Предположения. Связи с будущим).
// Данные под авторизацией: /api/strategies/{combination} требует cookie,
// поэтому загрузка клиентская, а не на этапе сборки.
const API = process.env.NEXT_PUBLIC_API_URL || ''

const ASSM_LABELS: [string, string][] = [
  ['assm_planning', 'Планирование'],
  ['assm_growth', 'Рост и производительность'],
  ['assm_advertising', 'Реклама'],
  ['assm_feedback', 'Обратная связь'],
  ['assm_risk', 'Риск'],
  ['assm_product', 'Выбор продукта'],
  ['assm_service', 'Сервис'],
  ['assm_startup', 'Стартап'],
  ['assm_investment', 'Инвестиции и финансы'],
  ['assm_contracts', 'Договора и соглашения'],
  ['assm_sync', 'Синхронизация'],
  ['assm_creative', 'Творческий вклад'],
  ['assm_interaction', 'Взаимодействие'],
  ['assm_resources', 'Достаточность ресурсов'],
  ['assm_research', 'Исследование и разработка'],
  ['assm_trade', 'Международная торговля'],
  ['assm_failures', 'Источники неудач'],
  ['assm_success', 'Источники удачи'],
]

const labelStyle = {
  fontSize: 10,
  color: '#c0392b',
  letterSpacing: 2,
  textTransform: 'uppercase' as const,
  fontFamily: 'sans-serif',
  fontWeight: 700,
  marginBottom: 8,
}

const boxStyle = {
  border: '1px solid rgba(26,37,64,0.12)',
  borderRadius: 6,
  padding: '14px 18px',
  background: 'rgba(255,255,255,0.5)',
  fontFamily: 'sans-serif',
  fontSize: 13,
  color: 'rgba(26,37,64,0.72)',
  lineHeight: 1.7,
}

const subLabelStyle = {
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: 1.5,
  textTransform: 'uppercase' as const,
  fontFamily: 'sans-serif',
  color: 'rgba(26,37,64,0.5)',
  marginBottom: 4,
}

const bodyStyle = {
  fontFamily: 'sans-serif',
  fontSize: 13,
  color: 'rgba(26,37,64,0.7)',
  lineHeight: 1.7,
  margin: 0,
}

function Block({ title, text }: { title: string; text?: string | null }) {
  return (
    <div style={{ marginTop: 20 }}>
      <div style={labelStyle}>{title}</div>
      <div style={boxStyle}>
        {text
          ? text.split('\n').map((p, i) => (
              <p key={i} style={{ margin: i ? '10px 0 0' : 0 }}>{p}</p>
            ))
          : <em style={{ opacity: 0.4 }}>Не заполнено</em>}
      </div>
    </div>
  )
}

export default function HexagramDetail({ combination }: { combination: string }) {
  const search = useSearchParams()
  const from = search.get('from') || '/dashboard'
  const [s, setS] = useState<any>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    fetch(API + '/api/strategies/' + combination, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setS)
      .catch((code) => setErr(code === 401
        ? 'Требуется вход в личный кабинет.'
        : 'Не удалось загрузить описание гексаграммы.'))
  }, [combination])

  const backStyle = {
    fontFamily: 'sans-serif',
    fontSize: 12,
    letterSpacing: 1,
    textTransform: 'uppercase' as const,
    color: '#1e3a8a',
    textDecoration: 'none',
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 20px 60px' }}>
      <a href={from} style={backStyle}>← Назад к отчёту</a>

      {err && <p style={{ marginTop: 24, fontFamily: 'sans-serif', color: '#c0392b' }}>{err}</p>}

      {!err && !s && (
        <p style={{ marginTop: 24, fontFamily: 'sans-serif', opacity: 0.5 }}>Загрузка…</p>
      )}

      {s && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginTop: 24 }}>
            <HexagramSVG combo={combination} size={96} color="#1a2540" />
            <div>
              <h1 style={{ fontFamily: 'Georgia, serif', fontSize: 28, color: '#1a2540', margin: 0, fontWeight: 400 }}>
                {s.hexagram_number ? '№ ' + s.hexagram_number + ' · ' : ''}{s.title}
              </h1>
              <div style={{ fontFamily: 'monospace', letterSpacing: 3, marginTop: 6, color: 'rgba(26,37,64,0.6)' }}>
                {combination}
              </div>
              {s.lifecycle_stage && (
                <div style={{ fontFamily: 'sans-serif', fontSize: 13, marginTop: 6, color: 'rgba(26,37,64,0.6)' }}>
                  Стадия жизненного цикла: {s.lifecycle_stage}
                </div>
              )}
            </div>
          </div>

          <Block title="Стратагема" text={s.stratagema_title} />
          <Block title="Маркетинг" text={s.marketing_text} />
          <Block title="Управление" text={s.management_text} />

          <div style={{ marginTop: 28 }}>
            <div style={labelStyle}>Предположения. Связи с будущим</div>
            {ASSM_LABELS.map(([field, title]) => (
              <div key={field} style={{ marginBottom: 10 }}>
                <div style={subLabelStyle}>{title}</div>
                <p style={bodyStyle}>
                  {s[field] || <em style={{ opacity: 0.4 }}>Не заполнено</em>}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

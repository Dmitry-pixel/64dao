'use client'

import { useMemo, useState } from 'react'
import {
  type M3ChecklistStep, type M3Object, type M3Result, type M3TradeoffIn,
} from '@/lib/m3'

export type M3ChecklistProps = {
  steps: M3ChecklistStep[]
  objects: M3Object[]
  /** Порядок ранга V — приоритет вложения; ранга Z — очередь исполнения. */
  investmentOrder: string[]
  executionOrder: string[]
  results: M3Result[]
  decided: boolean
  onToggle: (stepId: string, done: boolean) => Promise<void>
  onDecide: (body: M3TradeoffIn) => Promise<void>
}

const STEP_LABEL: Record<string, string> = {
  route: 'Маршрут',
  hold: 'Удержать',
  prep: 'Подготовка',
  decision: 'Решение',
}

const STEP_NOTE: Record<string, string> = {
  route: 'Работа над назревшей слабостью: линия в состоянии старого Инь.',
  hold: 'Пакет удержания: линия перегрета, цель — остаться на месте, а не переместиться.',
  prep: 'Аналитическое время без бюджета. В правиле такта не учитывается.',
  decision: 'Решение владельца.',
}

const S = {
  h2: {
    fontFamily: 'sans-serif', fontSize: 13, letterSpacing: '0.10em',
    textTransform: 'uppercase' as const, fontWeight: 400, color: '#6b6559',
    borderBottom: '1px solid #cfc9bc', paddingBottom: 7, margin: '52px 0 20px',
  } as React.CSSProperties,
  h3: {
    fontFamily: 'Georgia,serif', fontSize: 19, fontWeight: 400,
    margin: '26px 0 6px', color: '#1a2540',
  } as React.CSSProperties,
  text: {
    fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.65)',
    lineHeight: 1.7, margin: '10px 0',
  } as React.CSSProperties,
  row: {
    display: 'flex', alignItems: 'flex-start', gap: 10,
    padding: '10px 0', borderBottom: '1px solid #e2ddd2',
  } as React.CSSProperties,
  rowText: {
    fontFamily: 'sans-serif', fontSize: 13.5, color: '#1a2540',
    lineHeight: 1.55, flex: 1,
  } as React.CSSProperties,
  tag: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: '0.06em',
    textTransform: 'uppercase' as const, color: '#6b6559',
    flex: '0 0 92px', paddingTop: 2,
  } as React.CSSProperties,
  done: { color: 'rgba(26,37,64,0.4)', textDecoration: 'line-through' } as React.CSSProperties,
  card: {
    background: '#f4f2ec', border: '1px solid #cfc9bc',
    padding: '20px 22px', margin: '20px 0',
  } as React.CSSProperties,
  banner: {
    borderLeft: '3px solid #1e3a8a', background: '#f4f2ec',
    padding: '14px 18px', margin: '18px 0',
    fontFamily: 'sans-serif', fontSize: 13.5, lineHeight: 1.65, color: '#1a2540',
  } as React.CSSProperties,
  bannerWarn: { borderLeftColor: '#c0392b' } as React.CSSProperties,
  bannerTitle: {
    fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase' as const,
    color: '#6b6559', display: 'block', marginBottom: 5,
  } as React.CSSProperties,
  label: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)',
    display: 'block', marginBottom: 5,
  } as React.CSSProperties,
  input: {
    padding: '8px 10px', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', background: '#fff',
    width: '100%', boxSizing: 'border-box' as const,
  } as React.CSSProperties,
  waveRow: {
    display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0',
    borderBottom: '1px solid #e2ddd2',
  } as React.CSSProperties,
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center', gap: 8, padding: '11px 22px',
    background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer', marginTop: 16,
  } as React.CSSProperties,
  warn: {
    fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b',
    lineHeight: 1.6, marginTop: 10,
  } as React.CSSProperties,
}

/** §17: не более двух направлений в активной трансформации одновременно. */
const ACTIVE_MAX = 2


export default function M3Checklist({
  steps, objects, investmentOrder, executionOrder, results,
  decided, onToggle, onDecide,
}: M3ChecklistProps) {
  const byId = useMemo(
    () => Object.fromEntries(objects.map(o => [o.id, o])),
    [objects],
  )
  const resultById = useMemo(
    () => Object.fromEntries(results.map(r => [r.object_id, r])),
    [results],
  )

  const [waves, setWaves] = useState<Record<string, number>>(() => {
    // Предложение метода: первые ACTIVE_MAX по рангу V идут в первую волну,
    // остальные во вторую. Правило такта — ограничение управленческого
    // ресурса, а не денег: запускать всё разом значит не закончить ничего.
    const out: Record<string, number> = {}
    investmentOrder.forEach((id, i) => { out[id] = i < ACTIVE_MAX ? 1 : 2 })
    return out
  })
  const [cost, setCost] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState<string | null>(null)

  const custom = investmentOrder.some((id, i) => waves[id] !== (i < ACTIVE_MAX ? 1 : 2))
  const wave1 = investmentOrder.filter(id => waves[id] === 1)

  const grouped = useMemo(() => {
    const out: Record<number, M3ChecklistStep[]> = {}
    for (const s of steps) (out[s.wave] ??= []).push(s)
    return out
  }, [steps])

  async function toggle(s: M3ChecklistStep) {
    setToggling(s.id)
    try {
      await onToggle(s.id, !s.done)
    } finally {
      setToggling(null)
    }
  }

  async function decide() {
    setError(null)
    if (wave1.length > ACTIVE_MAX) {
      setError(
        `В первой волне ${wave1.length} направления. Правило такта — не более ` +
        `${ACTIVE_MAX}: узким местом станет управленческий ресурс, а не деньги.`,
      )
      return
    }
    if (!wave1.length) {
      setError('Хотя бы одно направление должно быть в первой волне.')
      return
    }
    setBusy(true)
    try {
      const grouped: Record<string, string[]> = {}
      for (const [id, w] of Object.entries(waves)) {
        (grouped[String(w)] ??= []).push(id)
      }
      await onDecide({
        accepted_option: custom ? 'custom' : 'method',
        waves: grouped,
        cost_accepted: cost.trim() || null,
        review_triggers: [
          'Закрытие маршрута направления волны 1',
          'Падение выручки направления волны 1 более чем на 10% за полугодие',
          'Выход отложенного направления из состояния старого Инь',
          'Появление внешнего финансирования',
        ],
      })
    } catch (e: any) {
      setError(e?.message || 'Не удалось сохранить решение.')
    } finally {
      setBusy(false)
    }
  }

  const maxWave = Math.max(2, ...Object.values(waves))

  return (
    <>
      <h2 style={S.h2}><span style={{ color: '#c0392b', marginRight: 10 }}>05</span>Чек-лист</h2>

      {!decided && (
        <>
          <h3 style={S.h3}>Решение о порядке волн</h3>
          <p style={S.text}>
            Приоритет вложения и очередь исполнения расходятся — это результат,
            а не дефект. Метод предлагает порядок, принимает его собственник.
            Решение записывается: через полгода повторная диагностика увидит,
            что отложенное направление не изменилось, и без записанного решения
            истолкует это как невыполнение рекомендаций, а не как исполнение плана.
          </p>

          <div style={S.card}>
            {investmentOrder.map(id => {
              const o = byId[id]
              const r = resultById[id]
              if (!o) return null
              return (
                <div key={id} style={S.waveRow}>
                  <span style={{ ...S.rowText, flex: 1 }}>
                    {o.name}
                    <span style={{ color: '#6b6559', fontSize: 12 }}>
                      {' '}· вложение {r?.v_rank ?? '—'} · исполнение {r?.z_rank ?? '—'}
                    </span>
                  </span>
                  <select
                    aria-label={`Волна: ${o.name}`}
                    style={{ ...S.input, width: 'auto' }}
                    value={waves[id] ?? 2}
                    onChange={e => setWaves(prev => ({ ...prev, [id]: Number(e.target.value) }))}
                  >
                    {Array.from({ length: maxWave + 1 }, (_, i) => i + 1).map(w => (
                      <option key={w} value={w}>Волна {w}</option>
                    ))}
                  </select>
                </div>
              )
            })}

            <label style={{ ...S.label, marginTop: 16 }} htmlFor="cost">
              Цена выбора — что вы принимаете, откладывая остальное
            </label>
            <textarea
              id="cost"
              style={{ ...S.input, minHeight: 70, fontFamily: 'inherit' }}
              value={cost}
              maxLength={5000}
              placeholder="Например: обучение ждёт полгода, назревшая слабость в ресурсах может перестать быть назревшей"
              onChange={e => setCost(e.target.value)}
            />
            <p style={{ ...S.text, fontSize: 12, marginTop: 6 }}>
              Отложенное направление со старым Инь теряет энергию перехода:
              назревшая слабость либо снимается сама, либо перестаёт быть
              назревшей. Это предсказание, которое повторная диагностика проверит.
            </p>

            {error && <p style={S.warn}>{error}</p>}

            <button type="button" style={S.btnPrimary} onClick={decide} disabled={busy}>
              {busy ? 'Сохраняем…' : custom ? 'Принять свой порядок' : 'Принять порядок метода'}
            </button>
          </div>
        </>
      )}

      {decided && (
        <div style={{ ...S.banner }}>
          <span style={S.bannerTitle}>Решение зафиксировано</span>
          Чек-лист перестроен по волнам. События пересмотра приведены ниже —
          наступление любого означает пересобрать волны, а не продолжать по инерции.
        </div>
      )}

      {Object.keys(grouped).sort((a, b) => Number(a) - Number(b)).map(w => (
        <div key={w}>
          <h3 style={S.h3}>Волна {w}</h3>
          {grouped[Number(w)].map(s => (
            <div key={s.id} style={S.row}>
              <input
                type="checkbox"
                checked={s.done}
                disabled={toggling === s.id}
                onChange={() => toggle(s)}
                aria-label={s.step_text}
                style={{ marginTop: 3 }}
              />
              <span style={S.tag} title={STEP_NOTE[s.step_type]}>
                {STEP_LABEL[s.step_type] ?? s.step_type}
              </span>
              <span style={{ ...S.rowText, ...(s.done ? S.done : {}) }}>
                {s.step_text}
                {s.needs_budget && (
                  <span style={{ color: '#6b6559', fontSize: 12 }}> · требует бюджета</span>
                )}
              </span>
            </div>
          ))}
        </div>
      ))}

      {decided && (
        <div style={{ ...S.banner, ...S.bannerWarn }}>
          <span style={S.bannerTitle}>События пересмотра</span>
          Закрытие маршрута направления первой волны · падение его выручки более
          чем на 10% за полугодие · выход отложенного направления из состояния
          старого Инь · появление внешнего финансирования.
        </div>
      )}
    </>
  )
}

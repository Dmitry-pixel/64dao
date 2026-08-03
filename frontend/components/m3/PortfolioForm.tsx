'use client'

import { useMemo, useState } from 'react'
import {
  MIN_COVERAGE, MIN_SHARE, OBJECTS_MAX, OBJECTS_MIN,
  PROFITABILITY_LABELS,
  type M3Industry, type M3ObjectIn, type M3Profitability,
} from '@/lib/m3'

export type PortfolioFormProps = {
  industries: M3Industry[]
  portfolioIndustryId: number | null
  initial?: M3ObjectIn[]
  submitting?: boolean
  error?: string | null
  onSubmit: (objects: M3ObjectIn[]) => void
  onCancel?: () => void
}

const S = {
  eyebrow: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2,
    textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)',
  } as React.CSSProperties,
  h2: {
    fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400,
    color: '#1a2540', margin: '8px 0 10px',
  } as React.CSSProperties,
  text: {
    fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.65)',
    lineHeight: 1.7,
  } as React.CSSProperties,
  card: {
    border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8,
    padding: '16px 18px', marginTop: 14, background: 'rgba(255,255,255,0.45)',
  } as React.CSSProperties,
  cardHead: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 12,
  } as React.CSSProperties,
  cardNum: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2,
    textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)',
  } as React.CSSProperties,
  grid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))',
    gap: 12,
  } as React.CSSProperties,
  field: { display: 'flex', flexDirection: 'column' as const, gap: 5 } as React.CSSProperties,
  label: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)',
  } as React.CSSProperties,
  input: {
    padding: '8px 10px', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', background: '#fff',
    width: '100%', boxSizing: 'border-box' as const,
  } as React.CSSProperties,
  screening: {
    borderTop: '1px solid rgba(26,37,64,0.08)', marginTop: 12, paddingTop: 12,
  } as React.CSSProperties,
  check: {
    display: 'flex', alignItems: 'flex-start', gap: 8, marginTop: 8,
    fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', lineHeight: 1.5,
    cursor: 'pointer',
  } as React.CSSProperties,
  actions: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginTop: 24, gap: 12, flexWrap: 'wrap' as const,
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
  btnSmall: {
    padding: '6px 12px', background: 'none', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer',
    color: '#1a2540',
  } as React.CSSProperties,
  warn: {
    fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', lineHeight: 1.6,
    marginTop: 4,
  } as React.CSSProperties,
  note: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)',
    lineHeight: 1.6, marginTop: 6,
  } as React.CSSProperties,
  sum: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)',
    marginTop: 10,
  } as React.CSSProperties,
}

const PROFITABILITY_ORDER: M3Profitability[] = [
  'profitable', 'marginal', 'unprofitable', 'unknown',
]

function blank(position: number): M3ObjectIn {
  return {
    position,
    name: '',
    revenue: null,
    revenue_dynamics: null,
    revenue_share: null,
    profitability: 'unknown',
    industry_id: null,
    // Скрининг 1 по умолчанию «да» — ценовое давление как у рынка, блок Р*
    // не открывается. Скрининг 2 по умолчанию «нет» — направление на том же
    // рынке. Это состояние большинства направлений, и оно не требует
    // дополнительных вопросов.
    screening_price: true,
    screening_market: false,
    is_new_venture: false,
  }
}

function num(v: string): number | null {
  if (v.trim() === '') return null
  const n = Number(v.replace(',', '.'))
  return Number.isFinite(n) ? n : null
}


export default function PortfolioForm({
  industries, portfolioIndustryId, initial,
  submitting = false, error = null, onSubmit, onCancel,
}: PortfolioFormProps) {
  const [objects, setObjects] = useState<M3ObjectIn[]>(
    initial && initial.length ? initial : [blank(1), blank(2), blank(3)],
  )
  const [touched, setTouched] = useState(false)

  function patch(i: number, part: Partial<M3ObjectIn>) {
    setObjects(prev => prev.map((o, k) => (k === i ? { ...o, ...part } : o)))
  }

  function add() {
    setObjects(prev => (
      prev.length >= OBJECTS_MAX ? prev : [...prev, blank(prev.length + 1)]
    ))
  }

  function remove(i: number) {
    setObjects(prev => (
      prev.length <= OBJECTS_MIN
        ? prev
        : prev.filter((_, k) => k !== i).map((o, k) => ({ ...o, position: k + 1 }))
    ))
  }

  // Клиентские проверки зеркалят серверные. Смысл не в защите — сервер всё
  // равно проверит, — а в том, чтобы пользователь увидел, какое поле виновато,
  // вместо 422 без адреса.
  const problems = useMemo(() => {
    const out: string[] = []

    if (objects.some(o => !o.name.trim())) {
      out.push('У каждого направления должно быть название.')
    }

    const shares = objects.map(o => o.revenue_share).filter((s): s is number => s !== null)
    if (shares.length) {
      if (shares.some(s => s < MIN_SHARE)) {
        out.push(
          `Минимальная доля направления — ${MIN_SHARE}%. Направление меньшего ` +
          'размера не различимо на карте портфеля и искажает индекс защиты.',
        )
      }
      const total = shares.reduce((a, b) => a + b, 0)
      if (total > 100) {
        out.push(`Сумма долей ${total.toFixed(1)}% превышает 100%.`)
      }
      if (shares.length === objects.length && total < MIN_COVERAGE) {
        out.push(
          `Направления покрывают ${total.toFixed(1)}% выручки при минимуме ` +
          `${MIN_COVERAGE}%. Портфель, из которого выпала половина бизнеса, ` +
          'не отвечает на вопрос о распределении ресурса.',
        )
      }
    }

    if (objects.filter(o => o.is_new_venture).length > 1) {
      out.push('Новым направлением может быть отмечено только одно.')
    }

    return out
  }, [objects])

  const shareTotal = objects
    .map(o => o.revenue_share)
    .filter((s): s is number => s !== null)
    .reduce((a, b) => a + b, 0)

  const unprofitable = objects.filter(o => o.profitability === 'unprofitable')
  const unknownProfit = objects.filter(o => o.profitability === 'unknown')

  function submit() {
    setTouched(true)
    if (problems.length) return
    onSubmit(objects)
  }

  return (
    <div>
      <span style={S.eyebrow}>Метод 03 · шаг 1 из 2</span>
      <h2 style={S.h2}>Направления портфеля</h2>
      <p style={{ ...S.text, maxWidth: 620 }}>
        От {OBJECTS_MIN} до {OBJECTS_MAX} направлений: продукт, сегмент, канал
        или бизнес-единица. Числовые якоря — это данные, которые вы знаете точно;
        они дисциплинируют самооценку в анкете и задают размер круга на карте
        портфеля.
      </p>

      {objects.map((o, i) => (
        <div key={i} style={S.card}>
          <div style={S.cardHead}>
            <span style={S.cardNum}>Направление {i + 1}</span>
            {objects.length > OBJECTS_MIN && (
              <button type="button" style={S.btnSmall} onClick={() => remove(i)}>
                Убрать
              </button>
            )}
          </div>

          <div style={S.grid}>
            <div style={{ ...S.field, gridColumn: '1 / -1' }}>
              <label style={S.label} htmlFor={`name-${i}`}>Название</label>
              <input
                id={`name-${i}`}
                style={S.input}
                value={o.name}
                maxLength={255}
                placeholder="Например, салонный канал B2B"
                onChange={e => patch(i, { name: e.target.value })}
              />
            </div>

            <div style={S.field}>
              <label style={S.label} htmlFor={`rev-${i}`}>Выручка, млн ₽</label>
              <input
                id={`rev-${i}`}
                style={S.input}
                inputMode="decimal"
                value={o.revenue ?? ''}
                onChange={e => patch(i, { revenue: num(e.target.value) })}
              />
            </div>

            <div style={S.field}>
              <label style={S.label} htmlFor={`dyn-${i}`}>Динамика за 12 мес, %</label>
              <input
                id={`dyn-${i}`}
                style={S.input}
                inputMode="decimal"
                placeholder="−5 или 60"
                value={o.revenue_dynamics ?? ''}
                onChange={e => patch(i, { revenue_dynamics: num(e.target.value) })}
              />
            </div>

            <div style={S.field}>
              <label style={S.label} htmlFor={`share-${i}`}>Доля в общей выручке, %</label>
              <input
                id={`share-${i}`}
                style={S.input}
                inputMode="decimal"
                value={o.revenue_share ?? ''}
                onChange={e => patch(i, { revenue_share: num(e.target.value) })}
              />
            </div>

            <div style={S.field}>
              <label style={S.label} htmlFor={`prof-${i}`}>Прибыльность</label>
              <select
                id={`prof-${i}`}
                style={S.input}
                value={o.profitability}
                onChange={e => patch(i, { profitability: e.target.value as M3Profitability })}
              >
                {PROFITABILITY_ORDER.map(v => (
                  <option key={v} value={v}>{PROFITABILITY_LABELS[v]}</option>
                ))}
              </select>
            </div>

            <div style={S.field}>
              <label style={S.label} htmlFor={`ind-${i}`}>Область</label>
              <select
                id={`ind-${i}`}
                style={S.input}
                value={o.industry_id ?? ''}
                onChange={e => patch(i, {
                  industry_id: e.target.value === '' ? null : Number(e.target.value),
                })}
              >
                <option value="">Как у портфеля</option>
                {industries.map(ind => (
                  <option key={ind.id} value={ind.id}>{ind.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={S.screening}>
            <label style={S.check}>
              <input
                type="checkbox"
                checked={!o.screening_price}
                onChange={e => patch(i, { screening_price: !e.target.checked })}
              />
              <span>
                Ценовое давление и условия конкуренции по этому направлению
                <strong> отличаются</strong> от рынка в целом
                <span style={S.note}>
                  Откроет три отдельных вопроса о структуре рынка для этого направления.
                  Ценовая власть различается между сегментами одного рынка — без этого
                  привлекательность направлений различалась бы только по спросу.
                </span>
              </span>
            </label>

            <label style={S.check}>
              <input
                type="checkbox"
                checked={o.screening_market}
                onChange={e => patch(i, { screening_market: e.target.checked })}
              />
              <span>
                Направление работает на другом рынке — другая отрасль или география
                <span style={S.note}>
                  Откроет три вопроса о макроконтуре. Отмечайте только при смене
                  отрасли или страны: регулирование у сегментов одного рынка общее.
                </span>
              </span>
            </label>

            <label style={S.check}>
              <input
                type="checkbox"
                checked={o.is_new_venture}
                onChange={e => patch(i, { is_new_venture: e.target.checked })}
              />
              <span>Новое направление — запущено недавно, истории почти нет</span>
            </label>
          </div>
        </div>
      ))}

      {objects.length < OBJECTS_MAX && (
        <button type="button" style={{ ...S.btnGhost, marginTop: 14 }} onClick={add}>
          + Добавить направление
        </button>
      )}

      <p style={S.sum}>
        Направлений: {objects.length}. Сумма долей: {shareTotal ? `${shareTotal.toFixed(1)}%` : '—'}.
        {portfolioIndustryId === null && ' Область портфеля не выбрана — веса будут универсальными.'}
      </p>

      {unprofitable.length > 0 && (
        <p style={S.note}>
          {unprofitable.length === 1 ? 'Направление' : 'Направления'}{' '}
          {unprofitable.map(o => o.name || `№${o.position}`).join(', ')} отмечено как
          убыточное: линия ресурсов будет принудительно слабой независимо от ответов.
          Направление, которое не зарабатывает, не может иметь сильную ресурсную линию.
        </p>
      )}

      {unknownProfit.length > 0 && (
        <p style={S.note}>
          Прибыльность не указана у {unknownProfit.length} из {objects.length}.
          Это законный ответ, но он сам по себе диагноз линии ресурсов и попадёт в отчёт.
        </p>
      )}

      {touched && problems.map((p, i) => (
        <p key={i} style={S.warn}>{p}</p>
      ))}
      {error && <p style={S.warn}>{error}</p>}

      <div style={S.actions}>
        {onCancel
          ? <button type="button" style={S.btnGhost} onClick={onCancel}>← Назад</button>
          : <span />}
        <button type="button" style={S.btnPrimary} onClick={submit} disabled={submitting}>
          {submitting ? 'Сохраняем…' : 'К анкете →'}
        </button>
      </div>
    </div>
  )
}

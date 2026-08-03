'use client'

import { useMemo, useState } from 'react'
import {
  LINE_TITLES,
  type M3AnswerIn, type M3ArbiterRow, type M3Item, type M3Questionnaire,
} from '@/lib/m3'

export type M3SurveyProps = {
  questionnaire: M3Questionnaire
  saving?: boolean
  error?: string | null
  onSaveRanks: (ranks: number[]) => Promise<void>
  onSave: (answers: M3AnswerIn[]) => Promise<void>
  onArbiters: () => Promise<M3ArbiterRow[]>
  onCalculate: () => Promise<void>
  onCancel?: () => void
}

const SCALE: { value: number; label: string }[] = [
  { value: 1, label: 'Нет, совсем не так' },
  { value: 2, label: 'Скорее нет' },
  { value: 3, label: 'Скорее да' },
  { value: 4, label: 'Да, именно так' },
]

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
    lineHeight: 1.7, maxWidth: 620,
  } as React.CSSProperties,
  progressBar: {
    height: 3, background: 'rgba(26,37,64,0.1)', borderRadius: 2,
    margin: '14px 0 4px', overflow: 'hidden',
  } as React.CSSProperties,
  progressFill: { height: '100%', background: '#c0392b' } as React.CSSProperties,
  progressText: {
    fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.45)',
  } as React.CSSProperties,
  item: {
    borderTop: '1px solid rgba(26,37,64,0.1)', padding: '16px 0',
  } as React.CSSProperties,
  itemText: {
    fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540',
    lineHeight: 1.6, marginBottom: 4,
  } as React.CSSProperties,
  hint: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.55)',
    lineHeight: 1.6, marginBottom: 10, paddingLeft: 10,
    borderLeft: '2px solid rgba(192,57,43,0.35)',
  } as React.CSSProperties,
  lineTag: {
    fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)',
    marginBottom: 6,
  } as React.CSSProperties,
  scaleRow: { display: 'flex', gap: 8, flexWrap: 'wrap' as const, marginTop: 8 } as React.CSSProperties,
  scaleBtn: {
    padding: '8px 14px', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, background: 'none', fontFamily: 'sans-serif', fontSize: 13,
    cursor: 'pointer', color: '#1a2540', textAlign: 'left' as const,
  } as React.CSSProperties,
  scaleBtnOn: {
    background: '#1e3a8a', color: '#fff', borderColor: '#1e3a8a',
  } as React.CSSProperties,
  unknownOn: {
    background: 'rgba(26,37,64,0.08)', borderColor: 'rgba(26,37,64,0.35)',
  } as React.CSSProperties,
  actions: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginTop: 26, gap: 12,
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
    fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b',
    lineHeight: 1.6, marginTop: 10,
  } as React.CSSProperties,
  note: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)',
    lineHeight: 1.6, marginTop: 8,
  } as React.CSSProperties,
  rankRow: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 0', borderBottom: '1px solid rgba(26,37,64,0.08)',
  } as React.CSSProperties,
  rankName: {
    fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', flex: 1,
  } as React.CSSProperties,
  reviewRow: {
    display: 'flex', justifyContent: 'space-between', gap: 16,
    padding: '7px 0', borderBottom: '1px solid rgba(26,37,64,0.08)',
    fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540',
  } as React.CSSProperties,
  reviewHead: {
    fontFamily: 'Georgia,serif', fontSize: 17, color: '#1a2540',
    margin: '22px 0 6px',
  } as React.CSSProperties,
}

type Step =
  | { kind: 'ranks' }
  | { kind: 'market' }
  | { kind: 'object'; objectId: string; name: string; position: number }
  | { kind: 'arbiter' }
  | { kind: 'review' }

/** Ключ ответа: у блока Р направления нет, у остальных — есть. */
function key(code: string, objectId: string | null): string {
  return `${objectId ?? '-'}::${code}`
}


export default function M3Survey({
  questionnaire, saving = false, error = null,
  onSaveRanks, onSave, onArbiters, onCalculate, onCancel,
}: M3SurveyProps) {
  const { market_items, object_items, override_items, objects } = questionnaire

  const [answers, setAnswers] = useState<Record<string, number | null>>({})
  const [ranks, setRanks] = useState<Record<string, number | null>>({})
  const [arbiters, setArbiters] = useState<M3ArbiterRow[]>([])
  const [idx, setIdx] = useState(0)
  const [localError, setLocalError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const steps: Step[] = useMemo(() => {
    const out: Step[] = [{ kind: 'ranks' }, { kind: 'market' }]
    for (const o of objects) {
      out.push({ kind: 'object', objectId: o.id, name: o.name, position: o.position })
    }
    out.push({ kind: 'arbiter' }, { kind: 'review' })
    return out
  }, [objects])

  const step = steps[idx]

  /**
   * Пункты блока Р* показываются только по скринингам: переопределять рынок
   * там, где он общий, значит спрашивать одно и то же дважды.
   * Скрининг 1 (ценовое давление отличается) открывает Р1*–Р3* — линию 5.
   * Скрининг 2 (другой рынок) открывает Р4*–Р6* — линию 6.
   */
  function overridesFor(objectId: string): M3Item[] {
    const o = objects.find(x => x.id === objectId)
    if (!o) return []
    return override_items.filter(it => (
      (it.line === 5 && !o.screening_price) || (it.line === 6 && o.screening_market)
    ))
  }

  function itemsOf(s: Step): { item: M3Item; objectId: string | null }[] {
    if (s.kind === 'market') {
      return market_items.map(item => ({ item, objectId: null }))
    }
    if (s.kind === 'object') {
      return [
        ...object_items.map(item => ({ item, objectId: s.objectId })),
        ...overridesFor(s.objectId).map(item => ({ item, objectId: s.objectId })),
      ]
    }
    if (s.kind === 'arbiter') {
      return arbiters.flatMap(row =>
        row.items.map(item => ({ item, objectId: row.object_id })),
      )
    }
    return []
  }

  const current = step ? itemsOf(step) : []
  const allAnswered = current.every(({ item, objectId }) => key(item.code, objectId) in answers)

  const ranksReady = useMemo(() => {
    const vals = objects.map(o => ranks[o.id]).filter((v): v is number => v != null)
    if (vals.length !== objects.length) return false
    return new Set(vals).size === objects.length
  }, [ranks, objects])

  function set(code: string, objectId: string | null, value: number | null) {
    setAnswers(prev => ({ ...prev, [key(code, objectId)]: value }))
  }

  function collect(list: { item: M3Item; objectId: string | null }[]): M3AnswerIn[] {
    return list.map(({ item, objectId }) => ({
      item_code: item.code,
      object_id: objectId,
      value: answers[key(item.code, objectId)] ?? null,
    }))
  }

  async function next() {
    setLocalError(null)
    if (!step) return
    setBusy(true)
    try {
      if (step.kind === 'ranks') {
        const ordered = objects.map(o => ranks[o.id] as number)
        await onSaveRanks(ordered)
        setIdx(i => i + 1)
        return
      }

      if (step.kind === 'market' || step.kind === 'object' || step.kind === 'arbiter') {
        const payload = collect(current)
        if (payload.length) await onSave(payload)
      }

      // Арбитры известны только после того, как сохранены базовые ответы:
      // правило показа считается сервером по эффективным баллам.
      const nextStep = steps[idx + 1]
      if (nextStep?.kind === 'arbiter') {
        const rows = await onArbiters()
        const needed = rows.filter(r => r.items.length > 0)
        setArbiters(needed)
        setIdx(needed.length ? idx + 1 : idx + 2)
        return
      }

      setIdx(i => i + 1)
    } catch (e: any) {
      setLocalError(e?.message || 'Не удалось сохранить ответы. Попробуйте ещё раз.')
    } finally {
      setBusy(false)
    }
  }

  function back() {
    setLocalError(null)
    if (idx === 0) { onCancel?.(); return }
    // Шаг арбитров пропускаем назад, если он пуст.
    const prev = steps[idx - 1]
    if (prev?.kind === 'arbiter' && arbiters.length === 0) setIdx(idx - 2)
    else setIdx(idx - 1)
  }

  async function finish() {
    setLocalError(null)
    setBusy(true)
    try {
      await onCalculate()
    } catch (e: any) {
      setLocalError(e?.message || 'Расчёт не прошёл. Проверьте, что отвечены все пункты.')
      setBusy(false)
    }
  }

  const progress = steps.length > 1 ? Math.round((idx / (steps.length - 1)) * 100) : 0
  const disabled = saving || busy

  function renderItem({ item, objectId }: { item: M3Item; objectId: string | null }) {
    const k = key(item.code, objectId)
    const value = answers[k]
    const chosen = k in answers
    return (
      <div key={k} style={S.item}>
        <div style={S.lineTag}>
          {item.code} · {LINE_TITLES[item.line]}
        </div>
        <p style={S.itemText}>{item.text}</p>
        {item.hint && <p style={S.hint}>{item.hint}</p>}
        <div style={S.scaleRow}>
          {SCALE.map(s => (
            <button
              key={s.value}
              type="button"
              style={{
                ...S.scaleBtn,
                ...(chosen && value === s.value ? S.scaleBtnOn : {}),
              }}
              onClick={() => set(item.code, objectId, s.value)}
            >
              {s.value} — {s.label}
            </button>
          ))}
          <button
            type="button"
            style={{ ...S.scaleBtn, ...(chosen && value === null ? S.unknownOn : {}) }}
            onClick={() => set(item.code, objectId, null)}
          >
            Не знаю
          </button>
        </div>
      </div>
    )
  }

  if (!step) return null

  return (
    <div>
      <div style={S.progressBar}>
        <div style={{ ...S.progressFill, width: `${progress}%` }} />
      </div>
      <div style={S.progressText}>Шаг {idx + 1} из {steps.length}</div>

      {step.kind === 'ranks' && (
        <>
          <span style={S.eyebrow}>Метод 03 · до анкеты</span>
          <h2 style={S.h2}>Ваш порядок приоритета</h2>
          <p style={S.text}>
            Расставьте направления так, как видите приоритет сегодня: 1 — куда
            вложили бы деньги в первую очередь. Это нужно сделать <strong>до</strong>{' '}
            ответов на вопросы: метод сравнивает свой расчёт с вашей интуицией,
            и если заполнить порядок после анкеты, сравнивать будет не с чем.
          </p>
          <p style={S.note}>
            Совпадение не является целью. Полное совпадение означало бы, что метод
            не добавил ничего к тому, что вы и так знали; резкое расхождение —
            что он спорит с реальностью. Ценность в объяснимых расхождениях.
          </p>
          <div style={{ marginTop: 16 }}>
            {objects.map(o => (
              <div key={o.id} style={S.rankRow}>
                <span style={S.rankName}>{o.name}</span>
                <select
                  aria-label={`Приоритет: ${o.name}`}
                  style={{
                    padding: '7px 10px', border: '1px solid rgba(26,37,64,0.2)',
                    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14,
                    background: '#fff', color: '#1a2540',
                  }}
                  value={ranks[o.id] ?? ''}
                  onChange={e => setRanks(prev => ({
                    ...prev,
                    [o.id]: e.target.value === '' ? null : Number(e.target.value),
                  }))}
                >
                  <option value="">—</option>
                  {objects.map((_, i) => (
                    <option key={i + 1} value={i + 1}>{i + 1}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          {!ranksReady && Object.keys(ranks).length > 0 && (
            <p style={S.note}>Каждое место должно быть занято ровно одним направлением.</p>
          )}
        </>
      )}

      {step.kind === 'market' && (
        <>
          <span style={S.eyebrow}>Блок Р · рынок портфеля</span>
          <h2 style={S.h2}>Рынок, на котором вы работаете</h2>
          <p style={S.text}>
            Шесть вопросов, один раз на весь портфель. Отвечайте по наблюдаемому
            опыту, а не по отраслевым отчётам: метод выводит структуру рынка
            косвенно, из того, что вы видели сами.
          </p>
          {current.map(renderItem)}
        </>
      )}

      {step.kind === 'object' && (
        <>
          <span style={S.eyebrow}>
            Блок Н · направление {step.position} из {objects.length}
          </span>
          <h2 style={S.h2}>{step.name}</h2>
          <p style={S.text}>
            Отвечайте <strong>про это направление</strong>, а не про компанию целиком.
            Один и тот же вопрос по разным направлениям может иметь разные ответы —
            в этом и смысл.
          </p>
          {current.map(renderItem)}
        </>
      )}

      {step.kind === 'arbiter' && (
        <>
          <span style={S.eyebrow}>Уточнение</span>
          <h2 style={S.h2}>Несколько дополнительных вопросов</h2>
          <p style={S.text}>
            По части линий два базовых ответа разошлись или попали ровно на границу.
            Такие линии запускают пакеты действий, и опираться на два ответа здесь
            нельзя — уточняем третьим.
          </p>
          {arbiters.map(row => (
            <div key={row.object_id} style={{ marginTop: 18 }}>
              <div style={S.reviewHead}>{row.name}</div>
              {row.items.map(item => renderItem({ item, objectId: row.object_id }))}
            </div>
          ))}
        </>
      )}

      {step.kind === 'review' && (
        <>
          <span style={S.eyebrow}>Проверка</span>
          <h2 style={S.h2}>Ваши ответы</h2>
          <p style={S.text}>
            Проверьте перед расчётом. После расчёта состав направлений меняться
            не будет: ответы и результат фиксируются снимком, иначе выданный отчёт
            стал бы неповторяемым.
          </p>

          <div style={S.reviewHead}>Рынок портфеля</div>
          {market_items.map(item => (
            <div key={item.code} style={S.reviewRow}>
              <span>{item.code}</span>
              <span>{answers[key(item.code, null)] ?? 'не знаю'}</span>
            </div>
          ))}

          {objects.map(o => (
            <div key={o.id}>
              <div style={S.reviewHead}>{o.name}</div>
              {[...object_items, ...overridesFor(o.id)].map(item => (
                <div key={item.code} style={S.reviewRow}>
                  <span>{item.code}</span>
                  <span>{answers[key(item.code, o.id)] ?? 'не знаю'}</span>
                </div>
              ))}
              {arbiters.filter(a => a.object_id === o.id).flatMap(a => a.items).map(item => (
                <div key={item.code} style={S.reviewRow}>
                  <span>{item.code} · уточнение</span>
                  <span>{answers[key(item.code, o.id)] ?? 'не знаю'}</span>
                </div>
              ))}
            </div>
          ))}
        </>
      )}

      {(localError || error) && <p style={S.warn}>{localError || error}</p>}

      <div style={S.actions}>
        <button type="button" style={S.btnGhost} onClick={back} disabled={disabled}>
          ← Назад
        </button>

        {step.kind === 'review' ? (
          <button type="button" style={S.btnPrimary} onClick={finish} disabled={disabled}>
            {disabled ? 'Считаем…' : 'Рассчитать →'}
          </button>
        ) : (
          <button
            type="button"
            style={S.btnPrimary}
            onClick={next}
            disabled={disabled || (step.kind === 'ranks' ? !ranksReady : !allAnswered)}
          >
            {disabled ? 'Сохраняем…' : 'Дальше →'}
          </button>
        )}
      </div>

      {step.kind !== 'ranks' && step.kind !== 'review' && !allAnswered && (
        <p style={S.note}>
          Ответьте на все пункты шага. «Не знаю» — законный ответ: он сам по себе
          диагноз и попадёт в отчёт оговоркой.
        </p>
      )}
    </div>
  )
}

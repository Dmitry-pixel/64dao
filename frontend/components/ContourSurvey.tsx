'use client'

import { useMemo, useState } from 'react'

export type ContourItem = { item_id: string; text: string }
export type ContourBlock = { block: number; title: string; items: ContourItem[] }

export type ContourSurveyProps = {
  title: string
  blocks: ContourBlock[]
  scaleLabels: Record<string, string>
  maxUnknowns: number
  submitting?: boolean
  error?: string | null
  submitLabel?: string
  onSubmit: (answers: Record<string, number | null>) => void
  onCancel?: () => void
}

const C = {
  stage: { maxWidth: 860, margin: '0 auto', padding: '48px 40px' } as React.CSSProperties,
  eyebrow: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2,
    textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)',
  } as React.CSSProperties,
  h2: {
    fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400,
    color: '#1a2540', margin: '8px 0 10px',
  } as React.CSSProperties,
  legend: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.55)',
    lineHeight: 1.6, marginTop: 8,
  } as React.CSSProperties,
  progressBar: {
    height: 3, background: 'rgba(26,37,64,0.1)', borderRadius: 2,
    margin: '12px 0', overflow: 'hidden',
  } as React.CSSProperties,
  progressFill: { height: '100%', background: '#c0392b' } as React.CSSProperties,
  item: {
    borderTop: '1px solid rgba(26,37,64,0.1)', padding: '16px 0',
  } as React.CSSProperties,
  itemText: {
    fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540',
    lineHeight: 1.6, marginBottom: 10,
  } as React.CSSProperties,
  scaleRow: { display: 'flex', gap: 8, flexWrap: 'wrap' as const } as React.CSSProperties,
  scaleBtn: {
    minWidth: 40, padding: '8px 14px', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, background: 'none', fontFamily: 'sans-serif', fontSize: 13,
    cursor: 'pointer', color: '#1a2540',
  } as React.CSSProperties,
  scaleBtnOn: { background: '#1e3a8a', color: '#fff', borderColor: '#1e3a8a' } as React.CSSProperties,
  unknownOn: { background: 'rgba(26,37,64,0.08)', borderColor: 'rgba(26,37,64,0.35)' } as React.CSSProperties,
  hint: { fontFamily: 'sans-serif', fontSize: 12, marginTop: 10 } as React.CSSProperties,
  warn: { fontFamily: 'sans-serif', fontSize: 12, color: '#c0392b', marginTop: 8 } as React.CSSProperties,
  actions: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginTop: 28,
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
  reviewRow: {
    display: 'flex', justifyContent: 'space-between', gap: 16,
    padding: '8px 0', borderBottom: '1px solid rgba(26,37,64,0.08)',
  } as React.CSSProperties,
}


export default function ContourSurvey({
  title, blocks, scaleLabels, maxUnknowns,
  submitting = false, error = null, submitLabel = 'Завершить',
  onSubmit, onCancel,
}: ContourSurveyProps) {
  const [answers, setAnswers] = useState<Record<string, number | null>>({})
  const [idx, setIdx] = useState(0)
  const [review, setReview] = useState(false)

  const total = blocks.length
  const block = blocks[idx]

  const totalUnknowns = useMemo(
    () => Object.values(answers).filter(v => v === null).length,
    [answers],
  )
  const blockUnknowns = block ? block.items.filter(it => answers[it.item_id] === null).length : 0
  const answered = block ? block.items.every(it => it.item_id in answers) : false
  const complete = answered && blockUnknowns <= 1
  const limitReached = totalUnknowns >= maxUnknowns

  function set(itemId: string, value: number | null) {
    setAnswers(prev => ({ ...prev, [itemId]: value }))
  }

  function next() {
    if (idx < total - 1) setIdx(i => i + 1)
    else setReview(true)
  }

  function back() {
    if (review) { setReview(false); return }
    if (idx > 0) setIdx(i => i - 1)
    else onCancel?.()
  }

  function labelFor(v: number | null | undefined): string {
    if (v === null) return 'Не знаю'
    if (v === undefined) return '—'
    return `${v} — ${scaleLabels[String(v)] || ''}`
  }

  // ── Экран подтверждения перед отправкой ────────────────────────────────────
  if (review) {
    return (
      <div style={C.stage}>
        <div style={C.eyebrow}>{title} · проверка ответов</div>
        <h2 style={C.h2}>Проверьте ответы перед отправкой</h2>
        <p style={C.legend}>
          После отправки изменить ответы нельзя — результат фиксируется снимком.
          Если нужно что-то поправить, вернитесь к нужному блоку.
        </p>

        {blocks.map((b, bi) => (
          <div key={b.block} style={{ marginTop: 22 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
              <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: '#1a2540' }}>{b.title}</div>
              <button style={{ ...C.btnGhost, padding: '4px 12px', fontSize: 12 }}
                      onClick={() => { setIdx(bi); setReview(false) }}>Изменить</button>
            </div>
            {b.items.map(it => (
              <div key={it.item_id} style={C.reviewRow}>
                <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.72)', flex: 1 }}>{it.text}</div>
                <div style={{
                  fontFamily: 'sans-serif', fontSize: 13, whiteSpace: 'nowrap' as const,
                  color: answers[it.item_id] === null ? '#c0392b' : '#1a2540',
                }}>{labelFor(answers[it.item_id])}</div>
              </div>
            ))}
          </div>
        ))}

        {error && <p style={C.warn}>{error}</p>}

        <div style={C.actions}>
          <button style={C.btnGhost} onClick={back} disabled={submitting}>← К анкете</button>
          <button style={{ ...C.btnPrimary, opacity: submitting ? 0.4 : 1, minWidth: 160, justifyContent: 'center' }}
                  disabled={submitting}
                  onClick={() => onSubmit(answers)}>
            {submitting ? 'Отправка…' : `${submitLabel} →`}
          </button>
        </div>
      </div>
    )
  }

  // ── Степпер по блокам ──────────────────────────────────────────────────────
  if (!block) return null

  return (
    <div style={C.stage}>
      <div style={C.eyebrow}>{title}</div>
      <div style={C.progressBar}>
        <div style={{ ...C.progressFill, width: `${(idx / total) * 100}%` }} />
      </div>
      <div style={{ fontFamily: 'Georgia,serif', fontSize: 14, color: '#1a2540' }}>
        Блок {idx + 1} / {total}
      </div>

      <h2 style={C.h2}>{block.title}</h2>
      <p style={C.legend}>
        {[1, 2, 3, 4].map(n => `${n} — ${scaleLabels[String(n)] || ''}`).join('   ·   ')}
      </p>
      <p style={C.legend}>
        «Не знаю» снижает точность: балл по линии будет рассчитан по трём пунктам,
        а сама линия помечается в отчёте как неполная. Выбирайте, только если данных
        действительно нет.
      </p>

      <div style={{ marginTop: 18 }}>
        {block.items.map(it => {
          const val = it.item_id in answers ? answers[it.item_id] : undefined
          // Гасим «Не знаю» и по лимиту анкеты, и по лимиту блока: второй пропуск
          // в блоке делает линию неопределимой (§3.6), и узнавать об этом
          // постфактум, упёршись в заблокированную кнопку «Далее», — плохо.
          const unknownBlocked = val !== null && (limitReached || blockUnknowns >= 1)
          return (
            <div key={it.item_id} style={C.item}>
              <div style={C.itemText}>{it.text}</div>
              <div style={C.scaleRow}>
                {[1, 2, 3, 4].map(n => (
                  <button key={n} title={scaleLabels[String(n)] || ''}
                          style={{ ...C.scaleBtn, ...(val === n ? C.scaleBtnOn : {}) }}
                          onClick={() => set(it.item_id, n)}>{n}</button>
                ))}
                <button disabled={unknownBlocked}
                        style={{ ...C.scaleBtn, marginLeft: 18,
                                 opacity: unknownBlocked ? 0.35 : 1,
                                 ...(val === null ? C.unknownOn : {}) }}
                        onClick={() => set(it.item_id, null)}>Не знаю</button>
              </div>
            </div>
          )
        })}
      </div>

      <p style={{ ...C.hint, color: limitReached ? '#c0392b' : 'rgba(26,37,64,0.5)' }}>
        «Не знаю»: {totalUnknowns} из {maxUnknowns}{limitReached ? ' — лимит исчерпан' : ''}
      </p>
      {limitReached && !complete && (
        <p style={C.warn}>
          Лимит «Не знаю» исчерпан — оцените оставшиеся пункты по шкале 1–4.
          Если точных данных нет, выберите ближайшее приближение.
        </p>
      )}
      {blockUnknowns > 1 && (
        <p style={C.warn}>
          В блоке допускается не более одного ответа «Не знаю». Уточните оценку.
        </p>
      )}

      <div style={C.actions}>
        <button style={C.btnGhost} onClick={back}>← Назад</button>
        <button style={{ ...C.btnPrimary, opacity: !complete ? 0.4 : 1,
                         minWidth: 150, justifyContent: 'center' }}
                disabled={!complete} onClick={next}>
          {idx === total - 1 ? 'К проверке →' : 'Далее →'}
        </button>
      </div>
    </div>
  )
}

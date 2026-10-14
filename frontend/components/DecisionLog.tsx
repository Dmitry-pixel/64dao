'use client'
/**
 * Журнал решений под отчётом (Методы 1, 3, 4).
 *
 * Клиент записывает, какой сценарий выбрал, что делает и чего ждёт, а к
 * повторной диагностике отмечает, что произошло. Без записи повтор
 * показывает сдвиг, но не то, совпал ли он с замыслом.
 *
 * Стили встроенные и нейтральные: компонент стоит на трёх страницах с
 * разной вёрсткой, и общий класс пришлось бы согласовывать с каждой.
 */
import { useCallback, useEffect, useState } from 'react'
import { decisionsApi, type Decision, type DecisionMethod, type DecisionOutcome } from '@/lib/api'

const OUTCOME: { key: DecisionOutcome; label: string; color: string; bg: string }[] = [
  { key: 'done', label: 'Выполнено', color: '#166534', bg: '#dcfce7' },
  { key: 'partial', label: 'Частично', color: '#92400e', bg: '#fef3c7' },
  { key: 'not_done', label: 'Не выполнено', color: '#991b1b', bg: '#fee2e2' },
]

const C = {
  wrap: { margin: '40px 0 8px', padding: '24px 26px', background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 10 },
  label: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 },
  h2: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, color: '#1a2540', margin: '8px 0 6px' },
  lead: { fontFamily: 'sans-serif', fontSize: 13.5, color: 'rgba(26,37,64,0.65)', lineHeight: 1.6, margin: '0 0 18px', maxWidth: 680 },
  card: { border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, padding: '16px 18px', marginBottom: 12, background: '#fff' },
  field: { fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.45)', fontWeight: 700, margin: '10px 0 3px' },
  text: { fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', lineHeight: 1.55, whiteSpace: 'pre-wrap' as const, margin: 0 },
  input: { width: '100%', boxSizing: 'border-box' as const, padding: '9px 12px', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', background: '#fff', resize: 'vertical' as const, lineHeight: 1.5 },
  row: { display: 'flex', gap: 8, flexWrap: 'wrap' as const, alignItems: 'center' },
  btn: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '9px 18px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
  ghost: { background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '6px 12px', fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer' },
  link: { background: 'none', border: 'none', padding: 0, fontFamily: 'sans-serif', fontSize: 12, cursor: 'pointer', color: 'rgba(26,37,64,0.55)', textDecoration: 'underline' },
  faint: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.45)' },
}

function fmtDate(iso: string | null) {
  return iso ? new Date(iso).toLocaleDateString('ru-RU') : ''
}

function Field({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (<><div style={C.field}>{label}</div><p style={C.text}>{value}</p></>)
}

type Draft = { scenario: string; actions: string; expected: string }
const EMPTY: Draft = { scenario: '', actions: '', expected: '' }

function DraftForm({ initial, busy, submitLabel, onSubmit, onCancel }: {
  initial: Draft
  busy: boolean
  submitLabel: string
  onSubmit: (d: Draft) => void
  onCancel?: () => void
}) {
  const [d, setD] = useState<Draft>(initial)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={C.field}>Какой сценарий выбран *</div>
      <textarea style={C.input} rows={2} maxLength={4000} value={d.scenario}
        placeholder="Например: развиваем маркетплейсы, салонный канал удерживаем"
        onChange={e => setD({ ...d, scenario: e.target.value })} />
      <div style={C.field}>Что делаем</div>
      <textarea style={C.input} rows={3} maxLength={4000} value={d.actions}
        placeholder="Конкретные шаги, ответственные, сроки"
        onChange={e => setD({ ...d, actions: e.target.value })} />
      <div style={C.field}>Какой результат ожидаем</div>
      <textarea style={C.input} rows={2} maxLength={4000} value={d.expected}
        placeholder="Что должно измениться к повторной диагностике"
        onChange={e => setD({ ...d, expected: e.target.value })} />
      <div style={{ ...C.row, marginTop: 8 }}>
        <button style={{ ...C.btn, opacity: busy || !d.scenario.trim() ? 0.5 : 1 }}
          disabled={busy || !d.scenario.trim()} onClick={() => onSubmit(d)}>
          {busy ? 'Сохраняем…' : submitLabel}
        </button>
        {onCancel && <button style={C.ghost} onClick={onCancel}>Отмена</button>}
      </div>
    </div>
  )
}

function DecisionCard({ d, editable, onChange, onDelete }: {
  d: Decision
  editable: boolean
  onChange: (next: Decision) => void
  onDelete: (id: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState(d.outcome_note ?? '')
  const [err, setErr] = useState('')

  async function patch(body: Parameters<typeof decisionsApi.update>[1]): Promise<boolean> {
    setBusy(true); setErr('')
    try { onChange(await decisionsApi.update(d.id, body)); return true }
    catch { setErr('Не удалось сохранить. Попробуйте ещё раз.'); return false }
    finally { setBusy(false) }
  }

  if (editing) {
    return (
      <div style={C.card}>
        <DraftForm busy={busy} submitLabel="Сохранить"
          initial={{ scenario: d.scenario, actions: d.actions ?? '', expected: d.expected ?? '' }}
          onCancel={() => setEditing(false)}
          onSubmit={async v => { if (await patch(v)) setEditing(false) }} />
        {err && <p style={{ ...C.faint, color: '#c0392b' }}>{err}</p>}
      </div>
    )
  }

  const current = OUTCOME.find(o => o.key === d.outcome)
  return (
    <div style={C.card}>
      <div style={{ ...C.row, justifyContent: 'space-between' }}>
        <span style={C.faint}>Записано {fmtDate(d.created_at)}</span>
        {editable && (
          <span style={C.row}>
            <button style={C.link} onClick={() => setEditing(true)}>Изменить</button>
            <button style={{ ...C.link, color: '#c0392b' }}
              onClick={() => { if (confirm('Удалить запись о решении?')) onDelete(d.id) }}>Удалить</button>
          </span>
        )}
      </div>
      <Field label="Сценарий" value={d.scenario} />
      <Field label="Что делаем" value={d.actions} />
      <Field label="Ожидаемый результат" value={d.expected} />

      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid rgba(26,37,64,0.08)' }}>
        <div style={{ ...C.field, marginTop: 0 }}>Что произошло</div>
        {editable ? (
          <>
            <div style={C.row}>
              {OUTCOME.map(o => (
                <button key={o.key} disabled={busy}
                  style={{ ...C.ghost, ...(d.outcome === o.key ? { background: o.bg, color: o.color, borderColor: o.bg, fontWeight: 600 } : {}) }}
                  onClick={() => patch({ outcome: d.outcome === o.key ? '' : o.key })}>
                  {o.label}
                </button>
              ))}
            </div>
            <textarea style={{ ...C.input, marginTop: 8 }} rows={2} maxLength={4000} value={note}
              placeholder="Комментарий: что получилось, что помешало"
              onChange={e => setNote(e.target.value)}
              onBlur={() => { if (note !== (d.outcome_note ?? '')) patch({ outcome_note: note }) }} />
          </>
        ) : (
          <>
            <p style={C.text}>{current ? current.label : <span style={C.faint}>Пока не отмечено</span>}</p>
            <Field label="Комментарий" value={d.outcome_note} />
          </>
        )}
        {d.outcome_at && <p style={{ ...C.faint, marginTop: 6 }}>Отмечено {fmtDate(d.outcome_at)}</p>}
        {err && <p style={{ ...C.faint, color: '#c0392b' }}>{err}</p>}
      </div>
    </div>
  )
}

export default function DecisionLog({ method, sourceId }: { method: DecisionMethod; sourceId: string }) {
  const [items, setItems] = useState<Decision[] | null>(null)
  const [editable, setEditable] = useState(false)
  const [adding, setAdding] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    decisionsApi.list(method, sourceId)
      .then(r => { setItems(r.items); setEditable(r.editable) })
      .catch(() => setItems([]))
  }, [method, sourceId])

  useEffect(() => { if (sourceId) load() }, [sourceId, load])

  // Ссылка из письма-напоминания ведёт на #decision-log. Отчёт рисуется
  // после загрузки данных, поэтому браузер сам к якорю не прокручивает:
  // делаем это, когда блок появился.
  const loaded = items !== null
  useEffect(() => {
    if (!loaded || typeof window === 'undefined' || window.location.hash !== '#decision-log') return
    const t = setTimeout(() => document.getElementById('decision-log')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300)
    return () => clearTimeout(t)
  }, [loaded])

  if (items === null) return null
  // Чужой отчёт без записей: показывать администратору пустой блок незачем.
  if (!editable && items.length === 0) return null

  async function create(d: Draft) {
    setBusy(true); setErr('')
    try {
      const created = await decisionsApi.create({ method, source_id: sourceId, ...d })
      setItems(prev => [...(prev ?? []), created])
      setAdding(false)
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Не удалось сохранить')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    try {
      await decisionsApi.remove(id)
      setItems(prev => (prev ?? []).filter(x => x.id !== id))
    } catch {
      setErr('Не удалось удалить. Попробуйте ещё раз.')
    }
  }

  const showForm = editable && (adding || items.length === 0)

  return (
    <section style={C.wrap} id="decision-log">
      <span style={C.label}>Журнал решений</span>
      <h2 style={C.h2}>Что вы решили по итогам отчёта</h2>
      <p style={C.lead}>
        Запишите выбранный сценарий, шаги и ожидаемый результат. К повторной диагностике отметьте,
        что получилось: тогда отчёт покажет не только сдвиг, но и то, совпал ли он с вашим решением.
      </p>

      {items.map(d => (
        <DecisionCard key={d.id} d={d} editable={editable}
          onChange={next => setItems(prev => (prev ?? []).map(x => x.id === next.id ? next : x))}
          onDelete={remove} />
      ))}

      {showForm ? (
        <div style={C.card}>
          <DraftForm initial={EMPTY} busy={busy} submitLabel="Записать решение" onSubmit={create}
            onCancel={items.length > 0 ? () => setAdding(false) : undefined} />
        </div>
      ) : editable && (
        <button style={C.ghost} onClick={() => setAdding(true)}>+ Добавить решение</button>
      )}
      {err && <p style={{ ...C.faint, color: '#c0392b', marginTop: 8 }}>{err}</p>}
    </section>
  )
}

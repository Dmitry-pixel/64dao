'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  m4, m4Applies,
  type M4AnswerValue, type M4ClientQuestion, type M4Profile, type M4Progress,
  type M4Questionnaire, type M4RunOut,
} from '@/lib/m4'
import { M4 } from '@/components/m4/styles'

const UNKNOWN = 'unknown'

/**
 * Анкета Метода 4: модуль за модулем, в порядке, который задаёт сервер
 * (от конкретного к абстрактному). Ответ сохраняется сразу при выборе —
 * кнопки «Сохранить» нет, уйти и вернуться можно в любой момент.
 *
 * Вопросы-условия (applies_when) скрываются и появляются по тем же
 * правилам, что на сервере; сколько вопросов осталось, считает сервер —
 * клиентский подсчёт только для подсветки по модулям.
 */
export default function M4RunPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = String(params?.id || '')

  const [run, setRun] = useState<M4RunOut | null>(null)
  const [q, setQ] = useState<M4Questionnaire | null>(null)
  const [profile, setProfile] = useState<M4Profile | null>(null)
  const [answers, setAnswers] = useState<Record<string, M4AnswerValue>>({})
  const [numText, setNumText] = useState<Record<string, string>>({})
  const [progress, setProgress] = useState<M4Progress | null>(null)
  const [step, setStep] = useState(0)
  const [showMissing, setShowMissing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    ;(async () => {
      try {
        const r = await m4.run(id)
        if (r.status === 'calculated') { router.replace(`/m4/${id}/result`); return }
        const [qq, pr] = await Promise.all([m4.questionnaire(r.mode), m4.profile(r.company_id)])
        const map: Record<string, M4AnswerValue> = {}
        const nums: Record<string, string> = {}
        for (const a of r.answers ?? []) {
          map[a.code] = a
          if (a.number != null) nums[a.code] = String(a.number)
        }
        setRun(r); setQ(qq); setProfile(pr); setAnswers(map); setNumText(nums); setProgress(r.progress)
      } catch (e: any) {
        setLoadError(e?.status === 404 ? 'Диагностика не найдена.' : e?.message || 'Не удалось загрузить анкету.')
      }
    })()
  }, [id, router])

  const visible = useMemo(() => {
    if (!q) return []
    return q.modules.map(m => ({ ...m, questions: m.questions.filter(x => m4Applies(x, answers, profile)) }))
  }, [q, answers, profile])

  async function save(code: string, value: string | null, number: number | null) {
    const prev = answers[code]
    setAnswers(a => {
      const next = { ...a }
      if (value === null && number === null) delete next[code]
      else next[code] = { code, value, number }
      return next
    })
    setError(null)
    try {
      const r = await m4.saveAnswers(id, [{ code, value, number }])
      setProgress(r.progress)
    } catch (e: any) {
      setAnswers(a => {
        const next = { ...a }
        if (prev) next[code] = prev
        else delete next[code]
        return next
      })
      setError(typeof e?.message === 'string' ? e.message : 'Ответ не сохранился, попробуйте ещё раз.')
    }
  }

  function saveNumber(x: M4ClientQuestion) {
    const raw = (numText[x.code] ?? '').replace(',', '.').replace(/\s/g, '')
    if (raw === '') return
    const n = Number(raw)
    if (!Number.isFinite(n)) { setError('Введите число.'); return }
    const cur = answers[x.code]
    if (cur && cur.number === n) return
    void save(x.code, null, n)
  }

  async function calculate() {
    if (!progress || progress.missing.length) {
      setShowMissing(true)
      const first = visible.findIndex(m => m.questions.some(x => !answers[x.code]))
      if (first >= 0) setStep(first)
      return
    }
    setBusy(true)
    setError(null)
    try {
      await m4.calculate(id)
      router.push(`/m4/${id}/result`)
    } catch (e: any) {
      setError(typeof e?.message === 'string' ? e.message : 'Не удалось рассчитать. Проверьте, что отвечены все вопросы.')
      setBusy(false)
    }
  }

  if (loadError) return (
    <div style={M4.page}><div style={M4.stage}>
      <p style={M4.warn}>{loadError}</p>
      <button style={M4.btnGhost} onClick={() => router.push('/m4')}>← К диагностикам</button>
    </div></div>
  )
  if (!run || !q || !progress) return (
    <div style={M4.page}><div style={M4.stage}><p style={M4.muted}>Загрузка…</p></div></div>
  )

  const mod = visible[step]
  const last = step === visible.length - 1
  const pct = progress.required ? Math.round((progress.answered / progress.required) * 100) : 0

  return (
    <div style={M4.page}><div style={M4.stage}>
      <span style={M4.label}>
        Метод 04 · {run.mode === 'express' ? 'Экспресс' : 'Полная диагностика'} · {run.company_name}
      </span>

      {/* Прогресс: число отвеченных считает сервер — с учётом вопросов-условий. */}
      <div style={{ margin: '14px 0 6px', height: 6, background: 'rgba(26,37,64,0.1)', borderRadius: 3 }}>
        <div style={{ width: `${pct}%`, height: 6, background: '#1a2540', borderRadius: 3, transition: 'width .2s' }} />
      </div>
      <div style={M4.status}>Отвечено {progress.answered} из {progress.required}</div>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '16px 0 26px' }}>
        {visible.map((m, i) => {
          const done = m.questions.every(x => answers[x.code])
          const on = i === step
          return (
            <button
              key={m.code}
              title={m.name}
              onClick={() => setStep(i)}
              style={{
                ...M4.opt, padding: '5px 10px', fontSize: 12,
                background: on ? '#1a2540' : done ? 'rgba(46,125,91,0.12)' : '#fff',
                color: on ? '#fff' : '#1a2540',
              }}
            >
              {/* Без номера: порядок анкеты не совпадает с номерами модулей
                  в отчёте, и два разных «4» путали бы клиента. */}
              {m.name}
            </button>
          )
        })}
      </div>

      <h1 style={{ ...M4.h1, fontSize: 28 }}>{mod.name}</h1>
      {/* Вводный абзац модуля пересказывает его вопрос, поэтому показываем
          одно из двух: абзац, если он заведён в админке, иначе вопрос модуля. */}
      <p style={M4.text}>{mod.intro || mod.client_question}</p>

      {mod.questions.map(x => {
        const a = answers[x.code]
        const missing = showMissing && !a
        return (
          <div
            key={x.code}
            style={{ ...M4.card, borderLeft: missing ? '3px solid #c0392b' : '3px solid transparent' }}
          >
            <p style={M4.qText}>{x.text}</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              {x.type === 'number' || x.type === 'money' ? (
                <>
                  <input
                    style={{ ...M4.input, width: 160 }}
                    inputMode="decimal"
                    value={numText[x.code] ?? ''}
                    placeholder={x.min != null && x.max != null ? `${x.min}–${x.max}` : 'число'}
                    onChange={e => setNumText(t => ({ ...t, [x.code]: e.target.value }))}
                    onBlur={() => saveNumber(x)}
                    onKeyDown={e => { if (e.key === 'Enter') saveNumber(x) }}
                  />
                  {x.unit && <span style={M4.muted}>{x.unit === 'RUB' ? '₽' : x.unit}</span>}
                </>
              ) : (
                x.options.map(o => (
                  <button
                    key={o.value}
                    style={a?.value === o.value ? M4.optOn : M4.opt}
                    onClick={() => save(x.code, o.value, null)}
                  >
                    {o.label}
                  </button>
                ))
              )}
              {x.unknown_allowed && (
                <button
                  style={a?.value === UNKNOWN ? M4.optUnknownOn : M4.optUnknown}
                  onClick={() => {
                    setNumText(t => ({ ...t, [x.code]: '' }))
                    void save(x.code, UNKNOWN, null)
                  }}
                >
                  Не знаю
                </button>
              )}
            </div>
          </div>
        )
      })}

      {error && <p style={M4.warn}>{error}</p>}
      {showMissing && progress.missing.length > 0 && (
        <p style={M4.warn}>
          Без ответа: {progress.missing.length}. Они отмечены красной линией. «Не знаю» — тоже ответ.
        </p>
      )}

      <div style={{ display: 'flex', gap: 12, marginTop: 24, flexWrap: 'wrap' }}>
        <button
          style={M4.btnGhost}
          onClick={() => (step === 0 ? router.push('/m4') : setStep(step - 1))}
        >
          ← {step === 0 ? 'К диагностикам' : 'Назад'}
        </button>
        {!last && (
          <button style={M4.btnPrimary} onClick={() => { setStep(step + 1); window.scrollTo(0, 0) }}>
            Дальше →
          </button>
        )}
        {last && (
          <button style={M4.btnPrimary} onClick={calculate} disabled={busy}>
            {busy ? 'Считаем…' : 'Рассчитать →'}
          </button>
        )}
      </div>
      <p style={M4.note}>
        Ответы сохраняются сразу. Изменить их можно до расчёта; после расчёта анкета фиксируется.
      </p>
    </div></div>
  )
}

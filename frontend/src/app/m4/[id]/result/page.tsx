'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { m4, type M4Result, type M4RunOut } from '@/lib/m4'
import { M4, STATE_COLOR, STATE_LABEL } from '@/components/m4/styles'
import M4Wheel from '@/components/m4/M4Wheel'

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'высокая', medium: 'средняя', low: 'низкая — выводы стоит считать гипотезами',
}

/**
 * Черновой экран результата: колесо, разрывы, ограничение, достоверность.
 * Полный отчёт с карточками и рекомендациями — отдельный этап; этот экран
 * нужен, чтобы проверить расчёт на живых ответах.
 */
export default function M4ResultPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = String(params?.id || '')

  const [run, setRun] = useState<M4RunOut | null>(null)
  const [res, setRes] = useState<M4Result | null>(null)
  const [names, setNames] = useState<Record<number, string>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([m4.run(id), m4.result(id), m4.questionnaire('express')])
      .then(([r, s, q]) => {
        setRun(r)
        setRes(s)
        setNames(Object.fromEntries(q.modules.map(m => [m.code, m.name])))
      })
      .catch((e: any) => setError(typeof e?.message === 'string' ? e.message : 'Не удалось загрузить результат.'))
  }, [id])

  if (error) return (
    <div style={M4.page}><div style={M4.stage}>
      <p style={M4.warn}>{error}</p>
      <button style={M4.btnGhost} onClick={() => router.push('/m4')}>← К диагностикам</button>
    </div></div>
  )
  if (!run || !res) return (
    <div style={M4.page}><div style={M4.stage}><p style={M4.muted}>Загрузка…</p></div></div>
  )

  const scores: Record<number, number | null> = {}
  for (const [k, v] of Object.entries(res.modules)) scores[Number(k)] = v.score
  const c = res.constraint
  const noAccounting = Object.entries(res.modules).filter(([, v]) => v.no_accounting).map(([k]) => Number(k))

  return (
    <div style={M4.page}><div style={M4.stage}>
      <span style={M4.label}>
        Метод 04 · {res.mode === 'express' ? 'Экспресс' : 'Полная диагностика'} · {run.company_name}
      </span>
      <h1 style={M4.h1}>Алмазное колесо</h1>
      <p style={M4.text}>
        Балл каждого модуля от 0 до 100. Пунктирные кольца — границы 40 и 70:
        ниже 40 — низкий уровень, от 70 — высокий.
      </p>

      <M4Wheel scores={scores} names={names} highlight={c?.module ?? null} />

      <div style={{ ...M4.card, marginTop: 24 }}>
        <h2 style={M4.h2}>Главные разрывы</h2>
        {res.top_gaps.map(m => {
          const v = res.modules[String(m)]
          return (
            <div key={m} style={M4.listRow}>
              <span>{m}. {names[m]}</span>
              <span style={{ color: v.state ? STATE_COLOR[v.state] : undefined }}>
                {v.score == null ? '—' : Math.round(v.score)} · {v.state ? STATE_LABEL[v.state] : 'нет данных'}
              </span>
            </div>
          )
        })}
      </div>

      {res.mode === 'full' && (
        <div style={M4.card}>
          <h2 style={M4.h2}>Системное ограничение</h2>
          {c ? (
            <p style={{ ...M4.text, marginBottom: 0 }}>
              <b>{c.module}. {names[c.module]}</b> — модуль, от которого зависит отдача остальных:{' '}
              {c.blocked.map(b => names[b]).filter(Boolean).join(', ')}. Пока он не подтянут,
              вложения в зависимые модули окупаются хуже.
            </p>
          ) : (
            <p style={{ ...M4.text, marginBottom: 0 }}>Все модули на высоком уровне — ограничения нет.</p>
          )}
          <p style={M4.note}>
            Сработало противоречий: {res.fired_rules.length}
            {res.unverified_rules.length > 0 && ` · не проверено из-за «Не знаю»: ${res.unverified_rules.length}`}
            {' '}· действий в очереди: {res.priority_queue.length}
          </p>
        </div>
      )}

      <div style={M4.card}>
        <h2 style={M4.h2}>Достоверность ответов</h2>
        <p style={{ ...M4.text, marginBottom: 0 }}>
          {res.confidence.index} из 100 — {CONFIDENCE_LABEL[res.confidence.level]}.
        </p>
        {noAccounting.length > 0 && (
          <p style={M4.note}>
            Нет учёта: {noAccounting.map(m => names[m]).join(', ')} — на большинство вопросов о фактах
            ответ «Не знаю».
          </p>
        )}
      </div>

      {res.mode === 'express' && (
        <div style={M4.card}>
          <h2 style={M4.h2}>Что дальше</h2>
          <p style={{ ...M4.text, marginBottom: 12 }}>
            Экспресс показывает разрывы, но не называет модуль, который сдерживает остальные,
            и не выстраивает очередь действий. Это делает полная диагностика — ответы экспресса
            в неё перенесутся.
          </p>
          <button style={M4.btnPrimary} onClick={() => router.push(
            `/m4?mode=full&company=${encodeURIComponent(run.company_name || '')}`,
          )}>
            Полная диагностика →
          </button>
        </div>
      )}

      <p style={M4.note}>Полный отчёт с рекомендациями по каждому модулю появится на следующем этапе.</p>
      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <button style={M4.btnGhost} onClick={() => router.push('/m4')}>← К диагностикам</button>
      </div>
    </div></div>
  )
}

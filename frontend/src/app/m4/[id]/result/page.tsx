'use client'

import { useEffect, useState, type CSSProperties } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { m4, type M4CardText, type M4Report, type M4ReportAction } from '@/lib/m4'
import { M4, STATE_COLOR, STATE_LABEL } from '@/components/m4/styles'
import M4Wheel from '@/components/m4/M4Wheel'

/**
 * Отчёт Метода 4. Всё, что здесь показано, собрано на сервере
 * (GET /api/m4/runs/{id}/report): цифры — из снимка расчёта, тексты — из
 * карточек и правил админки. Страница ничего не вычисляет и не держит
 * копий текстов, поэтому веб и будущий PDF не разойдутся.
 */

const SEVERITY_LABEL: Record<string, string> = { high: 'серьёзное', medium: 'заметное', low: 'слабое' }

const R = {
  section: { marginTop: 44 } as CSSProperties,
  h2: { fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400, color: '#1a2540', margin: '0 0 6px' } as CSSProperties,
  lead: { ...M4.text, marginBottom: 16 } as CSSProperties,
  cardTitle: { fontFamily: 'Georgia,serif', fontSize: 19, color: '#1a2540', margin: '0 0 8px', fontWeight: 400 } as CSSProperties,
  body: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.8)', lineHeight: 1.7, margin: '0 0 10px' } as CSSProperties,
  mistake: {
    fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.7)', lineHeight: 1.6,
    borderLeft: '2px solid rgba(192,57,43,0.5)', padding: '2px 0 2px 12px', margin: '12px 0 0',
  } as CSSProperties,
  sub: { fontFamily: 'sans-serif', fontSize: 12, fontWeight: 600, color: '#1a2540', margin: '12px 0 4px' } as CSSProperties,
  list: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.8)', lineHeight: 1.7, margin: 0, paddingLeft: 20 } as CSSProperties,
  meta: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.55)', marginTop: 12 } as CSSProperties,
  tag: {
    display: 'inline-block', fontFamily: 'sans-serif', fontSize: 11, padding: '2px 8px', borderRadius: 10,
    marginRight: 6, background: 'rgba(26,37,64,0.08)', color: '#1a2540',
  } as CSSProperties,
  banner: {
    background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.3)', borderRadius: 8,
    padding: '14px 18px', fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', lineHeight: 1.6, margin: '18px 0',
  } as CSSProperties,
}

function Mistake({ text }: { text: string | null }) {
  if (!text) return null
  return <p style={R.mistake}><b>Типичная ошибка.</b> {text}</p>
}

function CardBody({ card }: { card: M4CardText | null }) {
  if (!card) return null
  return (
    <>
      <h3 style={R.cardTitle}>{card.title}</h3>
      <p style={R.body}>{card.body}</p>
      <Mistake text={card.mistake} />
    </>
  )
}

function StateBadge({ score, state }: { score: number | null; state: string | null }) {
  const color = state ? STATE_COLOR[state] : 'rgba(26,37,64,0.5)'
  return (
    <span style={{ fontFamily: 'sans-serif', fontSize: 13, color, whiteSpace: 'nowrap' }}>
      {score == null ? '—' : Math.round(score)} · {state ? STATE_LABEL[state] : 'нет данных'}
    </span>
  )
}

function Action({ a }: { a: M4ReportAction }) {
  return (
    <div style={{ ...M4.card, opacity: a.blocked_by_constraint ? 0.8 : 1 }}>
      <div style={{ marginBottom: 8 }}>
        <span style={{ ...R.tag, background: '#1a2540', color: '#fff' }}>{a.n}</span>
        {a.is_constraint && <span style={{ ...R.tag, background: 'rgba(192,57,43,0.12)', color: '#c0392b' }}>системное ограничение</span>}
        {a.blocked_by_constraint && <span style={R.tag}>после снятия ограничения</span>}
        <span style={R.tag}>{a.module_name ?? 'противоречие'}</span>
      </div>
      <h3 style={R.cardTitle}>{a.title}</h3>
      {a.body && <p style={R.body}>{a.body}</p>}
      {a.steps && a.steps.length > 0 && (
        <>
          <div style={R.sub}>Шаги</div>
          <ol style={R.list}>{a.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
        </>
      )}
      {a.options && a.options.length > 0 && (
        <>
          <div style={R.sub}>Выберите один из вариантов</div>
          <ul style={R.list}>{a.options.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </>
      )}
      {a.first_step && (<><div style={R.sub}>С чего начать</div><p style={{ ...R.body, margin: 0 }}>{a.first_step}</p></>)}
      {a.how_to_check && (<><div style={R.sub}>Как проверить</div><p style={{ ...R.body, margin: 0 }}>{a.how_to_check}</p></>)}
      <div style={R.meta}>
        Вклад в результат {a.effect} из 3 · первый результат через {a.speed_weeks} нед. · затраты на внедрение {a.cost} из 3
      </div>
    </div>
  )
}

export default function M4ReportPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = String(params?.id || '')

  const [rep, setRep] = useState<M4Report | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    m4.report(id)
      .then(setRep)
      .catch((e: any) => setError(typeof e?.message === 'string' ? e.message : 'Не удалось загрузить отчёт.'))
  }, [id])

  if (error) return (
    <div style={M4.page}><div style={M4.stage}>
      <p style={M4.warn}>{error}</p>
      <button style={M4.btnGhost} onClick={() => router.push('/m4')}>← К диагностикам</button>
    </div></div>
  )
  if (!rep) return (
    <div style={M4.page}><div style={M4.stage}><p style={M4.muted}>Загрузка…</p></div></div>
  )

  const full = rep.run.mode === 'full'
  const scores: Record<number, number | null> = {}
  const names: Record<number, string> = {}
  for (const m of rep.modules) { scores[m.code] = m.score; names[m.code] = m.name }
  const c = rep.constraint
  const date = rep.run.calculated_at ? new Date(rep.run.calculated_at).toLocaleDateString('ru-RU') : ''

  return (
    <div style={M4.page}><div style={M4.stage}>
      <span style={M4.label}>
        Метод 04 · {full ? 'Полная диагностика' : 'Экспресс'} · {rep.run.company_name}{date && ` · ${date}`}
      </span>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <h1 style={M4.h1}>Алмазное колесо</h1>
        {/* Относительный адрес, как у PDF Метода 3: на сервере /api идёт через
            тот же домен, и куки авторизации уходят вместе с запросом. */}
        <a
          href={`/api/m4/runs/${id}/pdf`}
          target="_blank"
          rel="noreferrer"
          style={{
            fontFamily: 'sans-serif', fontSize: 13, color: '#fff', background: '#1a2540',
            borderRadius: 6, padding: '9px 18px', textDecoration: 'none',
          }}
        >
          Скачать PDF
        </a>
      </div>

      {rep.confidence.cautious && (
        <div style={R.banner}>
          <b>Осторожный режим.</b> Слишком много ответов «Не знаю» или ответы расходятся между собой.
          Выводы ниже — гипотезы для проверки, а не основание для решений.
        </div>
      )}

      <p style={M4.text}>
        Балл каждого модуля от 0 до 100. Пунктирные кольца — границы 40 и 70: ниже 40 — низкий уровень,
        от 70 — высокий. Модуль 10 «Финансы» — следствие решений в остальных девяти.
      </p>
      <M4Wheel scores={scores} names={names} highlight={c?.module ?? null} />

      {/* ── Главное ─────────────────────────────────────────────────── */}
      <div style={{ ...M4.card, marginTop: 24 }}>
        <h2 style={{ ...R.h2, fontSize: 22 }}>Главное</h2>
        {full && c && (
          <p style={R.body}>
            Системное ограничение — <b>{c.module}. {c.name}</b>. От него зависит отдача модулей:{' '}
            {c.blocked.map(b => b.name).join(', ')}. Начинать с него.
          </p>
        )}
        {full && !c && <p style={R.body}>Все управленческие модули на высоком уровне — системного ограничения нет.</p>}
        <p style={R.body}>
          Самые большие разрывы: {rep.top_gaps.map(g => `${g.code}. ${g.name}`).join('; ')}.
        </p>
        {rep.cause_effect?.text && <p style={{ ...R.body, marginBottom: 0 }}>{rep.cause_effect.text}</p>}
      </div>

      {/* ── Ограничение ─────────────────────────────────────────────── */}
      {full && c && (
        <section style={R.section}>
          <h2 style={R.h2}>Системное ограничение</h2>
          <p style={R.lead}>
            Не самый низкий балл, а модуль, от которого зависят сильные. Пока он не подтянут,
            вложения в зависимые модули окупаются хуже.
          </p>
          <div style={{ ...M4.card, borderLeft: '3px solid #c0392b' }}>
            <div style={{ ...R.meta, marginTop: 0, marginBottom: 8 }}>
              {c.module}. {c.name} · <StateBadge score={c.score} state={c.score < 40 ? 'low' : 'mid'} />
            </div>
            <CardBody card={c.card} />
          </div>
        </section>
      )}

      {/* ── Очередь действий ────────────────────────────────────────── */}
      {full && rep.actions.length > 0 && (
        <section style={R.section}>
          <h2 style={R.h2}>С чего начинать</h2>
          <p style={R.lead}>
            Действия по порядку: сначала системное ограничение, затем то, что даёт больший результат
            быстрее и дешевле{rep.resistance > 1 && ' — с поправкой на то, что изменения в компании даются с сопротивлением'}.
            Действия по модулям, которые зависят от ограничения, стоят в конце.
          </p>
          {rep.actions.map(a => <Action key={a.key} a={a} />)}
        </section>
      )}

      {/* ── Противоречия ────────────────────────────────────────────── */}
      {full && (rep.contradictions.length > 0 || rep.unverified.length > 0) && (
        <section style={R.section}>
          <h2 style={R.h2}>Противоречия</h2>
          <p style={R.lead}>
            Сочетания ответов, которые по отдельности
            выглядят нормально, а вместе указывают на то, что компания работает против себя.
          </p>
          {rep.contradictions.map(x => (
            <div key={x.code} style={M4.card}>
              <div style={{ marginBottom: 8 }}>
                <span style={{ ...R.tag, color: x.severity === 'high' ? '#c0392b' : '#1a2540' }}>
                  {SEVERITY_LABEL[x.severity]}
                </span>
              </div>
              <h3 style={R.cardTitle}>{x.title}</h3>
              <p style={R.body}>{x.diagnosis}</p>
              <div style={R.sub}>Что происходит</div>
              <p style={R.body}>{x.what_happens}</p>
              <div style={R.sub}>Как развязать — один из вариантов</div>
              <ul style={R.list}>{x.fix_one_of.map((f, i) => <li key={i}>{f}</li>)}</ul>
              <div style={R.sub}>Цена бездействия</div>
              <p style={{ ...R.body, margin: 0 }}>{x.cost_of_inaction}</p>
            </div>
          ))}
          {rep.unverified.length > 0 && (
            <p style={M4.note}>
              Не удалось проверить из-за ответов «Не знаю»: {rep.unverified.map(u => u.title).join('; ')}.
            </p>
          )}
        </section>
      )}

      {/* ── Модули ──────────────────────────────────────────────────── */}
      <section style={R.section}>
        <h2 style={R.h2}>Состояние модулей</h2>
        {rep.modules.map(m => (
          <div key={m.code} style={M4.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
              <span style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)' }}>
                {m.code}. {m.name}
                {c?.module === m.code && <span style={{ color: '#c0392b' }}> · системное ограничение</span>}
              </span>
              <StateBadge score={m.score} state={m.state} />
            </div>
            <CardBody card={m.card} />
            {m.no_accounting && (
              <p style={M4.note}>
                На большинство вопросов о фактах этого модуля ответ «Не знаю»: в компании нет учёта
                по этому направлению. Это само по себе диагноз.
              </p>
            )}
          </div>
        ))}
      </section>

      {/* ── Достоверность ───────────────────────────────────────────── */}
      <section style={R.section}>
        <h2 style={R.h2}>Достоверность ответов</h2>
        <div style={M4.card}>
          <div style={{ ...R.meta, marginTop: 0, marginBottom: 8 }}>Индекс {rep.confidence.index} из 100</div>
          <CardBody card={rep.confidence.card} />
          {rep.confidence.no_accounting.length > 0 && (
            <p style={M4.note}>Нет учёта: {rep.confidence.no_accounting.map(m => m.name).join(', ')}.</p>
          )}
        </div>
      </section>

      {!full && (
        <section style={R.section}>
          <div style={M4.card}>
            <h2 style={{ ...R.h2, fontSize: 22 }}>Что даст полная диагностика</h2>
            <p style={R.body}>
              Экспресс показывает разрывы, но не называет модуль, который сдерживает остальные, не ищет
              противоречия и не выстраивает очередь действий. Это делает полная диагностика — ответы
              экспресса в неё перенесутся.
            </p>
            <button style={M4.btnPrimary} onClick={() => router.push(
              `/m4?mode=full&company=${encodeURIComponent(rep.run.company_name || '')}`,
            )}>
              Полная диагностика →
            </button>
          </div>
        </section>
      )}

      <div style={{ display: 'flex', gap: 12, marginTop: 28 }}>
        <button style={M4.btnGhost} onClick={() => router.push('/m4')}>← К диагностикам</button>
      </div>
    </div></div>
  )
}

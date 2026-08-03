'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import M3Checklist from '@/components/m3/M3Checklist'
import PortfolioMap from '@/components/m3/PortfolioMap'
import {
  LINE_TITLES, PROFITABILITY_LABELS,
  getChecklist, getReport, postTradeoff, toggleChecklistStep,
  type M3ChecklistStep, type M3Report, type M3Result, type M3TradeoffIn,
} from '@/lib/m3'

const C = {
  bg: '#e8e4db', paper: '#f4f2ec', dark: '#1a2540',
  red: '#c0392b', blue: '#1e3a8a', line: '#cfc9bc', muted: '#6b6559',
}

const S = {
  page: { minHeight: '100vh', background: C.bg, color: C.dark } as React.CSSProperties,
  stage: {
    maxWidth: 900, margin: '0 auto', padding: '48px 32px 96px',
    fontFamily: 'Georgia,"Times New Roman",serif', fontSize: 15, lineHeight: 1.6,
  } as React.CSSProperties,
  header: { borderBottom: `2px solid ${C.dark}`, paddingBottom: 18 } as React.CSSProperties,
  brand: {
    fontSize: 12, letterSpacing: '0.18em', color: C.muted,
    textTransform: 'uppercase' as const,
  } as React.CSSProperties,
  h1: { fontSize: 27, margin: '10px 0 6px', fontWeight: 400 } as React.CSSProperties,
  sub: { fontSize: 14, color: C.muted } as React.CSSProperties,
  meta: {
    display: 'flex', gap: 26, flexWrap: 'wrap' as const,
    fontSize: 13, color: C.muted, marginTop: 12,
  } as React.CSSProperties,
  h2: {
    fontSize: 13, letterSpacing: '0.10em', textTransform: 'uppercase' as const,
    fontWeight: 400, color: C.muted, borderBottom: `1px solid ${C.line}`,
    paddingBottom: 7, margin: '52px 0 20px',
  } as React.CSSProperties,
  num: { color: C.red, marginRight: 10 } as React.CSSProperties,
  h3: { fontSize: 19, fontWeight: 400, margin: '0 0 6px' } as React.CSSProperties,
  h4: {
    fontSize: 13, letterSpacing: '0.06em', textTransform: 'uppercase' as const,
    color: C.muted, fontWeight: 400, margin: '22px 0 8px',
  } as React.CSSProperties,
  table: {
    width: '100%', borderCollapse: 'collapse' as const,
    fontSize: 13.5, margin: '14px 0',
  } as React.CSSProperties,
  th: {
    textAlign: 'left' as const, fontWeight: 400, color: C.muted, fontSize: 12,
    letterSpacing: '0.04em', textTransform: 'uppercase' as const,
    borderBottom: `1px solid ${C.line}`, padding: '7px 8px 7px 0',
    verticalAlign: 'bottom' as const,
  } as React.CSSProperties,
  td: {
    padding: '8px 8px 8px 0', borderBottom: '1px solid #e2ddd2',
    verticalAlign: 'top' as const,
  } as React.CSSProperties,
  tdNum: { textAlign: 'right' as const, paddingRight: 14 } as React.CSSProperties,
  card: {
    background: C.paper, border: `1px solid ${C.line}`,
    padding: '24px 26px', margin: '22px 0',
  } as React.CSSProperties,
  hx: {
    display: 'flex', gap: 20, alignItems: 'baseline', flexWrap: 'wrap' as const,
    fontSize: 13.5, marginTop: 4,
  } as React.CSSProperties,
  code: {
    fontFamily: '"Courier New",monospace', fontSize: 15, letterSpacing: '0.14em',
  } as React.CSSProperties,
  cellline: { fontSize: 12.5, color: C.muted, marginTop: 6 } as React.CSSProperties,
  banner: {
    borderLeft: `3px solid ${C.blue}`, background: C.paper,
    padding: '14px 18px', margin: '18px 0', fontSize: 13.5,
  } as React.CSSProperties,
  bannerWarn: { borderLeftColor: C.red } as React.CSSProperties,
  bannerTitle: {
    fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase' as const,
    color: C.muted, display: 'block', marginBottom: 5,
  } as React.CSSProperties,
  lineRow: {
    display: 'flex', alignItems: 'center', gap: 12, padding: '3px 0', fontSize: 13,
  } as React.CSSProperties,
  glyph: { flex: '0 0 66px', height: 9, position: 'relative' as const } as React.CSSProperties,
  btnGhost: {
    padding: '11px 18px', background: 'none', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
    color: C.dark,
  } as React.CSSProperties,
  warn: { fontSize: 13, color: C.red, lineHeight: 1.6 } as React.CSSProperties,
  muted: { color: C.muted, fontSize: 12.5, lineHeight: 1.65 } as React.CSSProperties,
}

const FLAG_LABELS: Record<string, string> = {
  BORDERLINE_LINE: 'пограничный балл линии',
  NEAR_OLD_YANG: 'балл подходит к границе перегрева',
  NEAR_OLD_YIN: 'балл подходит к границе назревшей слабости',
  VETO_UNPROFITABLE: 'вето по убыточности: линия ресурсов принудительно слабая',
  VETO_UNKNOWN: 'прибыльность не указана — это сам по себе диагноз линии ресурсов',
  VETO_MOBILITY_CONFLICT: 'вето и перегрев на одной линии — случай требует разбора вручную',
  REVENUE_CONTRADICTION: 'выручка падает при высокой оценке спроса',
  ECONOMY_CONTRADICTION: 'направление убыточно при высокой оценке экономики',
  SCALE_CONTRADICTION: 'крупная доля выручки при слабом канале',
  STRAIGHTLINING: 'все шесть линий совпали — анкета заполнена однородно',
}

const PORTFOLIO_FLAG_LABELS: Record<string, string> = {
  UNIFORM_PORTFOLIO: 'все направления в одной ячейке — формулировки их не различили',
  SELF_INFLATION: 'оценки систематически завышены',
  RANK_MISMATCH: 'расчёт расходится с порядком, названным собственником',
}

const MOBILITY_LABELS: Record<string, string> = {
  old_yin: 'старый Инь · назревшая слабость',
  old_yang: 'старый Ян · перегрев',
}

function LineGlyph({ yang, moving }: { yang: boolean; moving: boolean }) {
  const bg = moving ? C.red : C.dark
  return (
    <span style={S.glyph} aria-hidden="true">
      {yang
        ? <i style={{ position: 'absolute', top: 0, height: 9, left: 0, width: 66, background: bg, display: 'block' }} />
        : <>
            <i style={{ position: 'absolute', top: 0, height: 9, left: 0, width: 28, background: bg, display: 'block' }} />
            <i style={{ position: 'absolute', top: 0, height: 9, left: 38, width: 28, background: bg, display: 'block' }} />
          </>}
    </span>
  )
}

function Lines({ r }: { r: M3Result }) {
  // Линии выводятся сверху вниз — Л6 первой, как в гексаграмме.
  return (
    <div style={{ margin: '16px 0' }}>
      {[6, 5, 4, 3, 2, 1].map(n => {
        const yang = r.symbols[n - 1] === 'A'
        const state = r.mobility[String(n)]
        return (
          <div key={n} style={S.lineRow}>
            <LineGlyph yang={yang} moving={Boolean(state)} />
            <span style={{ flex: 1 }}>Л{n} · {LINE_TITLES[n]}</span>
            <span style={{ flex: '0 0 44px', textAlign: 'right', color: C.muted }}>
              {r.scores[`l${n}`]?.toFixed(2)}
            </span>
            <span style={{
              flex: '0 0 190px', fontSize: 12,
              color: state ? C.red : C.muted,
            }}>
              {state ? MOBILITY_LABELS[state] : yang ? 'Ян' : 'Инь'}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function M3ReportPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = String(params?.id || '')

  const [report, setReport] = useState<M3Report | null>(null)
  const [steps, setSteps] = useState<M3ChecklistStep[]>([])
  const [decided, setDecided] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const [rep, ch] = await Promise.all([getReport(id), getChecklist(id)])
    setReport(rep)
    setSteps(ch)
    // Решение уже принято, если шаги разложены больше чем в одну волну.
    setDecided(new Set(ch.map(s => s.wave)).size > 1)
  }, [id])

  useEffect(() => {
    if (!id) return
    load().catch((e: any) => setLoadError(
      e?.status === 404 ? 'Отчёт не найден.'
        : e?.status === 400 ? 'Портфель ещё не рассчитан.'
        : e?.message || 'Не удалось загрузить отчёт.',
    ))
  }, [id, load])

  const shares = useMemo(() => {
    const out: Record<string, number | null> = {}
    for (const o of report?.portfolio.objects ?? []) out[o.id] = o.revenue_share
    return out
  }, [report])

  const objectById = useMemo(
    () => Object.fromEntries((report?.portfolio.objects ?? []).map(o => [o.id, o])),
    [report],
  )

  async function handleToggle(stepId: string, done: boolean) {
    const updated = await toggleChecklistStep(id, stepId, done)
    setSteps(prev => prev.map(s => (s.id === stepId ? updated : s)))
  }

  async function handleDecide(body: M3TradeoffIn) {
    await postTradeoff(id, body)
    setSteps(await getChecklist(id))
    setDecided(true)
  }

  if (loadError) return (
    <div style={S.page}><div style={S.stage}>
      <p style={S.warn}>{loadError}</p>
      <button style={S.btnGhost} onClick={() => router.push('/m3')}>← К портфелям</button>
    </div></div>
  )

  if (!report) return (
    <div style={S.page}><div style={S.stage}>
      <p style={{ color: C.muted }}>Загрузка…</p>
    </div></div>
  )

  const { portfolio, summary, objects, investment_order, execution_order, disclaimers } = report
  const results = objects.map(o => o.result)
  const byId = Object.fromEntries(results.map(r => [r.object_id, r]))

  return (
    <div style={S.page}><div style={S.stage}>
      <header style={S.header}>
        <div style={S.brand}>64DAO · Метод 03 · Матрица силы</div>
        <h1 style={S.h1}>Распределение ресурсов между направлениями</h1>
        <div style={S.sub}>{portfolio.title || 'Портфель без названия'}</div>
        <div style={S.meta}>
          <span>Направлений: {summary.objects}</span>
          <span>Сумма позиций: {summary.sum_positions} из {summary.sum_positions_max}</span>
          <span>Подвижных линий: {summary.turbulence}</span>
          <span>Δ: {summary.delta > 0 ? `+${summary.delta}` : summary.delta}</span>
          {portfolio.calculated_at && (
            <span>Рассчитано: {new Date(portfolio.calculated_at).toLocaleDateString('ru-RU')}</span>
          )}
        </div>
      </header>

      {summary.verdicts_held && (
        <div style={{ ...S.banner, ...S.bannerWarn }}>
          <span style={S.bannerTitle}>Вердикты аллокации удержаны</span>
          Сработал портфельный флаг качества данных: {summary.flags
            .map(f => PORTFOLIO_FLAG_LABELS[f] ?? f).join('; ')}.
          Диагноз и маршруты ниже приведены, распределение ресурса — нет.
        </div>
      )}

      <h2 style={S.h2}><span style={S.num}>00</span>Исходные данные</h2>
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>Направление</th>
            <th style={{ ...S.th, ...S.tdNum }}>Выручка</th>
            <th style={{ ...S.th, ...S.tdNum }}>Динамика</th>
            <th style={{ ...S.th, ...S.tdNum }}>Доля</th>
            <th style={S.th}>Прибыльность</th>
          </tr>
        </thead>
        <tbody>
          {portfolio.objects.map(o => (
            <tr key={o.id}>
              <td style={S.td}>{o.position} · {o.name}</td>
              <td style={{ ...S.td, ...S.tdNum }}>{o.revenue ?? '—'}</td>
              <td style={{ ...S.td, ...S.tdNum }}>
                {o.revenue_dynamics === null ? '—'
                  : `${o.revenue_dynamics > 0 ? '+' : ''}${o.revenue_dynamics}%`}
              </td>
              <td style={{ ...S.td, ...S.tdNum }}>
                {o.revenue_share === null ? '—' : `${o.revenue_share}%`}
              </td>
              <td style={S.td}>{PROFITABILITY_LABELS[o.profitability]}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={S.h2}><span style={S.num}>01</span>Карта портфеля</h2>
      <PortfolioMap results={results} shares={shares} />
      <p style={S.muted}>
        Ячейку задаёт число сильных линий в триграмме, положение внутри ячейки —
        взвешенная координата по отраслевому пресету. Занято разных ячеек:{' '}
        {summary.distinct_cells} из 9.
        {summary.spearman !== null && (
          ` Согласие расчёта с вашим порядком приоритета: ${summary.spearman.toFixed(2)}.`
        )}
      </p>

      <h2 style={S.h2}>
        <span style={S.num}>02</span>Разбор направлений — в порядке приоритета вложения
      </h2>

      {objects.map(({ result: r, narrative }) => (
        <section key={r.object_id} style={S.card}>
          <h3 style={S.h3}>{r.position} · {r.name}</h3>
          <div style={S.cellline}>
            {r.cell_label} · приоритет вложения {r.v_rank} · очередь исполнения {r.z_rank}
          </div>

          <div style={S.hx}>
            <span><span style={S.code}>{r.symbols}</span> · № {r.current_hex}</span>
            <span style={{ color: C.muted, fontSize: 12.5 }}>{r.current_name}</span>
            {r.target_hex !== null && (
              <span style={{ color: C.blue }}>
                цель № {r.target_hex} · инверсия Л{r.target_lines.join(', Л')}
              </span>
            )}
            {r.risk_hex !== null && (
              <span style={{ color: C.red }}>
                эрозия № {r.risk_hex} · инверсия Л{r.risk_lines.join(', Л')}
              </span>
            )}
            {r.target_hex === null && r.risk_hex === null && (
              <span style={{ color: C.muted }}>подвижных линий нет — ограничение стабильно</span>
            )}
          </div>

          <Lines r={r} />

          {narrative.map(b => (
            <div key={`${b.kind}-${b.key}`}>
              <h4 style={S.h4}>{b.title}</h4>
              <p style={{ margin: '10px 0' }}>{b.body}</p>
              {b.mistake && (
                <div style={S.banner}>
                  <span style={S.bannerTitle}>Типичная ошибка</span>
                  {b.mistake}
                </div>
              )}
            </div>
          ))}

          {r.flags.length > 0 && (
            <div style={{ ...S.banner, ...S.bannerWarn }}>
              <span style={S.bannerTitle}>Оговорки по данным направления</span>
              {r.flags.map(f => FLAG_LABELS[f] ?? f).join('; ')}.
            </div>
          )}
        </section>
      ))}

      <h2 style={S.h2}><span style={S.num}>03</span>Портфельные ограничения</h2>
      <p>
        Сумма позиций {summary.sum_positions} из {summary.sum_positions_max}:
        столько сильных линий во всём портфеле. Подвижных линий {summary.turbulence} —
        это энергия перехода, доступная сейчас. Дельта {summary.delta > 0 ? `+${summary.delta}` : summary.delta}{' '}
        — ожидаемое изменение зрелости, если проработать назревшее и не потерять достигнутое.
      </p>
      <p style={S.muted}>
        Правило такта: не более двух направлений в активной трансформации
        одновременно. Ограничение управленческого ресурса, а не денег —
        запустив всё сразу, вы не закончите ничего.
      </p>
      {summary.flags.length > 0 && (
        <div style={{ ...S.banner, ...S.bannerWarn }}>
          <span style={S.bannerTitle}>Портфельные флаги</span>
          {summary.flags.map(f => PORTFOLIO_FLAG_LABELS[f] ?? f).join('; ')}.
        </div>
      )}

      <h2 style={S.h2}><span style={S.num}>04</span>Решение о распределении ресурсов</h2>
      <p>
        Два списка отвечают на разные вопросы. Приоритет вложения — куда
        осмысленно направить деньги на рост. Очередь исполнения — что нельзя
        потерять и что горит. Их расхождение не дефект: направление с крупной
        долей выручки надо защищать первым, но вкладывать в него — не обязательно.
      </p>

      <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 300px' }}>
          <h4 style={S.h4}>Приоритет вложения — ранг V</h4>
          <ol style={{ paddingLeft: 20 }}>
            {investment_order.map(oid => (
              <li key={oid} style={{ margin: '5px 0' }}>
                {objectById[oid]?.name ?? '—'}
                <span style={{ color: C.muted, fontSize: 12.5 }}>
                  {' '}· V {byId[oid]?.v_index.toFixed(4)}
                </span>
              </li>
            ))}
          </ol>
        </div>
        <div style={{ flex: '1 1 300px' }}>
          <h4 style={S.h4}>Очередь исполнения — ранг Z</h4>
          <ol style={{ paddingLeft: 20 }}>
            {execution_order.map(oid => (
              <li key={oid} style={{ margin: '5px 0' }}>
                {objectById[oid]?.name ?? '—'}
                <span style={{ color: C.muted, fontSize: 12.5 }}>
                  {' '}· Z {byId[oid]?.z_index.toFixed(4)}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {investment_order[investment_order.length - 1] === execution_order[0] && (
        <div style={S.banner}>
          <span style={S.bannerTitle}>Расхождение списков</span>
          Направление «{objectById[execution_order[0]]?.name}» последнее по приоритету
          вложения и первое по очереди исполнения. Это денежная корова: защищать
          в первую очередь, вкладывать в рост — в последнюю.
        </div>
      )}

      {summary.verdicts_held && (
        <div style={{ ...S.banner, ...S.bannerWarn }}>
          <span style={S.bannerTitle}>Вердикты удержаны</span>
          Списки приведены как расчёт, но не как рекомендация: качество данных
          не позволяет опереться на них при распределении ресурса.
        </div>
      )}

      <M3Checklist
        steps={steps}
        objects={portfolio.objects}
        investmentOrder={investment_order}
        executionOrder={execution_order}
        results={results}
        decided={decided}
        onToggle={handleToggle}
        onDecide={handleDecide}
      />

      <h2 style={S.h2}>Оговорки по данным</h2>
      <ul style={{ paddingLeft: 20 }}>
        {disclaimers.map((d, i) => (
          <li key={i} style={{ margin: '7px 0', fontSize: 13.5 }}>{d}</li>
        ))}
      </ul>

      <div style={{ marginTop: 40, display: 'flex', gap: 12 }}>
        <button style={S.btnGhost} onClick={() => router.push('/m3')}>← К портфелям</button>
      </div>
    </div></div>
  )
}

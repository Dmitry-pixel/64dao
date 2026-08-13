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
  // Оглавление: стили повторяют отчёт Метода 1, чтобы два отчёта
  // не разошлись видом. Колонка липкая — отчёт длинный.
  shell: { maxWidth: 1180, margin: '0 auto', padding: '0 24px', display: 'grid',
    gridTemplateColumns: '200px 1fr', gap: 32, alignItems: 'start' } as React.CSSProperties,
  toc: { position: 'sticky', top: 24, alignSelf: 'flex-start', paddingTop: 48 } as React.CSSProperties,
  tocTitle: { fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 1, color: 'rgba(26,37,64,0.4)',
    textTransform: 'uppercase', marginBottom: 12, fontWeight: 600 } as React.CSSProperties,
  tocLink: { display: 'block', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.5)',
    padding: '6px 10px', borderRadius: 4, cursor: 'pointer', marginBottom: 2,
    textDecoration: 'none' } as React.CSSProperties,
  tocLinkOn: { background: 'rgba(26,37,64,0.06)', color: '#1a2540' } as React.CSSProperties,
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
  // Плашка как в отчёте Метода 1, но на калибр меньше: здесь заголовок
  // 13px капителью, и плашка в полный размер перевешивает название.
  num: { display: 'inline-block', fontFamily: 'sans-serif', fontSize: 11,
    fontWeight: 500, color: '#fff', background: C.red, borderRadius: 3,
    padding: '3px 7px', letterSpacing: 1, marginRight: 10 } as React.CSSProperties,
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
  traj: {
    fontSize: 12.5, color: C.muted, lineHeight: 1.8, margin: '10px 0 0',
  } as React.CSSProperties,
  verdict: {
    borderTop: `1px solid ${C.line}`, marginTop: 18, paddingTop: 13, fontSize: 14,
  } as React.CSSProperties,
  reason: { color: C.muted, fontSize: 12.5 } as React.CSSProperties,
  muted: { color: C.muted, fontSize: 12.5, lineHeight: 1.65 } as React.CSSProperties,
}

const FLAG_LABELS: Record<string, string> = {
  BORDERLINE_LINE: 'пограничный балл линии',
  NEAR_OLD_YANG: 'балл подходит к границе перегрева',
  NEAR_OLD_YIN: 'балл подходит к границе назревшей слабости',
  // Формулировка повторяет m3_pdf.FLAG_LABELS — при правке менять обе.
  VETO_UNPROFITABLE: 'вето по убыточности: символ линии 1 понижен до Инь независимо от балла',
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

/**
 * Число с десятичной запятой.
 *
 * toFixed даёт точку, а отчёт русскоязычный и печатается рядом с PDF, где
 * запятая уже стоит. Разнобой в одном документе читается как опечатка.
 */
function num(value: number | null | undefined, digits = 2, dash = '—'): string {
  if (value === null || value === undefined || Number.isNaN(value)) return dash
  return value.toFixed(digits).replace('.', ',')
}

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
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

/**
 * Вывод ячейки под таблицей линий. Печатается всегда, а не только когда
 * расходится с баллами: иначе клиент не поймёт, почему у одного направления
 * пояснение есть, а у другого нет. Заодно делает отраслевой пресет видимым.
 */
function CellBreakdown({ r }: { r: M3Result }) {
  const b = r.cell_breakdown
  if (!b) return null
  return (
    <div style={{ margin: '-8px 0 16px', fontSize: 12, color: C.muted }}>
      {(['strength', 'attract'] as const).map(axis => (
        <div key={axis} style={{ margin: '2px 0' }}>{b[axis].text}</div>
      ))}
    </div>
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
              {num(r.scores[`l${n}`])}
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

// Разделы отчёта. Ярлыки короче заголовков намеренно: в колонке 200px
// полное «Разбор направлений — в порядке приоритета вложения» переносится
// на три строки и оглавление перестаёт читаться списком.
const M3_SECTIONS = [
  { label: '00 — Исходные данные', anchor: 'm3-00' },
  { label: '01 — Карта портфеля', anchor: 'm3-01' },
  { label: '02 — Разбор направлений', anchor: 'm3-02' },
  { label: '03 — Портфельные ограничения', anchor: 'm3-03' },
  { label: '04 — Решение о распределении', anchor: 'm3-04' },
  { label: 'Оговорки по данным', anchor: 'm3-notes' },
]

export default function M3ReportPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = String(params?.id || '')

  const [report, setReport] = useState<M3Report | null>(null)
  const [steps, setSteps] = useState<M3ChecklistStep[]>([])
  const [decided, setDecided] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState(0)

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
      <div style={{ display: 'flex', gap: 12 }}>
        <button style={S.btnGhost} onClick={() => router.push('/m3')}>← К портфелям</button>
        <button style={S.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
      </div>
    </div></div>
  )

  if (!report) return (
    <div style={S.page}><div style={S.stage}>
      <p style={{ color: C.muted }}>Загрузка…</p>
    </div></div>
  )

  const {
    portfolio, summary, objects, investment_order, execution_order,
    analysis, disclaimers,
  } = report
  const results = objects.map(o => o.result)
  const byId = Object.fromEntries(results.map(r => [r.object_id, r]))
  // Цепочка та же, что в company_name_for на сервере: у портфелей,
  // созданных до миграции 024, названия компании нет — берём название
  // портфеля, иначе заголовок выданного ранее отчёта стал бы «Компания».
  const company = portfolio.company_name || portfolio.title || 'Компания'

  return (
    <div style={S.page}><div style={S.shell}>
      <aside style={S.toc}>
        <h4 style={S.tocTitle}>Содержание</h4>
        {M3_SECTIONS.map((s, i) => (
          <a key={s.anchor} href={`#${s.anchor}`}
             style={{ ...S.tocLink, ...(i === activeSection ? S.tocLinkOn : {}) }}
             onClick={() => setActiveSection(i)}>{s.label}</a>
        ))}
      </aside>
      <div style={S.stage}>
      <header style={S.header}>
        <div style={S.brand}>64DAO · Метод 3</div>
        <h1 style={S.h1}>Матрица силы · {company}</h1>
        {portfolio.title && portfolio.title !== company && (
          <div style={S.sub}>{portfolio.title}</div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: -8 }}>
          <a
            href={`/api/reports/m3/${portfolio.id}/download`}
            target="_blank"
            rel="noreferrer"
            style={{
              fontFamily: 'sans-serif', fontSize: 13, color: '#fff',
              background: '#1a2540', borderRadius: 6, padding: '9px 18px',
              textDecoration: 'none',
            }}
          >Скачать PDF</a>
        </div>
        <div style={S.meta}>
          <span>Направлений: {summary.objects}</span>
          <span>Сумма позиций: {summary.sum_positions} из {summary.sum_positions_max}</span>
          <span>Подвижных линий: {summary.turbulence}</span>
          <span>Δ: {signed(summary.delta)}</span>
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

      <h2 id="m3-00" style={{ ...S.h2, scrollMarginTop: 20 }}><span style={S.num}>00</span>Исходные данные</h2>
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>Направление</th>
            <th style={{ ...S.th, ...S.tdNum }}>Выручка</th>
            <th style={{ ...S.th, ...S.tdNum }}>Динамика</th>
            <th style={{ ...S.th, ...S.tdNum }}>Доля</th>
            <th style={S.th}>Прибыльность</th>
            <th style={S.th}>Рынок</th>
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
              <td style={S.td}>{byId[o.id]?.market_label ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 id="m3-01" style={{ ...S.h2, scrollMarginTop: 20 }}><span style={S.num}>01</span>Карта портфеля</h2>
      <PortfolioMap results={results} shares={shares} />
      <p style={S.muted}>
        Ячейку задаёт сумма отраслевых весов сильных линий, положение внутри ячейки —
        взвешенная координата по отраслевому пресету. Занято разных ячеек:{' '}
        {summary.distinct_cells} из 9.
        {summary.spearman !== null && (
          ` Согласие расчёта с вашим порядком приоритета: ${num(summary.spearman)}.`
        )}
      </p>

      {/*
        Таблица отвечает на вопрос, который по кругам не прочитать: какая у
        направления конфигурация линий. Две точки в одной ячейке могут иметь
        противоположные вердикты.
      */}
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>№</th>
            <th style={S.th}>Направление</th>
            <th style={S.th}>Ячейка</th>
            <th style={S.th}>Код</th>
            <th style={{ ...S.th, ...S.tdNum }}>Текущая</th>
            <th style={{ ...S.th, ...S.tdNum }}>Цель</th>
            <th style={{ ...S.th, ...S.tdNum }}>Риск</th>
            <th style={{ ...S.th, ...S.tdNum }}>Подв.</th>
          </tr>
        </thead>
        <tbody>
          {results.map(r => (
            <tr key={r.object_id}>
              <td style={S.td}>{r.position}</td>
              <td style={S.td}>{r.name}</td>
              <td style={S.td}>{r.cell_label}</td>
              <td style={{ ...S.td, ...S.code }}>{r.symbols}</td>
              <td style={{ ...S.td, ...S.tdNum }}>{r.current_hex}</td>
              <td style={{ ...S.td, ...S.tdNum, color: C.blue }}>
                {r.target_hex ?? '—'}
              </td>
              <td style={{ ...S.td, ...S.tdNum, color: C.red }}>
                {r.risk_hex ?? '—'}
              </td>
              <td style={{ ...S.td, ...S.tdNum }}>
                {Object.keys(r.mobility).length}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 id="m3-02" style={{ ...S.h2, scrollMarginTop: 20 }}>
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

          {(r.trajectory.target || r.trajectory.risk) && (
            <div style={S.traj}>
              {r.trajectory.target && (
                <div>
                  Целевое состояние: № {r.current_hex} → № {r.trajectory.target.to_hex},{' '}
                  {r.trajectory.target.phrase}.
                </div>
              )}
              {r.trajectory.risk && (
                <div>
                  Сценарий эрозии без закрепления: № {r.current_hex} →{' '}
                  № {r.trajectory.risk.to_hex}, {r.trajectory.risk.phrase}.
                </div>
              )}
            </div>
          )}

          <Lines r={r} />
          <CellBreakdown r={r} />

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

          {/* Вердикт замыкает разбор — как в PDF. Считает его сервер. */}
          <div style={S.verdict}>
            <b style={{ fontWeight: 400, color: C.red }}>{r.verdict.verdict}.</b>{' '}
            <span style={S.reason}>
              Зона матрицы: {r.verdict.zone_ru} ({r.verdict.zone_en}).{' '}
              {r.verdict.notes.join(' · ')}.
            </span>
          </div>
        </section>
      ))}

      <h2 id="m3-03" style={{ ...S.h2, scrollMarginTop: 20 }}><span style={S.num}>03</span>Портфельные ограничения</h2>
      <p>
        Раздел отвечает на вопрос, который нельзя задать, оценивая направления
        по отдельности: какая слабость повторяется и, значит, принадлежит
        компании, а не продукту.
      </p>

      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>Линия</th>
            <th style={S.th}>Фактор</th>
            <th style={{ ...S.th, ...S.tdNum }}>Инь из {summary.objects}</th>
            <th style={{ ...S.th, ...S.tdNum }}>Дельта линии</th>
            <th style={S.th}>Прочтение</th>
          </tr>
        </thead>
        <tbody>
          {analysis.yin_table.map(row => (
            <tr key={row.line}>
              <td style={S.td}>Л{row.line}</td>
              <td style={S.td}>{row.factor}</td>
              <td style={{ ...S.td, ...S.tdNum }}>{row.yin}</td>
              <td style={{ ...S.td, ...S.tdNum }}>{signed(row.delta_line)}</td>
              <td style={S.td}>{row.reading}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {analysis.constraints.length > 0 ? analysis.constraints.map((c, i) => (
        <div key={c.line} style={S.card}>
          <span style={S.bannerTitle}>
            Ограничение {i + 1} · {c.kind_title}
          </span>
          <p style={{ margin: 0 }}>{c.body}</p>
        </div>
      )) : (
        <p style={S.muted}>
          Ни одна слабость не повторяется у большинства направлений: общего
          ограничения компании расчёт не фиксирует. Работать нужно
          по направлениям.
        </p>
      )}

      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>Показатель</th>
            <th style={{ ...S.th, ...S.tdNum }}>Значение</th>
            <th style={S.th}>Прочтение</th>
          </tr>
        </thead>
        <tbody>
          {analysis.metrics.map(m => (
            <tr key={m.name}>
              <td style={S.td}>{m.name}</td>
              <td style={{ ...S.td, ...S.tdNum }}>{m.value}</td>
              <td style={S.td}>{m.reading}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p style={S.muted}>{analysis.tact_note}</p>
      {summary.flags.length > 0 && (
        <div style={{ ...S.banner, ...S.bannerWarn }}>
          <span style={S.bannerTitle}>Портфельные флаги</span>
          {summary.flags.map(f => PORTFOLIO_FLAG_LABELS[f] ?? f).join('; ')}.
        </div>
      )}

      <h2 id="m3-04" style={{ ...S.h2, scrollMarginTop: 20 }}><span style={S.num}>04</span>Решение о распределении ресурсов</h2>
      <p>
        Два списка отвечают на разные вопросы. Приоритет вложения — куда
        осмысленно направить деньги на рост. Очередь исполнения — что нельзя
        потерять и что горит. Их расхождение не дефект: направление с крупной
        долей выручки надо защищать первым, но вкладывать в него — не обязательно.
      </p>

      {analysis.rank_comparison && (
        <>
          <h4 style={S.h4}>Ваш порядок против расчётного</h4>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>Направление</th>
                <th style={{ ...S.th, ...S.tdNum }}>Вы</th>
                <th style={{ ...S.th, ...S.tdNum }}>Расчёт</th>
                <th style={{ ...S.th, ...S.tdNum }}>Δ</th>
              </tr>
            </thead>
            <tbody>
              {analysis.rank_comparison.rows.map(r => (
                <tr key={r.position}>
                  <td style={S.td}>{r.position} · {r.name}</td>
                  <td style={{ ...S.td, ...S.tdNum }}>{r.owner_rank}</td>
                  <td style={{ ...S.td, ...S.tdNum }}>{r.v_rank}</td>
                  <td style={{ ...S.td, ...S.tdNum }}>
                    {r.gap === 0 ? '—' : (r.gap > 0 ? `+${r.gap}` : r.gap)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={S.muted}>{analysis.rank_comparison.reading}</p>
        </>
      )}

      <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 300px' }}>
          <h4 style={S.h4}>Приоритет вложения — ранг V</h4>
          <ol style={{ paddingLeft: 20 }}>
            {investment_order.map(oid => (
              <li key={oid} style={{ margin: '5px 0' }}>
                {objectById[oid]?.name ?? '—'}
                <span style={S.reason}>
                  {' '}· V {num(byId[oid]?.v_index, 4)}
                  {byId[oid] && ` · ${byId[oid].verdict.verdict.toLowerCase()}`}
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
                <span style={S.reason}>
                  {' '}· Z {num(byId[oid]?.z_index, 4)}
                  {byId[oid] && ` · ${byId[oid].execution_reason}`}
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

      <h2 id="m3-notes" style={{ ...S.h2, scrollMarginTop: 20 }}>Оговорки по данным</h2>
      <ul style={{ paddingLeft: 20 }}>
        {disclaimers.map((d, i) => (
          <li key={i} style={{ margin: '7px 0', fontSize: 13.5 }}>{d}</li>
        ))}
      </ul>

      <div style={{ marginTop: 40, display: 'flex', gap: 12 }}>
        <button style={S.btnGhost} onClick={() => router.push('/m3')}>← К портфелям</button>
        <button style={S.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
      </div>
    </div></div></div>
  )
}

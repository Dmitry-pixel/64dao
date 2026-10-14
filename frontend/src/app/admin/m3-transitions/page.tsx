'use client'
/**
 * Переходы Метода 3 между замерами — рабочий экран методолога.
 *
 * Тип перехода считается кодом (backend/app/m3_transition.py) по каждой паре
 * «прошлый замер → следующий» одной компании. Клиент его пока не видит:
 * тексты к типам пишутся по мере появления реальных повторов. Правила и
 * черновик текстов: claude/m3-transition-rules-draft.md в материалах проекта.
 */
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getM3Transitions, getMe, type M3TransitionPair, type M3TransitionDirection } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const OUTCOME_LABEL: Record<string, string> = { done: 'выполнено', partial: 'частично', not_done: 'не выполнено' }

const fmt = (iso: string) => new Date(iso).toLocaleDateString('ru-RU')
const lines = (xs: number[]) => (xs.length ? xs.join(', ') : '—')

// Символы с подсветкой значимо сменившихся (жирный) и пограничных (курсив) линий.
function Symbols({ s, changed, border }: { s: string; changed: number[]; border: number[] }) {
  return (
    <span style={{ fontFamily: 'monospace', fontSize: 13, letterSpacing: 1 }}>
      {s.split('').map((ch, i) => {
        const n = i + 1
        const style = changed.includes(n) ? { fontWeight: 700, color: '#c0392b' }
          : border.includes(n) ? { fontStyle: 'italic' as const, color: 'rgba(26,37,64,0.5)' } : {}
        return <span key={i} style={style}>{ch}</span>
      })}
    </span>
  )
}

function Row({ d }: { d: M3TransitionDirection }) {
  return (
    <tr>
      <td style={{ fontFamily: 'sans-serif', fontSize: 13 }}>{d.name}</td>
      <td style={{ fontFamily: 'sans-serif', fontSize: 13, whiteSpace: 'nowrap' }}>
        <b>{d.type}</b> · {d.type_title}
      </td>
      <td style={{ whiteSpace: 'nowrap' }}>
        <Symbols s={d.prev_symbols} changed={[]} border={[]} /> →{' '}
        <Symbols s={d.now_symbols} changed={d.changed} border={d.borderline} />
      </td>
      <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>{lines(d.changed)}</td>
      <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>{lines(d.borderline)}</td>
      <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>{d.scale} · {d.where} · {d.direction}</td>
      <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>{d.target}</td>
      <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>{d.risk}</td>
      <td style={{ fontFamily: 'sans-serif', fontSize: 12 }}>
        {d.intent.value}
        {d.intent.value !== 'нет данных' && (
          <span className="faint" style={{ display: 'block', fontSize: 11 }}>
            да: {lines(d.intent.met)} · нет: {lines(d.intent.missed)}
          </span>
        )}
      </td>
    </tr>
  )
}

function Pair({ p }: { p: M3TransitionPair }) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '20px 22px', marginBottom: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
        <div>
          <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 19, fontWeight: 400, margin: '0 0 4px' }}>
            {p.company_name || 'Без названия'}
          </h3>
          <span className="faint">{p.user_email}</span>
        </div>
        <div style={{ fontFamily: 'sans-serif', fontSize: 13, textAlign: 'right' }}>
          <Link href={`/report/m3/${p.previous.id}`}>{fmt(p.previous.calculated_at)}</Link>
          {' → '}
          <Link href={`/report/m3/${p.current.id}`}>{fmt(p.current.calculated_at)}</Link>
          <span className="faint" style={{ display: 'block', fontSize: 11 }}>
            {p.current.is_followup ? 'повтор по тарифу' : 'новая платная диагностика'}
          </span>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="tbl">
          <thead>
            <tr>
              <th>Направление</th><th>Тип</th><th>Символы</th><th>Сменились</th><th>Пограничные</th>
              <th>Масштаб · где · направление</th><th>Назревшее</th><th>Риск</th><th>Намерение</th>
            </tr>
          </thead>
          <tbody>{p.directions.map(d => <Row key={d.name} d={d} />)}</tbody>
        </table>
      </div>
      {(p.added.length > 0 || p.removed.length > 0) && (
        <p className="faint" style={{ marginTop: 10 }}>
          {p.added.length > 0 && <>Новые направления: {p.added.join(', ')}. </>}
          {p.removed.length > 0 && <>Убраны: {p.removed.join(', ')}.</>}
        </p>
      )}

      <div style={{ marginTop: 14 }}>
        <span className="label-red">Журнал решений после прошлого замера</span>
        {p.decisions.length === 0 ? (
          <p className="faint" style={{ marginTop: 6 }}>Клиент решений не записал.</p>
        ) : p.decisions.map(d => (
          <div key={d.id} style={{ fontFamily: 'sans-serif', fontSize: 13, margin: '8px 0', lineHeight: 1.5 }}>
            <b>{d.scenario}</b>
            {d.expected && <> · ждали: {d.expected}</>}
            {' · '}
            <span className="faint">итог: {d.outcome ? OUTCOME_LABEL[d.outcome] : 'не отмечен'}</span>
            {d.outcome_note && <span className="faint"> · {d.outcome_note}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AdminM3TransitionsPage() {
  const router = useRouter()
  const [items, setItems] = useState<M3TransitionPair[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getMe()
      .then(me => {
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        return getM3Transitions().then(r => setItems(r.items))
      })
      .catch(() => setError('Не удалось загрузить переходы'))
  }, [router])

  return (
    <>
      <AdminNav current="m3-transitions" />
      <div className="admin-shell">
        <AdminSide current="m3-transitions" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>
          <span className="label-red">Диагностики</span>
          <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>
            Переходы Метода 3
          </h1>
          <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: '0 0 24px', maxWidth: 760, lineHeight: 1.6 }}>
            Тип перехода каждого направления между двумя замерами одной компании. Клиент этого не видит:
            экран нужен, чтобы писать тексты к типам по реальным случаям. Жирным выделены значимо
            сменившиеся линии, курсивом пограничные (символ сменился, балл сдвинулся меньше чем на 0,5).
            Намерение берётся из шагов чек-листа, которые клиент отметил выполненными.
          </p>

          {error && <p style={{ color: 'var(--red)', fontFamily: 'sans-serif', fontSize: 13 }}>{error}</p>}
          {items === null && !error ? (
            <p className="faint">Загрузка…</p>
          ) : items && items.length === 0 ? (
            <div className="dash-empty">
              <h3>Повторных замеров пока нет</h3>
              <p>Пара появится, когда компания пройдёт Метод 3 второй раз.</p>
            </div>
          ) : items?.map(p => <Pair key={p.current.id} p={p} />)}
        </div>
      </div>
    </>
  )
}

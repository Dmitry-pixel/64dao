'use client'
import React from 'react'

type Q = { q: string; a: string; b: string }

function firstSentence(text: string, limit = 90): string {
  const t = (text || '').trim()
  if (!t) return ''
  const i = t.indexOf('. ')
  let head = i !== -1 ? t.slice(0, i + 1) : t
  if (head.length > limit) head = head.slice(0, limit).replace(/[ ,.;:]+$/, '') + '…'
  return head
}

export default function HexDiagram({ combo, questions, labels, scenario }: {
  combo: string
  questions: Q[]
  labels: [string, string][]
  scenario?: Record<string, any> | null
}) {
  const order = [5, 4, 3, 2, 1, 0]

  const line = (ch: string) =>
    ch === 'A'
      ? <div className="hxd-yang" />
      : <div className="hxd-yin"><span /><span /></div>

  const answer = (i: number) => {
    const ch = combo[i]
    const q = questions[i]
    if (!q || (ch !== 'A' && ch !== 'B')) return <em style={{ opacity: 0.4 }}>—</em>
    return ch === 'A' ? q.a : q.b
  }

  const param = (j: number) => {
    const short = firstSentence(String(scenario?.[labels[j][0]] || ''))
    return short || <em style={{ opacity: 0.4 }}>Не заполнено</em>
  }

  const ansCell = (i: number) => (
    <>
      <div className="hxd-k">Линия {i + 1} · Вопрос {i + 1}</div>
      <div className="hxd-q">{questions[i]?.q}</div>
      <div className="hxd-v">{answer(i)}</div>
    </>
  )

  const parCell = (i: number, j: number) => (
    <>
      <div className="hxd-k">Линия {i + 1} · {labels[j][1]}</div>
      <div className="hxd-v">{param(j)}</div>
    </>
  )

  return (
    <div className="hxd">
      <div className="hxd-d">
        <div className="hxd-hdr">
          <div className="a">Ответы диагностики</div>
          <div className="b" />
          <div className="c">Параметры стратагемы</div>
        </div>
        {order.map((i, j) => (
          <div className="hxd-row" key={i}>
            <div className="hxd-l">{ansCell(i)}</div>
            <div className="hxd-cl" />
            <div className="hxd-c">{line(combo[i])}</div>
            <div className="hxd-cr" />
            <div className="hxd-r">{parCell(i, j)}</div>
          </div>
        ))}
        <div className="hxd-cap">линия 1 — нижняя</div>
      </div>

      <div className="hxd-m">
        <div className="hxd-mcap">Ответы диагностики</div>
        <ul className="hxd-list">
          {order.map(i => <li key={i}>{ansCell(i)}</li>)}
        </ul>
        <div className="hxd-mhex">
          {order.map(i => (
            <div className="hxd-mrow" key={i}>
              <div className="hxd-mnum">{i + 1}</div>
              {line(combo[i])}
            </div>
          ))}
          <div className="hxd-cap">линия 1 — нижняя</div>
        </div>
        <div className="hxd-mcap">Параметры стратагемы</div>
        <ul className="hxd-list">
          {order.map((i, j) => <li key={i}>{parCell(i, j)}</li>)}
        </ul>
      </div>
    </div>
  )
}

export function StratagemaTable({ labels, scenario }: {
  labels: [string, string][]
  scenario?: Record<string, any> | null
}) {
  return (
    <div className="strt">
      <div className="strt-cap">Сценарий стратагемы</div>
      <p className="strt-note">Полные формулировки параметров, кратко показанных рядом с гексаграммой.</p>
      <table className="strt-tbl"><tbody>
        {labels.map(([key, label], j) => (
          <tr key={key}>
            <th>
              <span className="strt-line">Линия {6 - j}</span>
              <span className="strt-name">{label}</span>
            </th>
            <td>{scenario?.[key] || <em style={{ opacity: 0.4 }}>Не заполнено</em>}</td>
          </tr>
        ))}
      </tbody></table>
    </div>
  )
}

export function HexLines({ combo }: { combo: string }) {
  return (
    <div className="hxs">
      {[5, 4, 3, 2, 1, 0].map(i => (
        <div className="hxs-row" key={i}>
          {combo[i] === 'A'
            ? <div className="hxs-yang" />
            : <div className="hxs-yin"><span /><span /></div>}
        </div>
      ))}
    </div>
  )
}

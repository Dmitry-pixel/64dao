'use client'

import { useMemo } from 'react'

import type { M3Result } from '@/lib/m3'

export type PortfolioMapProps = {
  results: M3Result[]
  /**
   * Доля направления в выручке: object_id -> проценты. Отдельным параметром,
   * а не полем результата: доля — это якорь портфеля, а не величина расчёта,
   * и в снимке m3_results её нет.
   */
  shares: Record<string, number | null>
  width?: number
}

/**
 * Карта портфеля: матрица 3×3 GE/McKinsey.
 *
 * Ячейку задаёт число Ян в триграмме, а НЕ координата: 3 Ян — высокая,
 * 2 — средняя, 0–1 — низкая. Координата ставит точку внутри уже выбранной
 * ячейки. Эти две величины могут расходиться — направление с координатой
 * привлекательности 2,25 может стоять в нижнем ряду, если в верхней триграмме
 * один Ян. Рисовать по одной координате значило бы спорить с подписью зоны.
 *
 * Внутри ячейки точка кладётся в центральные 60%: у краёв круги наезжали бы
 * на границы соседних ячеек, и принадлежность зоне читалась бы неверно.
 */

const PAD_L = 70
const PAD_T = 20
const GRID = 270
const CELL = GRID / 3
const VB_W = 400
const VB_H = 330

const C = {
  paper: '#f4f2ec',
  line: '#cfc9bc',
  dark: '#1a2540',
  muted: '#6b6559',
  blue: '#1e3a8a',
  red: '#c0392b',
}

// Строка — привлекательность рынка. Индекс 0 — нижний ряд, «низкая».
const ROW_INDEX: Record<string, number> = { low: 0, mid: 1, high: 2 }

// Колонка — конкурентная сила. Ось направлена как в матрице GE/McKinsey:
// СИЛЬНАЯ СЛЕВА, слабая справа. Поэтому «Инвестировать» приходится на левый
// верхний угол, а «Избегать / выходить» — на правый нижний, и клиент,
// видевший матрицу раньше, читает картинку без переучивания.
const COL_INDEX: Record<string, number> = { high: 0, mid: 1, low: 2 }

// Знак горизонтали: рост конкурентной силы идёт влево.
const X_SIGN = -1

/**
 * Позиция внутри ячейки: 0,2 … 0,8 от её ширины по координате 1…4.
 *
 * reverse нужен горизонтали. Ось силы направлена вправо-налево, и без
 * зеркала направление с силой 4,00 внутри сильной колонки встало бы у её
 * правого края — то есть ближе к средней колонке, а не дальше от неё.
 */
function inCell(index: number, coord: number, reverse = false): number {
  let f = Math.min(1, Math.max(0, (coord - 1) / 3))
  if (reverse) f = 1 - f
  return index * CELL + CELL * (0.2 + 0.6 * f)
}

/**
 * Радиус по доле выручки. Площадь, а не радиус, пропорциональна доле: глаз
 * сравнивает площади, и линейный радиус преувеличил бы крупные направления
 * втрое. Пол в 9 пикселей — иначе доля 3% превращается в точку.
 */
function radius(share: number | null | undefined): number {
  const s = Math.min(100, Math.max(0, share ?? 0))
  return Math.round(9 + Math.sqrt(s / 100) * 22)
}


/**
 * Раскладка кругов. Координата ставит точку внутри ячейки, но два направления
 * одной ячейки с близкими координатами наезжают друг на друга — на контрольном
 * кейсе расстояние между центрами выходило 10 при сумме радиусов 36.
 *
 * Поэтому после координатной расстановки идёт проход раздвигания: пары
 * отталкиваются вдоль линии центров, затем каждый круг зажимается в границы
 * СВОЕЙ ячейки. Ячейка важнее точной позиции — она несёт зону, а координата
 * внутри неё уточняющая. Проход детерминирован: порядок обхода фиксирован
 * порядком направлений, одинаковый расчёт даёт одинаковую картинку.
 */
type Placed = { x: number; y: number; r: number; col: number; row: number }

function layout(results: M3Result[], shares: Record<string, number | null>) {
  const pts = new Map<string, Placed>()
  for (const r of results) {
    // Неизвестная сила трактуется как слабая — крайняя правая колонка.
    const col = COL_INDEX[r.cell_strength] ?? 2
    const row = ROW_INDEX[r.cell_attract] ?? 0
    pts.set(r.object_id, {
      x: PAD_L + inCell(col, r.coord_strength, true),
      y: PAD_T + GRID - inCell(row, r.coord_attract),
      r: radius(shares[r.object_id] ?? null),
      col, row,
    })
  }

  const ids = results.map(r => r.object_id)
  for (let pass = 0; pass < 60; pass++) {
    let moved = false
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const A = pts.get(ids[i])!
        const B = pts.get(ids[j])!
        const dx = B.x - A.x
        const dy = B.y - A.y
        // Полностью совпавшие координаты дают нулевой вектор отталкивания,
        // и круги остались бы друг на друге: два направления с одинаковыми
        // баллами читались бы как одно. При шкале в два-три пункта совпадение
        // вероятно, поэтому расталкиваем по углу от порядкового номера пары —
        // правило детерминированное, картинка воспроизводима.
        let d = Math.sqrt(dx * dx + dy * dy)
        let ux: number
        let uy: number
        if (d < 1e-9) {
          const angle = 2 * Math.PI * j / ids.length
          ux = Math.cos(angle); uy = Math.sin(angle); d = 0.01
        } else {
          ux = dx / d; uy = dy / d
        }
        const need = A.r + B.r + 4
        if (d < need) {
          const push = (need - d) / 2
          A.x -= ux * push; A.y -= uy * push
          B.x += ux * push; B.y += uy * push
          moved = true
        }
      }
    }
    for (const id of ids) {
      const P = pts.get(id)!
      const x0 = PAD_L + P.col * CELL + P.r + 2
      const x1 = PAD_L + (P.col + 1) * CELL - P.r - 2
      const y1 = PAD_T + GRID - P.row * CELL - P.r - 2
      const y0 = PAD_T + GRID - (P.row + 1) * CELL + P.r + 2
      P.x = Math.min(Math.max(P.x, Math.min(x0, x1)), Math.max(x0, x1))
      P.y = Math.min(Math.max(P.y, Math.min(y0, y1)), Math.max(y0, y1))
    }
    if (!moved) break
  }
  return pts
}

/** Вектор от круга: направление смещения по матрице, а не точка прибытия. */
function vector(p: Placed, lines: number[], kind: 'target' | 'risk') {
  if (!lines.length) return null
  const gap = p.r + 6
  const len = 42
  // Целевая — проработка назревшего, движение к росту. Рисковая — эрозия,
  // движение к падению. По вертикали рост — вверх, по горизонтали — ВЛЕВО:
  // ось силы развёрнута под GE/McKinsey, отсюда X_SIGN.
  const dir = kind === 'target' ? 1 : -1
  // Линии 1–3 — конкурентная сила (горизонталь), 4–6 — привлекательность
  // (вертикаль). Ведём по той оси, где подвижных линий больше.
  const horizontal = lines.filter(n => n <= 3).length
  const alongX = horizontal >= lines.length - horizontal
  let v
  if (alongX) {
    const dx = dir * X_SIGN
    const from = p.x + dx * gap
    v = { x1: from, y1: p.y, x2: from + dx * len, y2: p.y }
  } else {
    const from = p.y - dir * gap
    v = { x1: p.x, y1: from, x2: p.x, y2: from - dir * len }
  }
  return clipToGrid(v)
}

/**
 * Стрелка обрезается по рамке матрицы.
 *
 * Длина вектора фиксированная, а зажимается только круг, поэтому у направления
 * в крайней ячейке стрелка уезжала за сетку и висела в пустоте.
 *
 * Если после обрезки осталось меньше VECTOR_MIN, стрелку не рисуем вовсе:
 * огрызок в три пикселя направления не показывает, а цель и риск в отчёте
 * всё равно названы номерами гексаграмм в таблице под картой.
 */
const VECTOR_MIN = 10

function clipToGrid(v: { x1: number; y1: number; x2: number; y2: number }) {
  const cx = (n: number) => Math.min(Math.max(n, PAD_L), PAD_L + GRID)
  const cy = (n: number) => Math.min(Math.max(n, PAD_T), PAD_T + GRID)
  const c = { x1: cx(v.x1), y1: cy(v.y1), x2: cx(v.x2), y2: cy(v.y2) }
  if (Math.hypot(c.x2 - c.x1, c.y2 - c.y1) < VECTOR_MIN) return null
  return c
}


export default function PortfolioMap({ results, shares, width = 400 }: PortfolioMapProps) {
  const placed = useMemo(() => layout(results, shares), [results, shares])
  const hasTarget = results.some(r => r.target_lines.length > 0)
  const hasRisk = results.some(r => r.risk_lines.length > 0)

  const label = results
    .map(r => `${r.position}. ${r.name}: ${r.cell_label}`)
    .join('; ')

  return (
    <figure style={{ margin: '18px 0' }}>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        width={width}
        style={{ maxWidth: '100%', height: 'auto' }}
        role="img"
        aria-label={`Матрица три на три, направлений: ${results.length}. ${label}`}
      >
        <defs>
          <marker id="m3-up" viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0 0 L10 5 L0 10 z" fill={C.blue} />
          </marker>
          <marker id="m3-dn" viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0 0 L10 5 L0 10 z" fill={C.red} />
          </marker>
        </defs>

        <rect x={PAD_L} y={PAD_T} width={GRID} height={GRID} fill={C.paper} stroke={C.line} />
        {[1, 2].map(i => (
          <line key={`v${i}`} x1={PAD_L + i * CELL} y1={PAD_T}
                x2={PAD_L + i * CELL} y2={PAD_T + GRID} stroke={C.line} />
        ))}
        {[1, 2].map(i => (
          <line key={`h${i}`} x1={PAD_L} y1={PAD_T + i * CELL}
                x2={PAD_L + GRID} y2={PAD_T + i * CELL} stroke={C.line} />
        ))}

        <text x={PAD_L - 8} y={68} fontSize="11" textAnchor="end" fill={C.muted}>Выс.</text>
        <text x={PAD_L - 8} y={158} fontSize="11" textAnchor="end" fill={C.muted}>Сред.</text>
        <text x={PAD_L - 8} y={248} fontSize="11" textAnchor="end" fill={C.muted}>Низ.</text>
        <text x={PAD_L} y={13} fontSize="11" fill={C.muted}>Привлекательность рынка</text>
        <text x={115} y={306} fontSize="11" textAnchor="middle" fill={C.muted}>Сильная</text>
        <text x={205} y={306} fontSize="11" textAnchor="middle" fill={C.muted}>Средняя</text>
        <text x={295} y={306} fontSize="11" textAnchor="middle" fill={C.muted}>Слабая</text>
        <text x={205} y={324} fontSize="11" textAnchor="middle" fill={C.muted}>Конкурентоспособность бизнеса</text>

        {results.map(r => {
          const p = placed.get(r.object_id)
          if (!p) return null
          const t = vector(p, r.target_lines, 'target')
          const k = vector(p, r.risk_lines, 'risk')
          const stable = !r.target_lines.length && !r.risk_lines.length
          return (
            <g key={r.object_id}>
              {t && (
                <path d={`M ${t.x1} ${t.y1} L ${t.x2} ${t.y2}`}
                      stroke={C.blue} strokeWidth="2" markerEnd="url(#m3-up)" />
              )}
              {k && (
                <path d={`M ${k.x1} ${k.y1} L ${k.x2} ${k.y2}`}
                      stroke={C.red} strokeWidth="2" markerEnd="url(#m3-dn)" />
              )}
              <circle
                cx={p.x} cy={p.y} r={p.r}
                fill={C.paper} stroke={C.dark} strokeWidth="1.5"
                // Пунктир — направление без подвижных линий: «ограничение
                // стабильно», двигаться ему сейчас нечем.
                strokeDasharray={stable ? '3 2' : undefined}
              />
              <text x={p.x} y={p.y + 4} fontSize="10"
                    textAnchor="middle" fill={C.dark}>
                {r.position}
              </text>
            </g>
          )
        })}
      </svg>

      <figcaption style={{
        fontSize: 12, color: C.muted, lineHeight: 1.6, marginTop: 8,
        fontFamily: 'sans-serif',
      }}>
        Размер круга — доля направления в выручке (пропорциональна площадь, не радиус).
        {hasTarget && ' Синяя стрелка — целевое состояние: куда придёт направление, если проработать назревшее.'}
        {hasRisk && ' Красная — сценарий эрозии: куда сползёт, если не закрепить достигнутое.'}
        {results.some(r => !r.target_lines.length && !r.risk_lines.length) &&
          ' Пунктирный контур — подвижных линий нет, ограничение стабильно.'}
      </figcaption>
    </figure>
  )
}

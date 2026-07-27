'use client'
import { HEX_TUPLE } from '@/lib/hexagrams'

// SVG-гексаграмма: A = сплошная линия (янь), B = прерывистая (инь).
// Индекс 0 = нижняя линия, 5 = верхняя, порядок И Цзин снизу вверх.
// Геометрия синхронизирована с backend/app/pdf.py::_hexagram_svg.
// Вынесен из AdminNav.tsx: страница отчёта не должна тянуть админ-навигацию.

export function HexagramSVG({
  combo,
  size = 48,
  color = 'currentColor',
}: {
  combo: string
  size?: number
  color?: string
}) {
  if (!combo || combo.length !== 6) combo = 'AAAAAA'
  // lineH + gap должны давать totalH < size, иначе линии вылезают за viewBox
  // 6*lineH + 5*gap = totalH; при lineH=size*0.10, gap=size*0.06 → totalH=0.90*size ✓
  const lineH  = size * 0.10         // высота линии (янь)
  const gap    = size * 0.06         // промежуток между линиями
  const step   = lineH + gap
  const totalH = 6 * lineH + 5 * gap  // = 0.90 * size (всегда меньше size)
  const yOffset = (size - totalH) / 2
  const w  = size * 0.82
  const x0 = (size - w) / 2
  const brk = w * 0.22               // ширина разрыва в прерывистой линии (инь)

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      xmlns="http://www.w3.org/2000/svg"
      aria-label={HEX_TUPLE[combo]?.[1] ?? combo}
    >
      {[...combo].map((ch, i) => {
        // i=0 → нижняя линия → рисуем снизу вверх
        const y = yOffset + (5 - i) * step
        if (ch === 'A') {
          return <rect key={i} x={x0} y={y} width={w} height={lineH} fill={color} rx={lineH / 4} />
        }
        return (
          <g key={i}>
            <rect x={x0}              y={y} width={(w - brk) / 2} height={lineH} fill={color} rx={lineH / 4} />
            <rect x={x0 + (w + brk) / 2} y={y} width={(w - brk) / 2} height={lineH} fill={color} rx={lineH / 4} />
          </g>
        )
      })}
    </svg>
  )
}

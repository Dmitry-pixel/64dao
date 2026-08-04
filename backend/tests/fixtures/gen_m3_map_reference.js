// Генератор эталона раскладки карты портфеля.
//
// Зачем. Раскладка существует в двух экземплярах: PortfolioMap.tsx для веба
// и m3_map.py для PDF. Это единственная часть отчёта, которая может разойтись
// молча — расхождение в три пикселя глазом не видно. Эталон снимается
// прогоном настоящей логики фронта, а test_m3_map сверяет с ним питоновский
// порт.
//
// Когда перезапускать: после ЛЮБОЙ правки геометрии в PortfolioMap.tsx.
//   node backend/tests/fixtures/gen_m3_map_reference.js
// затем прогнать test_m3_map — упавшие тесты покажут, что порт отстал.
//
// Код ниже скопирован из PortfolioMap.tsx дословно; убраны React и типы.
// Править его руками нельзя — только переносить из компонента.

const PAD_L = 70, PAD_T = 20, GRID = 270, CELL = GRID / 3;
const ROW_INDEX = { low: 0, mid: 1, high: 2 };
const COL_INDEX = { high: 0, mid: 1, low: 2 };
const X_SIGN = -1;

function inCell(index, coord, reverse) {
  let f = Math.min(1, Math.max(0, (coord - 1) / 3));
  if (reverse) f = 1 - f;
  return index * CELL + CELL * (0.2 + 0.6 * f);
}

function radius(share) {
  const s = Math.min(100, Math.max(0, share ?? 0));
  return Math.round(9 + Math.sqrt(s / 100) * 22);
}

function layout(results, shares) {
  const pts = new Map();
  for (const r of results) {
    const col = COL_INDEX[r.cell_strength] ?? 2;
    const row = ROW_INDEX[r.cell_attract] ?? 0;
    pts.set(r.object_id, {
      x: PAD_L + inCell(col, r.coord_strength, true),
      y: PAD_T + GRID - inCell(row, r.coord_attract),
      r: radius(shares[r.object_id] ?? null),
      col, row,
    });
  }
  const ids = results.map(r => r.object_id);
  for (let pass = 0; pass < 60; pass++) {
    let moved = false;
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const A = pts.get(ids[i]), B = pts.get(ids[j]);
        const dx = B.x - A.x, dy = B.y - A.y;
        let d = Math.sqrt(dx * dx + dy * dy), ux, uy;
        if (d < 1e-9) {
          const angle = 2 * Math.PI * j / ids.length;
          ux = Math.cos(angle); uy = Math.sin(angle); d = 0.01;
        } else { ux = dx / d; uy = dy / d; }
        const need = A.r + B.r + 4;
        if (d < need) {
          const push = (need - d) / 2;
          A.x -= ux * push; A.y -= uy * push;
          B.x += ux * push; B.y += uy * push;
          moved = true;
        }
      }
    }
    for (const id of ids) {
      const P = pts.get(id);
      const x0 = PAD_L + P.col * CELL + P.r + 2;
      const x1 = PAD_L + (P.col + 1) * CELL - P.r - 2;
      const y1 = PAD_T + GRID - P.row * CELL - P.r - 2;
      const y0 = PAD_T + GRID - (P.row + 1) * CELL + P.r + 2;
      P.x = Math.min(Math.max(P.x, Math.min(x0, x1)), Math.max(x0, x1));
      P.y = Math.min(Math.max(P.y, Math.min(y0, y1)), Math.max(y0, y1));
    }
    if (!moved) break;
  }
  return pts;
}

function vector(p, lines, kind) {
  if (!lines.length) return null;
  const gap = p.r + 6, len = 42;
  const dir = kind === 'target' ? 1 : -1;
  const horizontal = lines.filter(n => n <= 3).length;
  const alongX = horizontal >= lines.length - horizontal;
  let v;
  if (alongX) {
    const dx = dir * X_SIGN;
    const from = p.x + dx * gap;
    v = { x1: from, y1: p.y, x2: from + dx * len, y2: p.y };
  } else {
    const from = p.y - dir * gap;
    v = { x1: p.x, y1: from, x2: p.x, y2: from - dir * len };
  }
  const cx = (n) => Math.min(Math.max(n, PAD_L), PAD_L + GRID);
  const cy = (n) => Math.min(Math.max(n, PAD_T), PAD_T + GRID);
  const c = { x1: cx(v.x1), y1: cy(v.y1), x2: cx(v.x2), y2: cy(v.y2) };
  if (Math.hypot(c.x2 - c.x1, c.y2 - c.y1) < 10) return null;
  return c;
}

const fs = require('fs');
const cases = JSON.parse(fs.readFileSync(__dirname + '/m3_map_cases.json', 'utf8'));
const out = {};
for (const [name, c] of Object.entries(cases)) {
  const pts = layout(c.results, c.shares);
  out[name] = c.results.map(r => {
    const p = pts.get(r.object_id);
    return {
      object_id: r.object_id,
      x: p.x, y: p.y, r: p.r, col: p.col, row: p.row,
      target: vector(p, r.target_lines, 'target'),
      risk: vector(p, r.risk_lines, 'risk'),
    };
  });
}
fs.writeFileSync(__dirname + '/m3_map_reference.json', JSON.stringify(out, null, 1));
console.log('cases:', Object.keys(out).join(', '));

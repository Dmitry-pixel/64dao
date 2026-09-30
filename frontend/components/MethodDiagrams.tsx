// Схемы Методов 3 и 4. Перенесены без изменений из прежней главной
// (app/page.tsx), теперь используются на странице /methods.

// ─── Алмазное колесо (Метод 4) ────────────────────────────────────────────────
// Оригинальная схема 64DAO: десять модулей, десятый (финансы) выделен как
// следствие остальных девяти. Баллов на схеме нет — она поясняет метод.
export function DiamondWheelSvg() {
  return (
    <svg viewBox="0 0 600 472" width="100%" role="img" aria-label="Алмазное колесо: десять управленческих модулей" style={{ display: 'block' }}>
      <g fill="none" stroke="rgba(26,37,64,0.22)" strokeWidth={1}>
        <path d="M 253.6 93.3 A 150 150 0 0 1 346.4 93.3 L 326.0 156.1 A 84 84 0 0 0 274.0 156.1 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 346.4 93.3 A 150 150 0 0 1 421.4 147.8 L 368.0 186.6 A 84 84 0 0 0 326.0 156.1 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 421.4 147.8 A 150 150 0 0 1 450.0 236.0 L 384.0 236.0 A 84 84 0 0 0 368.0 186.6 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 450.0 236.0 A 150 150 0 0 1 421.4 324.2 L 368.0 285.4 A 84 84 0 0 0 384.0 236.0 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 421.4 324.2 A 150 150 0 0 1 346.4 378.7 L 326.0 315.9 A 84 84 0 0 0 368.0 285.4 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 346.4 378.7 A 150 150 0 0 1 253.6 378.7 L 274.0 315.9 A 84 84 0 0 0 326.0 315.9 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 253.6 378.7 A 150 150 0 0 1 178.6 324.2 L 232.0 285.4 A 84 84 0 0 0 274.0 315.9 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 178.6 324.2 A 150 150 0 0 1 150.0 236.0 L 216.0 236.0 A 84 84 0 0 0 232.0 285.4 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 150.0 236.0 A 150 150 0 0 1 178.6 147.8 L 232.0 186.6 A 84 84 0 0 0 216.0 236.0 Z" fill="var(--background)" fillOpacity={1} />
        <path d="M 178.6 147.8 A 150 150 0 0 1 253.6 93.3 L 274.0 156.1 A 84 84 0 0 0 232.0 186.6 Z" fill="var(--accent)" fillOpacity={0.14} />
      </g>
      <circle cx={300} cy={236} r={76} fill="var(--background)" stroke="rgba(26,37,64,0.22)" strokeWidth={1} />
      <g fontFamily="sans-serif" fontSize={13} fontWeight={600} fill="rgba(26,37,64,0.55)" textAnchor="middle">
        <text x={300.0} y={123.0}>1</text>
        <text x={368.8} y={145.3}>2</text>
        <text x={411.3} y={203.8}>3</text>
        <text x={411.3} y={276.2}>4</text>
        <text x={368.8} y={334.7}>5</text>
        <text x={300.0} y={357.0}>6</text>
        <text x={231.2} y={334.7}>7</text>
        <text x={188.7} y={276.2}>8</text>
        <text x={188.7} y={203.8}>9</text>
        <text x={231.2} y={145.3}>10</text>
      </g>
      <g fontFamily="sans-serif" fontSize={12} fill="var(--foreground)">
        <text x={300.0} y={69.0} textAnchor="middle">Капитал и</text>
        <text x={300.0} y={83.0} textAnchor="middle">собственность</text>
        <text x={396.4} y={100.3} textAnchor="start">Стратегия</text>
        <text x={396.4} y={114.3} textAnchor="start">и границы</text>
        <text x={456.0} y={182.3} textAnchor="start">Ценность</text>
        <text x={456.0} y={196.3} textAnchor="start">и отличие</text>
        <text x={456.0} y={283.7} textAnchor="start">Продукт</text>
        <text x={456.0} y={297.7} textAnchor="start">и фокус</text>
        <text x={396.4} y={365.7} textAnchor="start">Организация</text>
        <text x={396.4} y={379.7} textAnchor="start">и люди</text>
        <text x={300.0} y={404.0} textAnchor="middle">Клиенты</text>
        <text x={203.6} y={365.7} textAnchor="end">Планирование</text>
        <text x={203.6} y={379.7} textAnchor="end">и бюджет</text>
        <text x={144.0} y={283.7} textAnchor="end">Производительность</text>
        <text x={144.0} y={297.7} textAnchor="end">и мотивация</text>
        <text x={144.0} y={182.3} textAnchor="end">Цена</text>
        <text x={144.0} y={196.3} textAnchor="end">и продвижение</text>
        <text x={203.6} y={107.3} textAnchor="end">Финансы</text>
      </g>
      <text x={300} y={230} textAnchor="middle" fontFamily="sans-serif" fontSize={14} fontWeight={600} fill="var(--foreground)">Алмазное</text>
      <text x={300} y={248} textAnchor="middle" fontFamily="sans-serif" fontSize={14} fontWeight={600} fill="var(--foreground)">колесо</text>
      <text x={300} y={268} textAnchor="middle" fontFamily="sans-serif" fontSize={11} fill="rgba(26,37,64,0.55)">10 модулей</text>
      <text x={300} y={456} textAnchor="middle" fontFamily="sans-serif" fontSize={12} fill="rgba(26,37,64,0.6)">Модуль 10 — следствие решений в остальных девяти</text>
    </svg>
  )
}
// ─── Матрица 3×3 в логике GE/McKinsey ────────────────────────────────────────
// Ось конкурентоспособности развёрнута к канону: сильная слева.
// Это то же правило, что в расчёте (COL_INDEX = {high: 0, mid: 1, low: 2}).
// Пример на схеме — иллюстративный, к расчёту конкретного клиента отношения
// не имеет.

export function PowerMatrixSvg() {
  const cells: { r: number; c: number }[] = []
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) cells.push({ r, c })

  const fillFor = (r: number, c: number) => {
    const rank = r + c
    if (rank <= 1) return 'rgba(30,58,138,0.16)'
    if (rank === 2) return 'rgba(30,58,138,0.08)'
    return 'rgba(192,57,43,0.08)'
  }

  const X0 = 96
  const Y0 = 34
  const S = 118

  const rowLabels = ['Высокая', 'Средняя', 'Низкая']
  const colLabels = ['Высокая', 'Средняя', 'Низкая']

  return (
    <svg viewBox="0 0 520 452" style={{ width: '100%', height: 'auto' }} role="img" aria-label="Матрица 3 на 3 в логике GE/McKinsey">
      {cells.map(({ r, c }) => (
        <rect
          key={`${r}-${c}`}
          x={X0 + c * S}
          y={Y0 + r * S}
          width={S - 6}
          height={S - 6}
          rx={4}
          fill={fillFor(r, c)}
          stroke="rgba(26,37,64,0.14)"
          strokeWidth={1}
        />
      ))}

      {/* подписи строк — привлекательность рынка */}
      {rowLabels.map((l, r) => (
        <text key={l} x={88} y={Y0 + r * S + (S - 6) / 2 + 4} textAnchor="end" fontSize={12} fill="rgba(26,37,64,0.65)">{l}</text>
      ))}

      {/* подписи столбцов — конкурентоспособность */}
      {colLabels.map((l, c) => (
        <text key={l} x={X0 + c * S + (S - 6) / 2} y={Y0 + 3 * S + 14} textAnchor="middle" fontSize={12} fill="rgba(26,37,64,0.65)">{l}</text>
      ))}

      {/* названия осей */}
      <text x={18} y={Y0 + 1.5 * S} textAnchor="middle" fontSize={12} fontWeight={600} fill="#1a2540" transform={`rotate(-90 18 ${Y0 + 1.5 * S})`}>
        ПРИВЛЕКАТЕЛЬНОСТЬ РЫНКА
      </text>
      <text x={X0 + 1.5 * S - 3} y={Y0 + 3 * S + 44} textAnchor="middle" fontSize={12} fontWeight={600} fill="#1a2540">
        КОНКУРЕНТОСПОСОБНОСТЬ
      </text>

      {/* текущая позиция и условный переход */}
      <defs>
        <marker id="m3arrow" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto">
          <path d="M0,0 L7,3.2 L0,6.4 z" fill="#c0392b" />
        </marker>
      </defs>
      <line
        x1={X0 + 1.5 * S - 3}
        y1={Y0 + 1.5 * S - 3}
        x2={X0 + 0.5 * S + 6}
        y2={Y0 + 0.5 * S + 10}
        stroke="#c0392b"
        strokeWidth={2}
        strokeDasharray="5 4"
        markerEnd="url(#m3arrow)"
      />
      <circle cx={X0 + 1.5 * S - 3} cy={Y0 + 1.5 * S - 3} r={6} fill="#c0392b" />
      <text x={X0 + 1.5 * S + 10} y={Y0 + 1.5 * S + 1} fontSize={11} fill="#c0392b" fontWeight={600}>Сегодня</text>
      <text x={X0 + 0.5 * S - 30} y={Y0 + 0.5 * S - 4} fontSize={11} fill="#c0392b" fontWeight={600}>Условный переход</text>

      <text x={X0} y={446} fontSize={10} fill="rgba(26,37,64,0.45)">Пример раскладки. Позиция и переход рассчитываются по вашим ответам.</text>
    </svg>
  )
}

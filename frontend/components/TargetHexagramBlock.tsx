'use client'
import { HexagramSVG } from '@/components/HexagramSVG'

// Целевая гексаграмма раздела 02 отчёта.
// Источник данных — БД: strategies.target_combination (миграция 020),
// приходит через /api/strategies/{combination} полями target_*.
// Разметку держим согласованной с backend/app/transition_block.py:
// правило паритета HTML и PDF.
export function TargetHexagramBlock({
  strategy,
  labelStyle,
}: {
  strategy: any
  labelStyle?: any
}) {
  if (!strategy?.target_number) return null
  return (
    <div style={{ marginBottom: 20 }}>
      <span style={labelStyle}>Целевая гексаграмма</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8 }}>
        <HexagramSVG combo={strategy.target_combination} size={88} color="#1a2540" />
        <div style={{ fontSize: 15, color: '#1a2540' }}>
          {strategy.target_number} &middot; {strategy.target_name}
        </div>
      </div>
    </div>
  )
}

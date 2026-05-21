'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getAssessment, getMe, getAssessmentStrategy, assessmentPdfUrl } from '@/lib/api'
import type { Strategy, Assessment, AuthUser } from '@/lib/api'
import { AppNav } from '@/components/AppNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

// ── Hexagram data ─────────────────────────────────────────────────────────────

const HEX_INFO: Record<string, [number, string]> = {
  'AAAAAA':[1,'Действие'],'BBBBBB':[2,'Реакция'],'ABBBAB':[3,'Появление'],
  'BABBBA':[4,'Формализация'],'AAABAB':[5,'Бдительность'],'BABAAA':[6,'Раздор'],
  'BABBBB':[7,'Управление'],'BBBBAB':[8,'Объединение'],'AAABAA':[9,'Развитие'],
  'AABAAA':[10,'Последовательность'],'AAABBB':[11,'Достижение'],'BBBAAA':[12,'Препятствие'],
  'ABAAAA':[13,'Осознанность'],'AAAABA':[14,'Процветание'],'BBABBB':[15,'Смирение'],
  'BBBABB':[16,'Радость'],'ABBAAB':[17,'Соответствие'],'BAABBA':[18,'Диссонанс'],
  'AABBBB':[19,'Подход'],'BBBBAA':[20,'Наблюдать'],'ABBABA':[21,'Устранять'],
  'ABABBA':[22,'Изящество'],'BBBBBA':[23,'Разрушение'],'ABBBBB':[24,'Возрождение'],
  'ABBAAA':[25,'Естественность'],'AAABBA':[26,'Изобилие'],'ABBBBA':[27,'Умеренность'],
  'BAAAAB':[28,'Избыток'],'BABBAB':[29,'Решимость'],'ABAABA':[30,'Великолепие'],
  'BBAAAB':[31,'Влияние'],'BAAABB':[32,'Выносливость'],'BBAAAA':[33,'Благоразумие'],
  'AAAABB':[34,'Сила'],'BBBABA':[35,'Благоприятный'],'ABABBB':[36,'Неблагоприятный'],
  'ABABAA':[37,'Гармония'],'AABABA':[38,'Полярность'],'BBABAB':[39,'Трудность'],
  'BABABB':[40,'Избавление'],'AABBBA':[41,'Убыток'],'ABBBAA':[42,'Прибыль'],
  'AAAAAB':[43,'Прорыв'],'BAAAAA':[44,'Встреча'],'BBBAAB':[45,'Объединение'],
  'BAABBB':[46,'Самоотдача'],'BABAAB':[47,'Понимание'],'BAABAB':[48,'Глубина'],
  'ABAAAB':[49,'Реформа'],'BAAABA':[50,'Ценности'],'ABBABB':[51,'Смелость'],
  'BBABBA':[52,'Сосредоточенность'],'BBABAA':[53,'Готовность'],'AABABB':[54,'Амбиции'],
  'ABAABB':[55,'Изобилие'],'BBAABA':[56,'Стимулирование'],'BABBAA':[57,'Интуиция'],
  'AABAAB':[58,'Бодрость'],'BAABAA':[59,'Установление связей'],'AABBAB':[60,'Реализм'],
  'AABBAA':[61,'Внутренняя правда'],'BBAABB':[62,'Точность'],'ABABAB':[63,'Завершение'],
  'BABABA':[64,'Незавершённость'],
}

const TARGET_HEX: Record<number, number> = {
  1:9,2:62,3:49,4:7,5:63,6:6,7:62,8:23,9:37,10:25,11:36,12:9,13:37,14:26,15:11,16:54,
  17:63,18:64,19:34,20:33,21:64,22:18,23:56,24:19,25:37,26:22,27:4,28:44,29:3,30:22,
  31:43,32:44,33:1,34:1,35:64,36:37,37:63,38:21,39:5,40:46,41:27,42:3,43:5,44:33,
  45:58,46:57,47:44,48:47,49:63,50:18,51:25,52:18,53:39,54:11,55:36,56:14,57:44,
  58:5,59:44,60:43,61:42,62:33,63:17,64:40,
}

const NUM_TO_COMBO: Record<number, string> = Object.fromEntries(
  Object.entries(HEX_INFO).map(([combo, [n]]) => [n, combo])
)

function hexSymbol(combo: string): string {
  const info = HEX_INFO[combo]
  if (!info) return '䷀'
  return String.fromCodePoint(0x4DC0 + info[0] - 1)
}

function getTargetHexInfo(combo: string): { num: number; name: string; symbol: string } | null {
  const info = HEX_INFO[combo]
  if (!info) return null
  const [curNum] = info
  const targetNum = TARGET_HEX[curNum]
  if (!targetNum) return null
  const targetCombo = NUM_TO_COMBO[targetNum]
  const targetName = targetCombo ? HEX_INFO[targetCombo]?.[1] ?? '' : ''
  return { num: targetNum, name: targetName, symbol: targetCombo ? hexSymbol(targetCombo) : '䷀' }
}

// ── Labels ────────────────────────────────────────────────────────────────────

const LC_FIELDS: [keyof Strategy, string][] = [
  ['lc_profit',    'Формирование прибыли'],
  ['lc_strategy',  'Рыночная стратегия'],
  ['lc_decisions', 'Принятие решений'],
  ['lc_consumer',  'Тип потребителя'],
  ['lc_market',    'Статус рынка'],
  ['lc_value',     'Тип ценности'],
]

const SCENARIO_KEYS: [string, string][] = [
  ['innovation_strategy',   'Инновационная стратегия'],
  ['innovation_type',       'Тип инновации'],
  ['value_discipline',      'Ценностная дисциплина'],
  ['leadership_principles', 'Принципы лидерства'],
  ['growth_strategy',       'Стратегия роста'],
  ['focus',                 'Фокус'],
]

const ASSM_FIELDS: [keyof Strategy, string][] = [
  ['assm_planning',    'Планирование'],
  ['assm_growth',      'Рост и производительность'],
  ['assm_advertising', 'Реклама'],
  ['assm_feedback',    'Обратная связь'],
  ['assm_risk',        'Риск'],
  ['assm_product',     'Выбор продукта'],
  ['assm_service',     'Сервис'],
  ['assm_startup',     'Стартап'],
  ['assm_investment',  'Инвестиции и финансы'],
  ['assm_contracts',   'Договора и соглашения'],
  ['assm_sync',        'Синхронизация'],
  ['assm_creative',    'Творческий вклад'],
  ['assm_interaction', 'Взаимодействие'],
  ['assm_resources',   'Достаточность ресурсов'],
  ['assm_research',    'Исследование и разработка'],
  ['assm_trade',       'Международная торговля'],
  ['assm_failures',    'Источники неудач'],
  ['assm_success',     'Источники удачи'],
]

// ── UI helpers ────────────────────────────────────────────────────────────────

const S = {
  eyebrow: {
    fontFamily: 'sans-serif' as const,
    fontSize: 10,
    letterSpacing: 2.5,
    textTransform: 'uppercase' as const,
    color: '#c0392b',
    fontWeight: 700,
    marginBottom: 12,
  },
  card: {
    background: 'rgba(255,255,255,0.72)',
    border: '1px solid rgba(26,37,64,0.09)',
    borderRadius: 10,
    padding: '22px 28px',
    marginBottom: 16,
  },
  empty: {
    fontFamily: 'sans-serif' as const,
    fontSize: 13,
    color: 'rgba(26,37,64,0.28)',
    fontStyle: 'italic' as const,
    margin: 0,
  },
  body: {
    fontFamily: 'sans-serif' as const,
    fontSize: 14,
    color: 'rgba(26,37,64,0.82)',
    lineHeight: 1.75,
    margin: 0,
    whiteSpace: 'pre-wrap' as const,
  },
}

function EyebrowLabel({ children }: { children: React.ReactNode }) {
  return <div style={S.eyebrow}>{children}</div>
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ ...S.card, ...style }}>{children}</div>
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Card>
      <EyebrowLabel>{label}</EyebrowLabel>
      {children}
    </Card>
  )
}

function Val({ text }: { text: string | null | undefined }) {
  if (text) {
    return <p style={S.body}>{text}</p>
  }
  return <p style={S.empty}>Не заполнено</p>
}

// ── Method 1 Report ───────────────────────────────────────────────────────────

function Method1Report({
  assessment, strategy, user, onBack, onDownload, generatingPdf,
}: {
  assessment: Assessment
  strategy: Strategy | null
  user: AuthUser
  onBack: () => void
  onDownload: () => void
  generatingPdf: boolean
}) {
  const combo = assessment.method1_combination ?? 'AAAAAA'
  const hexInfo = HEX_INFO[combo]
  const [hexNum, hexName] = hexInfo ?? [0, '']
  const sym = hexSymbol(combo)
  const companyName = assessment.company_name || user.company_name || user.full_name || 'Компания'
  const dateStr = new Date(assessment.created_at).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric',
  })

  const targetHex = getTargetHexInfo(combo)

  // LC blocks — always show all 6
  const lcBlocks = LC_FIELDS.map(([field, label], i) => ({
    label,
    letter: combo[i] ?? 'A',
    value: strategy?.[field] as string | null ?? null,
  }))

  // Scenario table rows — always show all
  const scRows: [string, string | null][] = SCENARIO_KEYS.map(([k, lbl]) => [
    lbl,
    strategy?.scenario?.[k] ?? null,
  ])

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '48px 40px 80px' }}>

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
        <button onClick={onBack} className="btn btn-ghost" style={{ fontSize: 13, padding: '8px 16px' }}>
          ← Назад
        </button>
        <button
          className="btn btn-primary"
          onClick={onDownload}
          disabled={generatingPdf}
          style={{ opacity: generatingPdf ? 0.6 : 1 }}
        >
          {generatingPdf ? 'Формируем PDF…' : '↓ Скачать отчёт PDF'}
        </button>
      </div>

      {/* ── 1. ОБЛОЖКА ── */}
      <div style={{
        background: '#1a2540', borderRadius: 14, padding: '48px 52px',
        marginBottom: 32, position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', right: 40, top: '50%', transform: 'translateY(-50%)',
          fontFamily: 'Georgia,serif', fontSize: 220, color: 'rgba(255,255,255,0.04)',
          lineHeight: 1, userSelect: 'none', pointerEvents: 'none',
        }}>{sym}</div>

        <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', color: '#c0392b', fontWeight: 700, marginBottom: 20 }}>
          СТРАТЕГИЧЕСКИЙ ОТЧЁТ · 64 ДАО
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 28, marginBottom: 28 }}>
          <div style={{ fontFamily: 'Georgia,serif', fontSize: 110, color: 'rgba(255,255,255,0.9)', lineHeight: 1, flexShrink: 0 }}>
            {sym}
          </div>
          <div style={{ paddingTop: 12 }}>
            {strategy?.stratagema_title && (
              <div style={{
                display: 'inline-block', padding: '3px 10px', borderRadius: 4,
                fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5,
                textTransform: 'uppercase', background: 'rgba(192,57,43,0.25)',
                border: '1px solid rgba(192,57,43,0.4)', color: '#e8a090', marginBottom: 12,
              }}>
                {strategy.stratagema_title}
              </div>
            )}
            <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#fff', margin: '0 0 8px', lineHeight: 1.2 }}>
              {strategy?.title || hexName}
            </h1>
            {hexNum > 0 && (
              <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 4 }}>
                Гексаграмма {hexNum}
              </div>
            )}
          </div>
        </div>

        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 18, display: 'flex', gap: 36 }}>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Компания</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{companyName}</div>
          </div>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Дата</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{dateStr}</div>
          </div>
        </div>
      </div>

      {/* Strategy image */}
      {strategy?.image_url && (
        <div style={{ marginBottom: 24, borderRadius: 10, overflow: 'hidden', border: '1px solid rgba(26,37,64,0.08)' }}>
          <img src={`${API}${strategy.image_url}`} alt={strategy.title ?? ''} style={{ width: '100%', display: 'block' }} />
        </div>
      )}

      {/* ── 2. ЖИЗНЕННЫЙ ЦИКЛ ── */}
      <Section label="Жизненный цикл">
        {/* Stage badge */}
        {strategy?.lifecycle_stage ? (
          <div style={{
            display: 'inline-block', padding: '3px 10px', borderRadius: 4,
            fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, textTransform: 'uppercase',
            background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.2)',
            color: '#c0392b', marginBottom: 14,
          }}>
            {strategy.lifecycle_stage}
          </div>
        ) : (
          <div style={{ marginBottom: 14 }}>
            <span style={{ ...S.empty }}>Стадия не указана</span>
          </div>
        )}

        {/* 6 LC blocks */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 20 }}>
          {lcBlocks.map((b, i) => (
            <div key={i} style={{
              background: 'rgba(255,255,255,0.5)',
              border: '1px solid rgba(26,37,64,0.1)',
              borderRadius: 8, padding: '12px 14px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{
                  width: 20, height: 20, borderRadius: '50%',
                  background: b.letter === 'A' ? 'rgba(30,58,138,0.12)' : 'rgba(26,37,64,0.07)',
                  border: `1px solid ${b.letter === 'A' ? 'rgba(30,58,138,0.25)' : 'rgba(26,37,64,0.15)'}`,
                  color: b.letter === 'A' ? '#1e3a8a' : '#1a2540',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'monospace', fontSize: 10, fontWeight: 700, flexShrink: 0,
                }}>{b.letter}</span>
                <span style={{
                  fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 1.2,
                  textTransform: 'uppercase', color: 'rgba(26,37,64,0.45)', fontWeight: 600,
                }}>{b.label}</span>
              </div>
              {b.value
                ? <p style={{ fontFamily: 'sans-serif', fontSize: 12.5, color: '#1a2540', lineHeight: 1.65, margin: 0 }}>{b.value}</p>
                : <p style={S.empty}>Не заполнено</p>
              }
            </div>
          ))}
        </div>
      </Section>

      {/* ── 3. СЦЕНАРИЙ СТРАТАГЕМЫ (ТАБЛИЦА) ── */}
      <Section label="Сценарий стратагемы">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            {scRows.map(([label, value], i) => (
              <tr key={label} style={{ background: i % 2 === 0 ? 'rgba(26,37,64,0.03)' : 'transparent' }}>
                <td style={{
                  padding: '8px 14px', border: '1px solid rgba(26,37,64,0.09)',
                  fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)',
                  width: '40%', verticalAlign: 'top',
                }}>{label}</td>
                <td style={{
                  padding: '8px 14px', border: '1px solid rgba(26,37,64,0.09)',
                  fontFamily: 'sans-serif', fontSize: 13, color: value ? '#1a2540' : 'rgba(26,37,64,0.28)',
                  fontWeight: value ? 500 : 400,
                  fontStyle: value ? 'normal' : 'italic',
                  verticalAlign: 'top',
                }}>
                  {value ?? 'Не заполнено'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      {/* ── 4. ПРЕДПОЛОЖЕНИЯ ── */}
      <Section label="Предположения · связи с будущим">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 0 }}>
          {ASSM_FIELDS.map(([field, label], i) => {
            const val = strategy?.[field] as string | null ?? null
            return (
              <div key={String(field)} style={{
                paddingBottom: 16, marginBottom: 16,
                borderBottom: i < ASSM_FIELDS.length - 1 ? '1px solid rgba(26,37,64,0.07)' : 'none',
              }}>
                <div style={{
                  fontFamily: 'sans-serif', fontSize: 10, fontWeight: 700,
                  letterSpacing: 1.5, textTransform: 'uppercase',
                  color: '#c0392b', marginBottom: 6,
                }}>{label}</div>
                {val
                  ? <p style={S.body}>{val}</p>
                  : <p style={S.empty}>Предположение не заполнено</p>
                }
              </div>
            )
          })}
        </div>
      </Section>

      {/* ── 5. ЦЕЛЕВОЕ СОСТОЯНИЕ (ПЕРЕХОД) ── */}
      <Card style={{ border: '1px solid rgba(192,57,43,0.2)', background: 'rgba(192,57,43,0.04)' }}>
        <EyebrowLabel>Целевое состояние · Переход</EyebrowLabel>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 20, marginBottom: 16 }}>
          {targetHex && (
            <div style={{ textAlign: 'center', flexShrink: 0, minWidth: 80 }}>
              <div style={{ fontFamily: 'Georgia,serif', fontSize: 64, lineHeight: 1, color: '#1a2540', marginBottom: 6 }}>
                {targetHex.symbol}
              </div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 10, color: '#c0392b', letterSpacing: 1, fontWeight: 600 }}>
                Гексаграмма {targetHex.num}
              </div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.6)', marginTop: 3 }}>
                {targetHex.name}
              </div>
            </div>
          )}
          <div style={{ flex: 1 }}>
            {strategy?.transition_title ? (
              <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 20, fontWeight: 400, color: '#1a2540', margin: '0 0 4px' }}>
                {strategy.transition_title}
              </h3>
            ) : (
              <p style={S.empty}>Название перехода не заполнено</p>
            )}
            {strategy?.transition_lifecycle_stage && (
              <div style={{
                display: 'inline-block', padding: '2px 8px', borderRadius: 4, marginBottom: 10,
                fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.2, textTransform: 'uppercase',
                background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.2)', color: '#c0392b',
              }}>
                {strategy.transition_lifecycle_stage}
              </div>
            )}
          </div>
        </div>
        {strategy?.transition_description
          ? <p style={S.body}>{strategy.transition_description}</p>
          : <p style={S.empty}>Описание перехода не заполнено</p>
        }
      </Card>

    </div>
  )
}

// ── Method 2 Report ───────────────────────────────────────────────────────────

const BMC_LABELS: Record<string, string> = {
  'Ключевые партнёры':      '01',
  'Ключевые активности':    '02',
  'Ключевые ресурсы':       '03',
  'Ценностное предложение': '04',
  'Отношения с клиентами':  '05',
  'Каналы':                 '06',
  'Сегменты клиентов':      '07',
  'Структура издержек':     '08',
  'Потоки доходов':         '09',
}

const BMC_ORDER = [
  'Ключевые партнёры', 'Ключевые активности', 'Ключевые ресурсы',
  'Ценностное предложение', 'Отношения с клиентами', 'Каналы',
  'Сегменты клиентов', 'Структура издержек', 'Потоки доходов',
]

function ScoreDots({ score }: { score: number }) {
  return (
    <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
      {[1,2,3,4,5].map(n => (
        <div key={n} style={{
          width: 10, height: 10, borderRadius: '50%',
          background: n <= score ? '#1e3a8a' : 'rgba(26,37,64,0.12)',
        }} />
      ))}
      <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.5)', marginLeft: 6 }}>
        {score} / 5
      </span>
    </div>
  )
}

function Method2Report({
  assessment, user, onBack, onDownload, generatingPdf,
}: {
  assessment: Assessment
  user: AuthUser
  onBack: () => void
  onDownload: () => void
  generatingPdf: boolean
}) {
  const method2 = assessment.method2_data as Record<string, { score: number; text: string }> | null
  const companyName = assessment.company_name || user.company_name || user.full_name || 'Компания'
  const dateStr = new Date(assessment.created_at).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric',
  })

  const blocks = BMC_ORDER
    .filter(key => method2?.[key])
    .map(key => ({ title: key, num: BMC_LABELS[key] ?? '', ...method2![key] }))

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '48px 40px 80px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
        <button onClick={onBack} className="btn btn-ghost" style={{ fontSize: 13, padding: '8px 16px' }}>← Назад</button>
        <button className="btn btn-primary" onClick={onDownload} disabled={generatingPdf} style={{ opacity: generatingPdf ? 0.6 : 1 }}>
          {generatingPdf ? 'Формируем PDF…' : '↓ Скачать отчёт PDF'}
        </button>
      </div>

      <div style={{ background: '#1a2540', borderRadius: 14, padding: '48px 52px', marginBottom: 32 }}>
        <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', color: '#c0392b', fontWeight: 700, marginBottom: 20 }}>
          БИЗНЕС МОДЕЛЬ · 64 ДАО
        </div>
        <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 34, fontWeight: 400, color: '#fff', margin: '0 0 24px', lineHeight: 1.2 }}>
          Анализ бизнес-модели
        </h1>
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 18, display: 'flex', gap: 36 }}>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Компания</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{companyName}</div>
          </div>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Дата</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{dateStr}</div>
          </div>
        </div>
      </div>

      {blocks.length > 0 ? (
        <>
          <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2.5, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600, marginBottom: 12 }}>
            Оценка блоков
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 32 }}>
            {blocks.map(block => (
              <div key={block.title} style={{ background: 'rgba(255,255,255,0.72)', border: '1px solid rgba(26,37,64,0.09)', borderRadius: 10, padding: '16px 18px' }}>
                <div style={{ fontFamily: 'sans-serif', fontSize: 11, fontWeight: 600, color: '#1a2540', marginBottom: 10 }}>
                  {block.num} · {block.title}
                </div>
                <ScoreDots score={block.score} />
              </div>
            ))}
          </div>
          <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2.5, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600, marginBottom: 12 }}>
            Комментарии
          </div>
          {blocks.map(block => (
            <Section key={block.title} label={`${block.num} · ${block.title}`}>
              <div style={{ marginBottom: block.text ? 14 : 0 }}><ScoreDots score={block.score} /></div>
              {block.text
                ? <p style={S.body}>{block.text}</p>
                : <p style={S.empty}>Комментарий не добавлен</p>
              }
            </Section>
          ))}
        </>
      ) : (
        <Section label="Бизнес-модель">
          <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.5)', margin: 0 }}>
            Данные бизнес-модели не заполнены.
          </p>
        </Section>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ReportPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)
  const [generatingPdf, setGeneratingPdf] = useState(false)

  useEffect(() => {
    const init = async () => {
      try {
        const [me, data] = await Promise.all([getMe(), getAssessment(id)])
        setUser(me)
        setAssessment(data)
        setIsAdmin(me.role === 'admin')

        if (data.method1_combination) {
          try {
            const s = await getAssessmentStrategy(id)
            setStrategy(s)
          } catch {
            // strategy not in DB yet
          }
        }
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [id])

  const handleDownload = () => {
    setGeneratingPdf(true)
    window.open(assessmentPdfUrl(id), '_blank')
    setTimeout(() => setGeneratingPdf(false), 2000)
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка…
    </div>
  )
  if (!assessment || !user) return null

  // Method1 если есть комбинация, иначе Method2
  const isMethod2 = !assessment.method1_combination
  const backUrl = isAdmin ? '/admin/my-reports' : '/dashboard'

  return (
    <>
      <AppNav current="dashboard" />
      {isMethod2 ? (
        <Method2Report
          assessment={assessment}
          user={user}
          onBack={() => router.push(backUrl)}
          onDownload={handleDownload}
          generatingPdf={generatingPdf}
        />
      ) : (
        <Method1Report
          assessment={assessment}
          strategy={strategy}
          user={user}
          onBack={() => router.push(backUrl)}
          onDownload={handleDownload}
          generatingPdf={generatingPdf}
        />
      )}
    </>
  )
}

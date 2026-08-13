/**
 * Метод 3 «Матрица силы» — клиент API.
 *
 * Отдельный модуль, а не api.ts: api.ts импортируют все остальные разделы,
 * и добавление туда типов изолированного метода расширяет поверхность правок
 * без выигрыша. Транспорт переиспользуется — request экспортирован из api.ts,
 * чтобы конфигурация fetch (credentials: 'include' для httpOnly-куки)
 * оставалась в одном месте.
 */
import { request } from '@/lib/api'

// ── Справочники ───────────────────────────────────────────────────────────────

export interface M3Industry {
  id: number
  name: string
}

export function listIndustries() {
  return request<M3Industry[]>('/api/m3/industries')
}

// ── Портфель ──────────────────────────────────────────────────────────────────

export type M3Profitability = 'profitable' | 'marginal' | 'unprofitable' | 'unknown'

export const PROFITABILITY_LABELS: Record<M3Profitability, string> = {
  profitable: 'Прибыльно',
  marginal: 'На грани',
  unprofitable: 'Убыточно',
  unknown: 'Не знаю',
}

export interface M3ObjectIn {
  position: number
  name: string
  revenue: number | null
  revenue_dynamics: number | null
  revenue_share: number | null
  profitability: M3Profitability
  industry_id: number | null
  screening_price: boolean
  screening_market: boolean
  is_new_venture: boolean
}

export interface M3Object extends M3ObjectIn {
  id: string
}

export interface M3Portfolio {
  id: string
  title: string | null
  /** Название компании: вводится перед диагностикой, идёт в заголовок отчёта. */
  company_name: string | null
  industry_id: number | null
  status: 'draft' | 'filled' | 'calculated'
  owner_ranks: number[] | null
  created_at: string
  calculated_at: string | null
  objects: M3Object[]
}

export function createPortfolio(data: {
  title?: string | null
  company_name?: string | null
  industry_id?: number | null
}) {
  return request<M3Portfolio>('/api/m3/portfolios', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function listPortfolios() {
  return request<M3Portfolio[]>('/api/m3/portfolios')
}

/** Удаляет портфель вместе с ответами, снимком расчёта и файлом PDF. */
export function deletePortfolio(id: string) {
  return request<void>(`/api/m3/portfolios/${id}`, { method: 'DELETE' })
}

export function getPortfolio(id: string) {
  return request<M3Portfolio>(`/api/m3/portfolios/${id}`)
}

export function putObjects(id: string, objects: M3ObjectIn[]) {
  return request<M3Portfolio>(`/api/m3/portfolios/${id}/objects`, {
    method: 'PUT',
    body: JSON.stringify({ objects }),
  })
}

export function putOwnerRanks(id: string, ranks: number[]) {
  return request<M3Portfolio>(`/api/m3/portfolios/${id}/owner-ranks`, {
    method: 'PUT',
    body: JSON.stringify({ ranks }),
  })
}

// ── Анкета ────────────────────────────────────────────────────────────────────

export interface M3Item {
  id: string
  block: string
  code: string
  line: number
  text: string
  is_reverse: boolean
  item_version: number
  hint: string | null
  is_arbiter: boolean
}

export interface M3Questionnaire {
  portfolio_id: string
  market_items: M3Item[]
  object_items: M3Item[]
  override_items: M3Item[]
  arbiter_items: M3Item[]
  objects: M3Object[]
}

export interface M3AnswerIn {
  item_code: string
  object_id?: string | null
  value: number | null
}

export interface M3ArbiterRow {
  object_id: string
  position: number
  name: string
  lines: number[]
  items: M3Item[]
}

export function getQuestionnaire(id: string) {
  return request<M3Questionnaire>(`/api/m3/portfolios/${id}/questionnaire`)
}

export function saveAnswers(id: string, answers: M3AnswerIn[]) {
  return request<{ saved: number; status: string }>(`/api/m3/portfolios/${id}/answers`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  })
}

export function getArbiterRequired(id: string) {
  return request<M3ArbiterRow[]>(`/api/m3/portfolios/${id}/arbiter-required`)
}

export function calculate(id: string) {
  return request<{
    portfolio_id: string
    objects: number
    verdicts_held: boolean
    flags: string[]
  }>(`/api/m3/portfolios/${id}/calculate`, { method: 'POST' })
}

// ── Отчёт ─────────────────────────────────────────────────────────────────────

/**
 * Вердикт, траектория и разбор портфеля приходят с сервера готовыми.
 *
 * Правило одно, а отчётов два — веб и PDF. Считать его здесь второй раз
 * значит завести третью копию: две копии раскладки карты мы уже держим
 * вручную, и это потолок. Клиент только отображает.
 */
export interface M3Verdict {
  zone_ru: string
  zone_en: string
  stance: string
  mobility: string
  verdict: string
  notes: string[]
}

export interface M3TransitionMove {
  axis: 'strength' | 'attract'
  from: 'low' | 'mid' | 'high'
  to: 'low' | 'mid' | 'high'
  phrase: string
}

export interface M3Transition {
  kind: 'target' | 'risk'
  from_hex: number
  to_hex: number
  from_cells: ['low' | 'mid' | 'high', 'low' | 'mid' | 'high']
  to_cells: ['low' | 'mid' | 'high', 'low' | 'mid' | 'high']
  moves: M3TransitionMove[]
  phrase: string
}

export interface M3Trajectory {
  // Обе ветки необязательны: подвижная линия может остаться внутри своей
  // триграммы и ячейку не сдвинуть — тогда печатать нечего.
  target: M3Transition | null
  risk: M3Transition | null
}

export interface M3YinRow {
  line: number
  factor: string
  yin: number
  yin_ripe: number
  yang: number
  yang_hot: number
  delta_line: number
  total: number
  strong_names: string[]
  reading: string
}

export interface M3Constraint {
  line: number
  factor: string
  yin: number
  yang: number
  yang_hot: number
  delta_line: number
  total: number
  kind: 'competence' | 'structural'
  kind_title: string
  body: string
}

export interface M3MetricReading {
  name: string
  value: string
  reading: string
}

export interface M3RankRow {
  position: number
  name: string
  owner_rank: number
  v_rank: number
  gap: number
}

export interface M3RankComparison {
  rows: M3RankRow[]
  agreed: number
  total: number
  disputed: M3RankRow[]
  /** Прочтение собирается на бэкенде: у формулировки уже есть потребитель
   *  в PDF, и вторая копия здесь разошлась бы с ним. */
  reading: string
}

export interface M3Analysis {
  yin_table: M3YinRow[]
  constraints: M3Constraint[]
  metrics: M3MetricReading[]
  tact_note: string
  /** null, если порядок не назван: сравнивать нечего. */
  rank_comparison: M3RankComparison | null
}

export interface M3Result {
  object_id: string
  name: string
  position: number
  scores: Record<string, number>
  symbols: string
  mobility: Record<string, string>
  cell_strength: 'low' | 'mid' | 'high'
  cell_attract: 'low' | 'mid' | 'high'
  cell_key: string
  cell_label: string
  // Вывод ячейки: какие линии дали Ян и на какую сумму весов.
  // Отсутствует у снимков до ревизии 030 — весов в них нет.
  cell_breakdown?: {
    strength: M3CellAxis
    attract: M3CellAxis
  } | null
  coord_strength: number
  coord_attract: number
  current_hex: number
  current_name: string
  target_hex: number | null
  target_lines: number[]
  risk_hex: number | null
  risk_lines: number[]
  v_index: number
  z_index: number
  v_rank: number
  z_rank: number
  weak_line: number
  strong_line: number
  tensions: string[]
  flags: string[]
  /** Сколько пунктов рынка направление переопределило своими ответами (0–6). */
  market_overrides: number
  /** Подпись колонки «Рынок». Собирается на бэкенде (m3_verdict.market_label):
   *  у формулировки одно определение, копии здесь нет. */
  market_label: string
  verdict: M3Verdict
  trajectory: M3Trajectory
  execution_reason: string
}

export interface M3NarrativeBlock {
  kind: string
  key: string
  title: string
  body: string
  mistake: string | null
}

export interface M3Report {
  portfolio: M3Portfolio
  summary: {
    objects: number
    sum_positions: number
    sum_positions_max: number
    turbulence: number
    delta: number
    distinct_cells: number
    spearman: number | null
    flags: string[]
    verdicts_held: boolean
    reduced: boolean
  }
  objects: { result: M3Result; narrative: M3NarrativeBlock[] }[]
  investment_order: string[]
  execution_order: string[]
  analysis: M3Analysis
  disclaimers: string[]
}

export function getReport(id: string) {
  return request<M3Report>(`/api/reports/m3/${id}`)
}

// ── Чек-лист и решение по волнам ──────────────────────────────────────────────

export interface M3ChecklistStep {
  id: string
  object_id: string | null
  step_text: string
  line: number | null
  step_type: 'route' | 'hold' | 'prep' | 'decision'
  wave: number
  needs_budget: boolean
  done: boolean
  done_at: string | null
}

export interface M3TradeoffIn {
  accepted_option: 'method' | 'custom'
  waves: Record<string, string[]>
  cost_accepted?: string | null
  review_triggers?: string[]
}

export function getChecklist(id: string) {
  return request<M3ChecklistStep[]>(`/api/reports/m3/${id}/checklist`)
}

export function toggleChecklistStep(id: string, stepId: string, done: boolean) {
  return request<M3ChecklistStep>(`/api/reports/m3/${id}/checklist/${stepId}`, {
    method: 'PATCH',
    body: JSON.stringify({ done }),
  })
}

export function postTradeoff(id: string, body: M3TradeoffIn) {
  return request<{ decision_id: string; steps_rescheduled: number }>(
    `/api/reports/m3/${id}/tradeoff`,
    { method: 'POST', body: JSON.stringify(body) },
  )
}

// ── Ограничения, зеркалящие серверные ─────────────────────────────────────────
// Дублируются намеренно: форма должна ловить ошибку до отправки, иначе
// пользователь получает 422 без указания, какое поле виновато. Сервер остаётся
// источником истины — клиентская проверка только предупреждает раньше.

export const OBJECTS_MIN = 3
export const OBJECTS_MAX = 8
export const MIN_SHARE = 3
export const MIN_COVERAGE = 80

export type M3CellAxis = {
  level: 'low' | 'mid' | 'high'
  sum: number
  total: number
  lines: { line: number; weight: number }[]
  /** Готовая строка вида «Сила: Ян на Л2 (45) + Л3 (30) = 75 из 100 → высокая».
   *  Собирается на бэкенде (m3_verdict.cell_breakdown_text): у формулировки
   *  одно определение, копии здесь нет. */
  text: string
}

export const LINE_TITLES: Record<number, string> = {
  1: 'Ресурсы и юнит-экономика',
  2: 'Продукт и дифференциация',
  3: 'Каналы и доля',
  4: 'Спрос сегмента',
  5: 'Структура рынка и маржа',
  6: 'Макро и регулирование',
}

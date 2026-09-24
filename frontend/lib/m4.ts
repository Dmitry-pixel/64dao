/**
 * Метод 4 «Алмазное колесо» — клиент API админки контента.
 *
 * Отдельный модуль по той же причине, что lib/m3.ts: типы изолированного
 * метода не расширяют общий api.ts. Транспорт общий — request из api.ts.
 */
import { request } from '@/lib/api'

const A = '/api/admin/m4'
const put = <T>(path: string, body: unknown) =>
  request<T>(`${A}${path}`, { method: 'PUT', body: JSON.stringify(body) })

export interface M4Module {
  code: number
  slug: string
  name: string
  client_question: string
  why_it_matters: string
  intro: string | null
  is_effect: boolean
  sort: number
  is_active: boolean
}

export interface M4Option {
  value: string
  label: string
  score: number | null
  sort: number
}

export interface M4Question {
  code: string
  module_code: number
  text: string
  type: 'bool' | 'scale3' | 'choice' | 'number' | 'money'
  unit: string | null
  weight: number
  is_fact: boolean
  tier: 'u0' | 'u1'
  reverse: boolean
  score_neutral: boolean
  score_excluded: boolean
  affects: string | null
  unknown_allowed: boolean
  unknown_score: number | null
  unknown_confidence_penalty: number
  metric_code: string | null
  control_pair: string | null
  applies_when: Record<string, string[]> | null
  construct_code: string | null
  source_ref: string | null
  note_internal: string | null
  min_value: number | null
  max_value: number | null
  item_version: number
  sort: number
  is_active: boolean
  options: M4Option[]
}

export type M4CardKind = 'module_state' | 'module_constraint' | 'recommendation' | 'dynamics' | 'confidence'

export interface M4Card {
  id: string
  kind: M4CardKind
  key: string
  module_code: number | null
  state: 'low' | 'mid' | 'high' | null
  rule_code: string | null
  title: string
  body: string
  mistake: string | null
  steps: string[] | null
  first_step: string | null
  how_to_check: string | null
  effect: number | null
  speed_weeks: number | null
  cost: number | null
  item_version: number
  sort: number
  is_active: boolean
}

export interface M4Rule {
  code: string
  title: string
  severity: 'high' | 'medium' | 'low'
  conditions: Record<string, unknown>
  diagnosis: string
  what_happens: string
  fix_one_of: string[]
  cost_of_inaction: string
  source_ref: string | null
  is_mvp: boolean
  rule_version: number
  sort: number
  is_active: boolean
}

export interface M4ConstructLink {
  method: string
  item_code: string
  reverse: boolean
  dynamic: boolean
  free_text: boolean
}

export interface M4Construct {
  code: string
  name: string
  unit: 'company' | 'direction' | 'function'
  reusable: boolean
  cross_check: 'always' | 'single_direction_only' | 'no' | null
  cross_check_why: string | null
  note: string | null
  sort: number
  is_active: boolean
  links: M4ConstructLink[]
}

export interface M4Chain {
  code: string
  label: string
  detected_by: string[]
  chain: string[]
  root_modules: number[]
  check_questions: string[]
  first_action: string
  note: string | null
  sort: number
  is_active: boolean
}

export const m4Admin = {
  modules: () => request<M4Module[]>(`${A}/modules`),
  putModule: (code: number, body: Partial<M4Module>) => put<M4Module>(`/modules/${code}`, body),

  questions: () => request<M4Question[]>(`${A}/questions`),
  putQuestion: (code: string, body: Partial<M4Question>) => put<M4Question>(`/questions/${code}`, body),
  setQuestionActive: (code: string, is_active: boolean) =>
    put<M4Question>(`/questions/${code}/active`, { is_active }),
  putOption: (code: string, value: string, body: Partial<M4Option>) =>
    put<M4Question>(`/questions/${code}/options/${value}`, body),

  cards: () => request<M4Card[]>(`${A}/cards`),
  putCard: (id: string, body: Partial<M4Card>) => put<M4Card>(`/cards/${id}`, body),

  rules: () => request<M4Rule[]>(`${A}/rules`),
  putRule: (code: string, body: Partial<M4Rule>) => put<M4Rule>(`/rules/${code}`, body),

  constructs: () => request<M4Construct[]>(`${A}/constructs`),
  putConstruct: (code: string, body: Partial<M4Construct>) => put<M4Construct>(`/constructs/${code}`, body),

  chains: () => request<M4Chain[]>(`${A}/chains`),
  putChain: (code: string, body: Partial<M4Chain>) => put<M4Chain>(`/chains/${code}`, body),
}

// ── Клиентская часть: прогоны анкеты ─────────────────────────────────────────

const C = '/api/m4'

export type M4Mode = 'express' | 'full'
export type M4RunStatus = 'draft' | 'filled' | 'calculated'

export interface M4ClientOption { value: string; label: string }

export interface M4ClientQuestion {
  code: string
  text: string
  type: 'bool' | 'scale3' | 'choice' | 'number' | 'money'
  unit: string | null
  is_fact: boolean
  unknown_allowed: boolean
  min: number | null
  max: number | null
  /** {"M01-Q09": ["yes"]} | {"M02-Q04": "yes"} | {"M02-Q10": ">1"} | {"profile.revenue_model": [...]} */
  applies_when: Record<string, string | string[]> | null
  options: M4ClientOption[]
}

export interface M4ClientModule {
  code: number
  name: string
  client_question: string
  intro: string | null
  questions: M4ClientQuestion[]
}

export interface M4Questionnaire {
  mode: M4Mode
  modules: M4ClientModule[]
  profile_options: Record<string, M4ClientOption[]>
}

export interface M4Profile {
  revenue_model: 'one_off' | 'repeat' | 'subscription'
  industry_id?: number | null
  revenue_range?: string | null
  headcount?: number | null
  active_clients?: number | null
}

export interface M4AnswerValue { code: string; value: string | null; number: number | null; source?: string }

export interface M4Progress { answered: number; required: number; missing: string[] }

export interface M4RunOut {
  id: string
  mode: M4Mode
  status: M4RunStatus
  company_id: string
  company_name: string | null
  is_followup: boolean
  reduced: boolean
  created_at: string
  calculated_at: string | null
  progress: M4Progress
  answers?: M4AnswerValue[]
}

export interface M4ModuleResult {
  score: number | null
  state: 'low' | 'mid' | 'high' | null
  answered: number
  unknown: number
  no_accounting: boolean
}

export interface M4Result {
  run_id: string
  mode: M4Mode
  calc_version: string
  modules: Record<string, M4ModuleResult>
  top_gaps: number[]
  constraint: { module: number; score: number; strength: number; blocked: number[] } | null
  cause_effect: { causes_avg: number; effect: number; case: string } | null
  fired_rules: { code: string; severity: string }[]
  unverified_rules: string[]
  confidence: { index: number; level: 'high' | 'medium' | 'low' } & Record<string, unknown>
  resistance: number
  priority_queue: unknown[]
  metrics: Record<string, number> | null
  reduced: boolean
  calculated_at: string | null
}

export interface M4CardText {
  title: string
  body: string
  mistake: string | null
  steps: string[] | null
  first_step: string | null
  how_to_check: string | null
}

export interface M4ReportModule {
  code: number
  name: string
  client_question: string | null
  is_effect: boolean
  score: number | null
  state: 'low' | 'mid' | 'high' | null
  no_accounting: boolean
  card: M4CardText | null
}

export interface M4ReportAction {
  n: number
  key: string
  module_code: number | null
  module_name: string | null
  rule_code: string | null
  is_constraint: boolean
  blocked_by_constraint: boolean
  effect: number
  speed_weeks: number
  cost: number
  title: string
  body: string | null
  steps: string[] | null
  options: string[] | null
  first_step: string | null
  how_to_check: string | null
}

export interface M4Report {
  run: { id: string; mode: M4Mode; company_name: string | null; calculated_at: string | null; calc_version: string; reduced: boolean }
  modules: M4ReportModule[]
  top_gaps: { code: number; name: string }[]
  constraint: { module: number; name: string; score: number; blocked: { code: number; name: string }[]; card: M4CardText | null } | null
  cause_effect: { causes_avg: number; effect: number; case: string; text: string | null } | null
  contradictions: {
    code: string; title: string; severity: 'high' | 'medium' | 'low'; diagnosis: string
    what_happens: string; fix_one_of: string[]; cost_of_inaction: string
  }[]
  unverified: { code: string; title: string }[]
  actions: M4ReportAction[]
  resistance: number
  confidence: {
    index: number; level: 'high' | 'medium' | 'low'; cautious: boolean
    card: M4CardText | null; no_accounting: { code: number; name: string }[]
  }
}

export const m4 = {
  questionnaire: (mode: M4Mode) => request<M4Questionnaire>(`${C}/questionnaire?mode=${mode}`),
  credits: () => request<{ full_available: number | null }>(`${C}/credits`),
  profile: (companyId: string) => request<M4Profile | null>(`${C}/companies/${companyId}/profile`),
  putProfile: (companyId: string, body: M4Profile) =>
    request<M4Profile>(`${C}/companies/${companyId}/profile`, { method: 'PUT', body: JSON.stringify(body) }),
  runs: () => request<M4RunOut[]>(`${C}/runs`),
  run: (id: string) => request<M4RunOut>(`${C}/runs/${id}`),
  createRun: (body: { mode: M4Mode; company_name?: string | null; company_id?: string | null; profile?: M4Profile }) =>
    request<M4RunOut>(`${C}/runs`, { method: 'POST', body: JSON.stringify(body) }),
  saveAnswers: (id: string, answers: { code: string; value?: string | null; number?: number | null }[]) =>
    request<M4RunOut>(`${C}/runs/${id}/answers`, { method: 'PUT', body: JSON.stringify({ answers }) }),
  calculate: (id: string) => request<M4Result>(`${C}/runs/${id}/calculate`, { method: 'POST' }),
  result: (id: string) => request<M4Result>(`${C}/runs/${id}/result`),
  report: (id: string) => request<M4Report>(`${C}/runs/${id}/report`),
  deleteRun: (id: string) => request<void>(`${C}/runs/${id}`, { method: 'DELETE' }),
}

/** Условие показа вопроса — та же логика, что m4_engine.applies на сервере.
 *  Совпадение важно: иначе анкета спросит то, чего расчёт не учтёт. */
export function m4Applies(
  q: M4ClientQuestion,
  answers: Record<string, M4AnswerValue>,
  profile: M4Profile | null,
): boolean {
  for (const [ref, cond] of Object.entries(q.applies_when ?? {})) {
    let val: string | null | undefined
    let num: number | null | undefined
    if (ref.startsWith('profile.')) {
      val = (profile as unknown as Record<string, string | null> | null)?.[ref.slice(8)]
    } else {
      val = answers[ref]?.value
      num = answers[ref]?.number
    }
    if (Array.isArray(cond)) {
      if (!cond.includes(val ?? '')) return false
      continue
    }
    const m = /^(>=|<=|>|<)(-?\d+(?:\.\d+)?)$/.exec(cond)
    if (m) {
      const bound = Number(m[2])
      if (num == null) return false
      const ok = m[1] === '>=' ? num >= bound : m[1] === '<=' ? num <= bound : m[1] === '>' ? num > bound : num < bound
      if (!ok) return false
      continue
    }
    if (val !== cond) return false
  }
  return true
}

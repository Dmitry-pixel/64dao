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

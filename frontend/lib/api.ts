/**
 * 64dao — API client
 * credentials: 'include' обязательно для передачи httpOnly-куки auth-token.
 */

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost'

// ── Base ──────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Экспортирован ради lib/m3.ts: Метод 3 держит свои типы отдельно, но
 * транспорт должен остаться один. Иначе credentials: 'include' для
 * httpOnly-куки пришлось бы дублировать, и копии разошлись бы при первой
 * же правке заголовков.
 */
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail ?? body.error ?? 'Request failed')
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

// ── Тарифы и флаги раздела ────────────────────────────────────────────────────

export interface PricingProduct {
  title: string
  price: number
  currency: string
  description: string
  features: { label: string; value: string }[]
  payment_enabled: boolean
  payment_note: string
}

export interface PricingResponse extends PricingProduct {
  /** Тарифы по продуктам: m12 — Методы 1 и 2, m3 — Метод 3. */
  products: Record<'m12' | 'm3', PricingProduct>
}

/**
 * Публичный тариф. Плоские поля верхнего уровня — тариф m12: так отвечает
 * бэкенд ради лендинга, который читает price/title напрямую.
 */
export function getPricing() {
  return request<PricingResponse>('/api/pricing')
}

/**
 * Режим сайта + флаг раздела Метода 3.
 *
 * Флаг нужен до запроса /api/m3/*: при выключенном разделе весь он отдаёт
 * 404 (осознанное решение бэкенда), и кабинет ловил бы 404 на каждом заходе.
 */
export function getSiteMode() {
  return request<{ enabled?: boolean; m3_enabled: boolean }>('/api/site-mode')
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function sendOTP(email: string) {
  return request<{ message: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export async function verifyOTP(email: string, code: string) {
  return request<{ success: boolean; role: string }>('/api/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  })
}

export async function resendOTP(email: string) {
  return request<{ message: string }>('/api/auth/resend-otp', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export async function logout() {
  _meCache = null
  return request<{ message: string }>('/api/auth/logout', { method: 'POST' })
}

/** Завершает сессии на всех устройствах, включая текущую. */
export async function logoutAll() {
  _meCache = null
  return request<{ message: string }>('/api/auth/logout-all', { method: 'POST' })
}

let _meCache: AuthUser | null = null
let _meFetching: Promise<AuthUser> | null = null

export async function getMe(): Promise<AuthUser> {
  if (_meCache) return _meCache
  if (_meFetching) return _meFetching
  _meFetching = request<AuthUser>('/api/auth/me').then(u => {
    _meCache = u
    _meFetching = null
    return u
  }).catch(err => {
    _meFetching = null
    throw err
  })
  return _meFetching
}

// ── Registration ──────────────────────────────────────────────────────────────

export async function register(data: {
  email: string
  full_name: string
  company_name: string
}) {
  return request<{ message: string }>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ── Assessments ───────────────────────────────────────────────────────────────

export async function createAssessment(data: {
  method?: 'method1' | 'method2'
  method1_answers?: Record<string, string>
  method1_combination?: string | null
  method2_data?: Record<string, { score: number; text: string }>
  finance_answers?: Record<string, number | null>
  company_name?: string | null
  company_id?: string | null
  status?: string
}) {
  return request<Assessment>('/api/assessments', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export interface FinanceItem {
  item_id: string
  text: string
}
export interface FinanceBlock {
  block: number
  title: string
  items: FinanceItem[]
}
export interface FinanceItemsResponse {
  scale_labels: Record<string, string>
  blocks: FinanceBlock[]
}

export interface BaseQuestion {
  lc_key: string
  label: string
  q: string
  help: string
  a: string
  b: string
  a_full: string
  b_full: string
}

/** 6 базовых вопросов Метода 1. Тексты правятся в админке, дефолты — в коде бэкенда. */
export async function getBaseQuestions() {
  return request<{ questions: BaseQuestion[] }>('/api/method1/base-questions')
}

export async function getFinanceItems() {
  return request<ContourItemsResponse>('/api/method1/finance-items')
}

// ── Контуры диагностики Метода 1 ─────────────────────────────────────────────

export interface ContourItemsResponse extends FinanceItemsResponse {
  contour: string
  title: string
  intro: string
  max_unknowns: number
}

export interface ContourInfo {
  contour: string
  title: string
  intro: string
  enabled: boolean
}

export interface PassedContour {
  contour: string
  combination: string
  created_at: string
}

export interface ContourSubmitResult {
  contour: string
  title: string
  combination: string
  result: Record<string, unknown>
}

/**
 * Метод диагностики. Признак приходит с сервера (assessments.method);
 * откат на содержимое method2_data — только для ответов, отданных до
 * появления поля. Единственное место, где это решается: раньше проверка
 * была скопирована в четыре файла и разъезжалась.
 */
export function isMethod2(a: { method?: string | null; method2_data?: unknown }): boolean {
  if (a.method) return a.method === 'method2'
  const d = a.method2_data as Record<string, unknown> | null | undefined
  return !!(d && Object.keys(d).length > 0)
}

export async function listContours() {
  return request<{ contours: ContourInfo[] }>('/api/method1/contours')
}

export async function getContourItems(contour: string) {
  return request<ContourItemsResponse>(`/api/method1/contour-items/${contour}`)
}

export async function submitContour(
  assessmentId: string,
  contour: string,
  answers: Record<string, number | null>,
) {
  return request<ContourSubmitResult>(
    `/api/assessments/${assessmentId}/contours/${contour}`,
    { method: 'POST', body: JSON.stringify({ answers }) },
  )
}

export async function listAssessments(q?: string) {
  const qs = q && q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ""
  return request<Assessment[]>(`/api/assessments${qs}`)
}

export async function getAssessment(id: string) {
  return request<Assessment>(`/api/assessments/${id}`)
}

export async function deleteAssessment(id: string) {
  return request<void>(`/api/assessments/${id}`, { method: 'DELETE' })
}

export function reportDownloadUrl(reportId: string) {
  return `${API}/api/reports/${reportId}/download`
}

export async function generateReport(assessmentId: string) {
  return request<ReportOut>(`/api/assessments/${assessmentId}/generate-report`, { method: 'POST' })
}

export function assessmentPdfUrl(assessmentId: string) {
  return `${API}/api/assessments/${assessmentId}/pdf`
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface Company {
  id: string
  name: string
  assessment_count: number
  latest_at: string | null
}

export function getCompanies() {
  return request<Company[]>('/api/companies')
}

export function getCompanyDynamics(id: string, compare: 'previous' | 'first' = 'previous') {
  return request<any>(`/api/companies/${id}/dynamics?compare=${compare}`)
}

// ── Настройки рассылки (админ) ───────────────────────────────────────────────
export interface RemindersSettings {
  enabled:        boolean
  repeat_enabled: boolean
  repeat_days:    number
}

export const adminApi = {
  stats:          () => request('/api/admin/stats'),
  users:          () => request('/api/admin/users'),
  strategies:     () => request('/api/admin/strategies'),
  getStrategy:    (id: string) => request(`/api/admin/strategies/${id}`),
  createStrategy: (d: unknown) => request('/api/admin/strategies', { method: 'POST', body: JSON.stringify(d) }),
  updateStrategy: (id: string, d: unknown) => request(`/api/admin/strategies/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  deleteStrategy: (id: string) => request(`/api/admin/strategies/${id}`, { method: 'DELETE' }),
  reports:        () => request('/api/admin/reports'),
  resetContour:   (assessmentId: string, contour: string) =>
    request<void>(`/api/admin/assessments/${assessmentId}/contours/${contour}`, { method: 'DELETE' }),
  logs:           () => request<LogEntry[]>('/api/admin/logs'),
  emailTemplates:     () => request<Record<string, EmailTemplate>>('/api/admin/email-templates'),
  saveEmailTemplates: (d: Record<string, EmailTemplate>) => request('/api/admin/email-templates', { method: 'PUT', body: JSON.stringify(d) }),
  remindersSettings:     () => request<RemindersSettings>('/api/admin/reminders-settings'),
  saveRemindersSettings: (d: RemindersSettings) => request<RemindersSettings>('/api/admin/reminders-settings', { method: 'PUT', body: JSON.stringify(d) }),

  uploadImage: async (strategyId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API}/api/admin/strategies/${strategyId}/image`, {
      method: 'POST', credentials: 'include', body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new ApiError(res.status, err.detail ?? 'Upload failed')
    }
    return res.json()
  },

  setup: (d: { setup_key: string; email: string; full_name: string }) =>
    request('/api/admin/setup', { method: 'POST', body: JSON.stringify(d) }),

  impersonate:     (userId: string) => request(`/api/admin/impersonate/${userId}`, { method: 'POST' }),
  stopImpersonate: ()               => request('/api/admin/impersonate/stop', { method: 'POST' }),
  impersonateStatus: ()             => request<ImpersonateStatus>('/api/admin/impersonate/status'),

  revokeUserSessions: (userId: string) =>
    request(`/api/admin/users/${userId}/revoke-sessions`, { method: 'POST' }),

  setUserRole: (userId: string, role: 'user' | 'admin') =>
    request(`/api/admin/users/${userId}/role`, { method: 'PATCH', body: JSON.stringify({ role }) }),

  setUserStatus: (userId: string, isActive: boolean) =>
    request(`/api/admin/users/${userId}/status`, { method: 'PATCH', body: JSON.stringify({ is_active: isActive }) }),

  deleteUser: (userId: string) =>
    request(`/api/admin/users/${userId}`, { method: 'DELETE' }),
  socialLinks:     () => request<{ telegram: string; vk: string; max: string }>('/api/admin/social-links'),
  saveSocialLinks: (d: { telegram: string; vk: string; max: string }) =>
    request('/api/admin/social-links', { method: 'PUT', body: JSON.stringify(d) }),
  sampleReportStatus: (method?: string) =>
    request<{ uploaded: boolean; size_bytes: number | null }>(
      `/api/admin/sample-report/status${method ? `?method=${method}` : ''}`,
    ),
  uploadSampleReport: async (file: File, method?: string) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API}/api/admin/sample-report${method ? `?method=${method}` : ''}`, {
      method: 'POST', credentials: 'include', body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new ApiError(res.status, err.detail ?? 'Upload failed')
    }
    return res.json()
  },
  deleteSampleReport: (method?: string) =>
    request(`/api/admin/sample-report${method ? `?method=${method}` : ''}`, { method: 'DELETE' }),
  lifecycleStages: () =>
    request<{ sort_order: number; name: string; description: string | null }[]>('/api/admin/lifecycle-stages'),
  saveLifecycleStages: (d: { sort_order: number; description: string | null }[]) =>
    request('/api/admin/lifecycle-stages', { method: 'PUT', body: JSON.stringify(d) }),

  // Тестовый доступ (гранты): квота + срок, письмо партнёру.
  accessGrants: (status?: string) =>
    request<AccessGrant[]>(`/api/admin/access-grants${status ? `?status=${status}` : ''}`),
  userAccessGrants: (userId: string) =>
    request<AccessGrant[]>(`/api/admin/users/${userId}/access-grants`),
  createAccessGrant: (userId: string, d: { quota: number; expires_at: string; reason?: string | null; notify: boolean }) =>
    request<AccessGrant>(`/api/admin/users/${userId}/access-grants`, { method: 'POST', body: JSON.stringify(d) }),
  revokeAccessGrant: (grantId: string) =>
    request<AccessGrant>(`/api/admin/access-grants/${grantId}/revoke`, { method: 'POST' }),
  notifyAccessGrant: (grantId: string) =>
    request<AccessGrant>(`/api/admin/access-grants/${grantId}/notify`, { method: 'POST' }),
}

// ── Strategies (public/user) ──────────────────────────────────────────────────

export async function getStrategyByCombo(combination: string) {
  return request<Strategy>(`/api/strategies/${combination}`)
}

export async function getAssessmentStrategy(assessmentId: string) {
  return request<Strategy>(`/api/assessments/${assessmentId}/strategy`)
}

export interface Strategy {
  id: string
  combination: string
  title: string | null
  current_state: Record<string, string> | null
  stratagema_title: string | null
  lifecycle_stage: string | null
  lifecycle_description: string | null
  lc_profit: string | null
  lc_strategy: string | null
  lc_decisions: string | null
  lc_consumer: string | null
  lc_market: string | null
  lc_value: string | null
  scenario: Record<string, string> | null
  scenario_text: string | null
  marketing_text: string | null
  management_text: string | null
  transition_title: string | null
  transition_lifecycle_stage: string | null
  transition_description: string | null
  image_url: string | null
  assm_planning: string | null
  assm_growth: string | null
  assm_advertising: string | null
  assm_feedback: string | null
  assm_risk: string | null
  assm_product: string | null
  assm_service: string | null
  assm_startup: string | null
  assm_investment: string | null
  assm_contracts: string | null
  assm_sync: string | null
  assm_creative: string | null
  assm_interaction: string | null
  assm_resources: string | null
  assm_research: string | null
  assm_trade: string | null
  assm_failures: string | null
  assm_success: string | null
  is_published: boolean
  updated_at: string
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ImpersonateStatus {
  active: boolean
  target_user: { id: string; email: string; full_name: string | null; role: string } | null
  admin_id: string | null
}

export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  company_name: string | null
  role: 'user' | 'admin'
  created_at: string
}

export interface ReportOut {
  id: string
  pdf_filename: string | null
  generated_at: string | null
  created_at: string
}

export interface EmailTemplate {
  subject:     string
  body_html:   string
  description?: string
}

export interface LogEntry {
  type:       'user' | 'assessment' | 'report'
  timestamp:  string
  user_email: string
  user_name:  string | null
  detail:     string
  sub:        string | null
}

export interface Assessment {
  id: string
  user_id: string
  method: 'method1' | 'method2' | null
  method1_combination: string | null
  method2_data: Record<string, { score: number; text: string }> | null
  company_name: string | null
  status: 'draft' | 'completed' | 'paid'
  created_at: string
  passed_contours?: PassedContour[]
  reports: ReportOut[]
  strategy_image_url: string | null
  finance_combination?: string | null
  finance_result?: Record<string, unknown> | null
  // Повторная диагностика: счётчик права живёт на первичной.
  company_id?:           string | null
  parent_assessment_id?: string | null
  is_followup?:          boolean
  followup_allowed?:     number
  followup_used?:        number
}

// ── Access grants (временный бесплатный доступ) ───────────────────────────────

export interface AccessGrant {
  id: string
  user_id: string
  user_email: string | null
  user_name: string | null
  quota: number
  used: number
  remaining: number
  status: 'active' | 'pending' | 'used_up' | 'expired' | 'revoked'
  starts_at: string
  expires_at: string
  reason: string | null
  created_at: string
  revoked_at: string | null
  email_sent_at: string | null
}

export interface CreditsBreakdown {
  credits: number
  paid_credits: number
  grant_credits: number
  grant_expires_at: string | null
}

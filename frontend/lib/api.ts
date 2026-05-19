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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    // FastAPI возвращает detail при HTTPException, error при нашем обработчике
    throw new ApiError(res.status, body.detail ?? body.error ?? 'Request failed')
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────────────

/**
 * Шаг 1: отправляем ТОЛЬКО email.
 * Бэкенд находит пользователя, генерирует OTP, отправляет на почту.
 * Никакого пароля — чистый OTP-flow.
 */
export async function sendOTP(email: string) {
  return request<{ message: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

/**
 * Шаг 2: отправляем email + код.
 * Бэкенд верифицирует OTP, ставит httpOnly-куку auth-token.
 * userId НЕ передаём — сервер идентифицирует по email.
 */
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
  return request<{ message: string }>('/api/auth/logout', { method: 'POST' })
}

export async function getMe() {
  return request<AuthUser>('/api/auth/me')
}

// ── Registration ──────────────────────────────────────────────────────────────

export async function register(data: {
  email: string
  password: string
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
  method1_answers?: Record<string, string>
  method1_combination?: string | null
  method2_data?: Record<string, { score: number; text: string }>
  status?: string
}) {
  return request<Assessment>('/api/assessments', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function listAssessments() {
  return request<Assessment[]>('/api/assessments')
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

// ── Admin ─────────────────────────────────────────────────────────────────────

export const adminApi = {
  stats:          () => request('/api/admin/stats'),
  users:          () => request('/api/admin/users'),
  strategies:     () => request('/api/admin/strategies'),
  getStrategy:    (id: string) => request(`/api/admin/strategies/${id}`),
  createStrategy: (d: unknown) => request('/api/admin/strategies', { method: 'POST', body: JSON.stringify(d) }),
  updateStrategy: (id: string, d: unknown) => request(`/api/admin/strategies/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  deleteStrategy: (id: string) => request(`/api/admin/strategies/${id}`, { method: 'DELETE' }),
  reports:        () => request('/api/admin/reports'),

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

  setup: (d: { setup_key: string; email: string; password: string; full_name: string }) =>
    request('/api/admin/setup', { method: 'POST', body: JSON.stringify(d) }),

  impersonate:     (userId: string) => request(`/api/admin/impersonate/${userId}`, { method: 'POST' }),
  stopImpersonate: ()               => request('/api/admin/impersonate/stop', { method: 'POST' }),
  impersonateStatus: ()             => request<ImpersonateStatus>('/api/admin/impersonate/status'),

  setUserRole: (userId: string, role: 'user' | 'admin') =>
    request(`/api/admin/users/${userId}/role`, { method: 'PATCH', body: JSON.stringify({ role }) }),
}

// ── Strategies (public/user) ──────────────────────────────────────────────────

export async function getStrategyByCombo(combination: string) {
  return request<Strategy>(`/api/strategies/${combination}`)
}

export interface Strategy {
  id: string
  combination: string
  title: string | null
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

export interface Assessment {
  id: string
  user_id: string
  method1_combination: string | null
  method2_data: Record<string, { score: number; text: string }> | null
  status: 'draft' | 'completed' | 'paid'
  created_at: string
  reports: ReportOut[]
}

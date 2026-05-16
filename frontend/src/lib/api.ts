const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new ApiError(res.status, data.detail ?? 'Ошибка сервера')
  }
  return res.json()
}

export const sendOTP = (email: string) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ email }) })

export const resendOTP = (email: string) =>
  request('/auth/resend-otp', { method: 'POST', body: JSON.stringify({ email }) })

export const verifyOTP = (email: string, code: string) =>
  request<{ role: string }>('/auth/verify', { method: 'POST', body: JSON.stringify({ email, code }) })

export const getMe = () =>
  request<{ id: string; email: string; role: string; full_name: string }>('/auth/me')

export const logout = () =>
  request('/auth/logout', { method: 'POST' })

// ── Impersonation ──────────────────────────────────────────────────────────────

export interface ImpersonateStatus {
  active: boolean
  target_user: { id: string; email: string; full_name: string | null; role: string } | null
  admin_id: string | null
}

export const getImpersonateStatus = () =>
  request<ImpersonateStatus>('/admin/impersonate/status')

export const stopImpersonation = () =>
  request<{ success: boolean; message: string }>('/admin/impersonate/stop', { method: 'POST' })
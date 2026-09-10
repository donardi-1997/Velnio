import { useAuthStore } from '../stores/auth'

const API_BASE = '/api'

async function billingRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().accessToken
  if (!token) throw new Error('Session expired')

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: 'Billing request failed' }))
    throw new Error(payload.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export const billingApi = {
  entitlements: () => billingRequest<any>('/billing/entitlements'),
  checkout: (planCode: string) =>
    billingRequest<{ url: string; session_id?: string | null }>('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan_code: planCode }),
    }),
  portal: () =>
    billingRequest<{ url: string; session_id?: string | null }>('/billing/portal', {
      method: 'POST',
    }),
}

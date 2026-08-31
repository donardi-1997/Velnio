import { useAuthStore } from '../stores/auth'

const API_BASE = '/api'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().accessToken
  const isFormData = options.body instanceof FormData
  const headers: Record<string, string> = isFormData
    ? { ...(options.headers as Record<string, string> || {}) }
    : { 'Content-Type': 'application/json', ...(options.headers as Record<string, string> || {}) }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    const refresh = useAuthStore.getState().refreshToken
    if (refresh) {
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      })
      if (refreshRes.ok) {
        const data = await refreshRes.json()
        useAuthStore.getState().setTokens(data.access_token, data.refresh_token)
        headers['Authorization'] = `Bearer ${data.access_token}`
        const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers })
        if (!retryRes.ok) {
          const err = await retryRes.json().catch(() => ({ detail: 'Error' }))
          throw new Error(err.detail || `HTTP ${retryRes.status}`)
        }
        return retryRes.json()
      }
    }
    useAuthStore.getState().logout()
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  auth: {
    register: (data: { email: string; password: string; first_name: string; last_name: string }) =>
      request<{ access_token: string; refresh_token: string }>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    login: (data: { email: string; password: string }) =>
      request<{ access_token: string; refresh_token: string }>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
    me: () => request<any>('/auth/me'),
  },
  workspace: {
    get: () => request<any>('/workspace'),
  },
  stores: {
    list: () => request<any[]>('/stores'),
    mockConnect: (data: any) => request<any>('/stores/mock-connect', { method: 'POST', body: JSON.stringify(data) }),
    disconnect: (id: string) => request<any>(`/stores/${id}/disconnect`, { method: 'POST' }),
  },
  products: {
    list: () => request<any[]>('/products'),
    create: (data: any) => request<any>('/products', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => request<any>(`/products/${id}`),
    update: (id: string, data: any) => request<any>(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/products/${id}`, { method: 'DELETE' }),
    analyze: (id: string) => request<any>(`/products/${id}/analyze`, { method: 'POST' }),
    publish: (id: string) => request<any>(`/products/${id}/publish`, { method: 'POST' }),
    importPreview: (url: string) => request<any>('/products/import/preview', { method: 'POST', body: JSON.stringify({ url }) }),
    importCreate: (data: any) => request<any>('/products/import/create', { method: 'POST', body: JSON.stringify(data) }),
    uploadImages: (id: string, files: File[]) => {
      const formData = new FormData()
      files.forEach((f) => formData.append('files', f))
      return request<any>(`/products/${id}/images/upload`, { method: 'POST', body: formData })
    },
    enrich: (id: string) => request<any>(`/products/${id}/enrich`, { method: 'POST' }),
    getEnrichment: (id: string) => request<any>(`/products/${id}/enrichment`),
  },
  angles: {
    list: (productId: string) => request<any[]>(`/products/${productId}/angles`),
    generate: (productId: string) => request<any[]>(`/products/${productId}/angles/generate`, { method: 'POST' }),
    select: (productId: string, angleId: string) => request<any>(`/products/${productId}/angles/${angleId}/select`, { method: 'POST' }),
  },
  landing: {
    get: (productId: string) => request<any>(`/products/${productId}/landing`),
    generate: (productId: string) => request<any>(`/products/${productId}/landing/generate`, { method: 'POST' }),
    update: (landingId: string, data: any) => request<any>(`/products/landings/${landingId}`, { method: 'PATCH', body: JSON.stringify(data) }),
    updateSection: (sectionId: string, data: any) => request<any>(`/products/landing-sections/${sectionId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  credits: {
    get: () => request<any>('/credits'),
    transactions: () => request<any[]>('/credits/transactions'),
  },
  billing: {
    plans: () => request<any[]>('/billing/plans'),
    subscription: () => request<any>('/billing/subscription'),
  },
  dashboard: {
    summary: () => request<any>('/dashboard/summary'),
  },
  campaigns: {
    list: () => request<any[]>('/campaigns'),
    create: (data: any) => request<any>('/campaigns', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => request<any>(`/campaigns/${id}`),
    update: (id: string, data: any) => request<any>(`/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/campaigns/${id}`, { method: 'DELETE' }),
    angles: {
      list: (campaignId: string) => request<any[]>(`/campaigns/${campaignId}/angles`),
      generate: (campaignId: string) => request<any[]>(`/campaigns/${campaignId}/angles`, { method: 'POST' }),
      select: (campaignId: string, angleId: string) => request<any>(`/campaigns/${campaignId}/angles/${angleId}/select`, { method: 'POST' }),
    },
    offer: {
      get: (campaignId: string) => request<any>(`/campaigns/${campaignId}/offer`),
      generate: (campaignId: string) => request<any>(`/campaigns/${campaignId}/offer`, { method: 'POST' }),
    },
    landing: {
      get: (campaignId: string) => request<any>(`/campaigns/${campaignId}/landing`),
      generate: (campaignId: string) => request<any>(`/campaigns/${campaignId}/landing`, { method: 'POST' }),
    },
    publish: (campaignId: string) => request<any>(`/campaigns/${campaignId}/publish`, { method: 'POST' }),
    byProduct: (productId: string) => request<any[]>(`/campaigns/by-product/${productId}`),
    generateVisualDirection: (campaignId: string) => request<any>(`/campaigns/${campaignId}/visual-direction/generate`, { method: 'POST' }),
    getVisualDirection: (campaignId: string) => request<any>(`/campaigns/${campaignId}/visual-direction`),
    generateAssets: (campaignId: string) => request<any>(`/campaigns/${campaignId}/assets/generate`, { method: 'POST', body: JSON.stringify({ preset: 'launch_pack' }) }),
    selectAsset: (campaignId: string, imageId: string, purpose: string) => request<any>(`/campaigns/${campaignId}/assets/${imageId}/select?purpose=${purpose}`, { method: 'POST' }),
    getPublishReadiness: (campaignId: string) => request<any>(`/campaigns/${campaignId}/publish-readiness`),
  },
  visualDirections: {
    update: (id: string, data: any) => request<any>(`/campaign-visual-directions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  performance: {
    getCampaign: (campaignId: string, fromDate?: string, toDate?: string) => {
      const params = new URLSearchParams()
      if (fromDate) params.set('from_date', fromDate)
      if (toDate) params.set('to_date', toDate)
      const qs = params.toString()
      return request<any>(`/campaigns/${campaignId}/performance${qs ? '?' + qs : ''}`)
    },
    getTimeline: (campaignId: string, fromDate?: string, toDate?: string) => {
      const params = new URLSearchParams()
      if (fromDate) params.set('from_date', fromDate)
      if (toDate) params.set('to_date', toDate)
      const qs = params.toString()
      return request<any>(`/campaigns/${campaignId}/performance/timeline${qs ? '?' + qs : ''}`)
    },
    getVariants: (campaignId: string) => request<any>(`/campaigns/${campaignId}/variants/performance`),
    getAngles: (campaignId: string) => request<any>(`/campaigns/${campaignId}/angles/performance`),
    analyze: (campaignId: string) => request<any>(`/campaigns/${campaignId}/performance/analyze`, { method: 'POST' }),
  },
  variants: {
    list: (campaignId: string) => request<any[]>(`/campaigns/${campaignId}/variants`),
    create: (campaignId: string, data: { name: string; clone_from_variant_id?: string | null }) =>
      request<any>(`/campaigns/${campaignId}/variants`, { method: 'POST', body: JSON.stringify(data) }),
    update: (campaignId: string, variantId: string, data: any) =>
      request<any>(`/campaigns/${campaignId}/variants/${variantId}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (campaignId: string, variantId: string) =>
      request<void>(`/campaigns/${campaignId}/variants/${variantId}`, { method: 'DELETE' }),
    updateTraffic: (campaignId: string, weights: Record<string, number>) =>
      request<any>(`/campaigns/${campaignId}/variants/traffic`, { method: 'PATCH', body: JSON.stringify({ weights }) }),
  },
  demo: {
    generateEvents: (campaignId: string, data?: { variant_a_sessions?: number; variant_b_sessions?: number; variant_a_purchases?: number; variant_b_purchases?: number; days_back?: number }) =>
      request<any>(`/campaigns/${campaignId}/demo/events`, { method: 'POST', body: JSON.stringify(data || {}) }),
    clearEvents: (campaignId: string) => request<any>(`/campaigns/${campaignId}/demo/events`, { method: 'DELETE' }),
  },
}

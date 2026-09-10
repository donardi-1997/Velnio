import { useAuthStore } from '../stores/auth'

export async function startShopifyOAuth(shopDomain: string): Promise<{ auth_url: string }> {
  const token = useAuthStore.getState().accessToken
  if (!token) throw new Error('Session expired')

  const response = await fetch('/api/stores/shopify/connect', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ shop_domain: shopDomain }),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Unable to connect Shopify' }))
    throw new Error(body.detail || 'Unable to connect Shopify')
  }
  return response.json()
}

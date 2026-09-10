import { request } from './api'

export function startShopifyOAuth(shopDomain: string): Promise<{ auth_url: string }> {
  return request<{ auth_url: string }>('/stores/shopify/connect', {
    method: 'POST',
    body: JSON.stringify({ shop_domain: shopDomain }),
  })
}

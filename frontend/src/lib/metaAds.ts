import { request } from './api'

export interface MetaAdsStatus {
  connected: boolean
  expired: boolean
  mode: string
  meta_user_id: string | null
  meta_user_name: string | null
  connected_at: string | null
  expires_at: string | null
}

export interface MetaAdAccount {
  id: string
  account_id: string
  name: string
  account_status: number | null
  currency: string | null
  timezone_name: string | null
}

export interface MetaPixel {
  id: string
  name: string | null
  last_fired_time: string | null
}

export interface MetaPage {
  id: string
  name: string | null
}

export interface MetaInstagramAccount {
  id: string
  name: string | null
  username: string | null
}

export interface MetaDeliveryResources {
  ad_account_id: string
  pixels: MetaPixel[]
  pages: MetaPage[]
  instagram_accounts: MetaInstagramAccount[]
}

export interface MetaAdsCampaignPublication {
  id: string
  campaign_id: string
  ad_account_id: string
  remote_campaign_id: string
  remote_campaign_name: string
  objective: string
  remote_status: string
  pixel_id: string | null
  page_id: string | null
  instagram_account_id: string | null
  delivery_configured_at: string | null
  created_at: string
  reused?: boolean
}

export interface MetaDeliveryConfigInput {
  pixel_id: string
  page_id: string
  instagram_account_id?: string | null
}

export const metaAdsApi = {
  status: () => request<MetaAdsStatus>('/meta-ads/status'),
  startConnection: () => request<{ auth_url: string; mode: string }>('/meta-ads/connect'),
  connectMock: () => request<{ connected: boolean; meta_user_id: string; meta_user_name: string | null }>('/meta-ads/connect-mock', { method: 'POST' }),
  disconnect: () => request<{ disconnected: boolean }>('/meta-ads/disconnect', { method: 'POST' }),
  adAccounts: () => request<MetaAdAccount[]>('/meta-ads/ad-accounts'),
  deliveryResources: (adAccountId: string) =>
    request<MetaDeliveryResources>(`/meta-ads/ad-accounts/${encodeURIComponent(adAccountId)}/delivery-resources`),
  campaignPublications: (campaignId: string) =>
    request<MetaAdsCampaignPublication[]>(`/campaigns/${campaignId}/meta-ads/publications`),
  publishCampaignPaused: (campaignId: string, adAccountId: string) =>
    request<MetaAdsCampaignPublication>(`/campaigns/${campaignId}/meta-ads/publish`, {
      method: 'POST',
      body: JSON.stringify({ ad_account_id: adAccountId }),
    }),
  configureDelivery: (campaignId: string, publicationId: string, data: MetaDeliveryConfigInput) =>
    request<MetaAdsCampaignPublication>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/delivery-config`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}

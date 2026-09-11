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

export interface MetaAdSetPublication {
  id: string
  campaign_publication_id: string
  remote_ad_set_id: string
  remote_ad_set_name: string
  remote_status: string
  target_country: string
  daily_budget_minor: number
  currency: string
  optimization_goal: string
  billing_event: string
  bid_strategy: string
  created_at: string
  reused?: boolean
}

export interface MetaAdSetPublishInput {
  daily_budget_minor: number
  target_country?: string | null
}

export type MetaCallToAction = 'SHOP_NOW' | 'LEARN_MORE' | 'GET_OFFER'

export interface MetaCreativePublication {
  id: string
  campaign_publication_id: string
  ad_set_publication_id: string
  product_image_id: string | null
  remote_creative_id: string
  remote_creative_name: string
  destination_url: string
  image_url: string
  primary_text: string
  headline: string | null
  call_to_action: MetaCallToAction
  page_id: string
  instagram_account_id: string | null
  created_at: string
  reused?: boolean
}

export interface MetaCreativePublishInput {
  product_image_id: string
  primary_text: string
  headline?: string | null
  call_to_action: MetaCallToAction
}

export interface MetaAdPublication {
  id: string
  campaign_publication_id: string
  ad_set_publication_id: string
  creative_publication_id: string
  remote_ad_id: string
  remote_ad_name: string
  remote_status: string
  created_at: string
  reused?: boolean
}

export interface MetaAdRemoteState {
  ad_publication_id: string
  remote_ad_id: string
  account_id: string
  campaign_id: string
  adset_id: string
  creative_id: string
  configured_status: string
  effective_status: string | null
}

export interface MetaLaunchCheck {
  key: string
  status: 'PASS' | 'FAIL'
  message: string
}

export interface MetaLaunchPlan {
  ad_account_id: string
  remote_campaign_id: string
  remote_ad_set_id: string
  remote_ad_id: string
  remote_creative_id: string
  destination_url: string
  pixel_id: string | null
  page_id: string | null
  instagram_account_id: string | null
  daily_budget_minor: number
  currency: string
  target_country: string
  current_configured_statuses: Record<string, string | null>
  proposed_statuses: Record<string, string>
}

export interface MetaLaunchReadiness {
  ready: boolean
  side_effects_performed: boolean
  readiness_fingerprint: string
  checks: MetaLaunchCheck[]
  launch_plan: MetaLaunchPlan
}

export interface MetaLaunchIntent {
  id: string
  ad_publication_id: string
  readiness_fingerprint: string
  confirmation_token: string
  expires_at: string
  created_at: string
  status: 'PENDING_CONFIRMATION'
  side_effects_performed: boolean
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
  getAdSet: (campaignId: string, publicationId: string) =>
    request<MetaAdSetPublication | null>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/ad-set`),
  publishAdSetPaused: (campaignId: string, publicationId: string, data: MetaAdSetPublishInput) =>
    request<MetaAdSetPublication>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/ad-set`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  creatives: (campaignId: string, publicationId: string) =>
    request<MetaCreativePublication[]>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/creatives`),
  publishCreative: (campaignId: string, publicationId: string, data: MetaCreativePublishInput) =>
    request<MetaCreativePublication>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/creatives`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  ads: (campaignId: string, publicationId: string) =>
    request<MetaAdPublication[]>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/ads`),
  adRemoteState: (campaignId: string, publicationId: string, adPublicationId: string) =>
    request<MetaAdRemoteState>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/ads/${adPublicationId}/remote-state`),
  launchReadiness: (campaignId: string, publicationId: string, adPublicationId: string) =>
    request<MetaLaunchReadiness>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/ads/${adPublicationId}/launch-readiness`),
  createLaunchIntent: (campaignId: string, publicationId: string, adPublicationId: string) =>
    request<MetaLaunchIntent>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/ads/${adPublicationId}/launch-intent`, {
      method: 'POST',
    }),
  publishAdPaused: (campaignId: string, publicationId: string, creativePublicationId: string) =>
    request<MetaAdPublication>(`/campaigns/${campaignId}/meta-ads/publications/${publicationId}/ads`, {
      method: 'POST',
      body: JSON.stringify({ creative_publication_id: creativePublicationId }),
    }),
}

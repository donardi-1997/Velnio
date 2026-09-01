export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Workspace {
  id: string
  name: string
  owner_id: string
  created_at: string
}

export interface Store {
  id: string
  workspace_id: string
  name: string
  shop_domain: string | null
  platform: string
  status: string
  country: string
  currency: string
  created_at: string
}

export interface ProductImage {
  id: string
  image_url: string
  image_type: string
  position: number
  generated_by_ai: string
}

export interface Product {
  id: string
  workspace_id: string
  store_id: string | null
  name: string
  source_type: string
  source_url: string | null
  source_domain: string | null
  source_external_id: string | null
  source_metadata: Record<string, any> | null
  supplier_price: number | null
  selling_price: number | null
  currency: string
  description: string | null
  target_country: string
  target_language: string
  status: string
  published_product_id: string | null
  created_at: string
  updated_at: string
  images: ProductImage[]
}

export interface ProductEnrichment {
  id: string
  product_id: string
  features: string[]
  benefits: string[]
  use_cases: string[]
  suggested_audiences: string[]
  short_description: string | null
  enriched_description: string | null
  created_at: string
  updated_at: string
}

export interface CampaignVisualDirection {
  id: string
  campaign_id: string
  visual_style: string
  tone: string
  color_notes: string | null
  background_style: string | null
  photography_style: string | null
  audience_context: string | null
  additional_instructions: string | null
  created_at: string
  updated_at: string
}

export interface ImportPreview {
  source_type: string
  source_url: string
  source_domain: string | null
  name: string | null
  description: string | null
  price: number | null
  currency: string
  images: { url: string; position: number }[]
  confidence: Record<string, number>
  metadata: Record<string, any>
}

export interface PublishReadiness {
  ready: boolean
  checks: { key: string; status: string; message?: string }[]
}

export interface CampaignImage {
  id: string
  purpose: string
  image_url: string
  source_type: string
  selected: boolean
}

export interface ProductAnalysis {
  id: string
  product_id: string
  overall_score: number
  demand_score: number
  visual_score: number
  problem_score: number
  margin_score: number
  saturation_score: number
  ad_potential_score: number
  impulse_score: number
  return_risk_score: number
  summary: string
  strengths: string[]
  risks: string[]
  recommended_price_min: number | null
  recommended_price_max: number | null
  generated_at: string
}

export interface SellingAngle {
  id: string
  product_id: string
  campaign_id?: string
  name: string
  target_audience: string
  pain_point: string
  main_promise: string
  hook: string
  description: string
  score: number
  position: number
  selected: boolean
  created_at: string
}

export interface LandingSection {
  id: string
  landing_page_id: string
  section_type: string
  position: number
  content: Record<string, any>
  created_at: string
  updated_at: string
}

export interface LandingPage {
  id: string
  product_id: string
  campaign_id?: string
  selling_angle_id: string | null
  title: string
  slug: string
  status: string
  version: number
  created_at: string
  updated_at: string
  sections: LandingSection[]
}

export interface CreditWallet {
  id: string
  workspace_id: string
  balance: number
  lifetime_credits: number
}

export interface CreditTransaction {
  id: string
  workspace_id: string
  amount: number
  transaction_type: string
  description: string
  reference_type: string | null
  reference_id: string | null
  created_at: string
}

export interface Plan {
  id: string
  code: string
  name: string
  monthly_price: number
  included_credits: number
  max_stores: number
  max_products_per_month: number
  active: boolean
}

export interface Subscription {
  id: string
  workspace_id: string
  plan_id: string
  status: string
  current_period_start: string | null
  current_period_end: string | null
  provider: string
  plan: Plan | null
}

export interface DashboardSummary {
  total_products: number
  analyzed_products: number
  total_landings: number
  published_products: number
  credits_remaining: number
}

export enum CampaignStatus {
  DRAFT = 'DRAFT',
  ANALYZING = 'ANALYZING',
  ANGLE_READY = 'ANGLE_READY',
  OFFER_READY = 'OFFER_READY',
  LANDING_READY = 'LANDING_READY',
  PUBLISHED = 'PUBLISHED',
  FAILED = 'FAILED',
}

export enum OfferType {
  STANDARD = 'STANDARD',
  DISCOUNT = 'DISCOUNT',
  BUNDLE = 'BUNDLE',
  BOGO = 'BOGO',
  FREE_SHIPPING = 'FREE_SHIPPING',
  COD = 'COD',
  CUSTOM = 'CUSTOM',
}

export interface Campaign {
  id: string
  product_id: string
  store_id: string
  name: string
  status: CampaignStatus
  target_country: string
  target_language: string
  currency: string
  selling_price: number | null
  supplier_price: number | null
  target_audience: string | null
  payment_strategy: string | null
  shipping_strategy: string | null
  notes: string | null
  external_product_id: string | null
  external_page_id: string | null
  published_at: string | null
  last_publish_error: string | null
  created_at: string
  updated_at: string
  product?: Product
  store?: Store
}

export interface Offer {
  id: string
  campaign_id: string
  headline: string
  offer_type: OfferType
  primary_price: number | null
  compare_at_price: number | null
  discount_percentage: number | null
  bundle_quantity: number | null
  free_shipping: boolean
  cash_on_delivery: boolean
  guarantee_days: number | null
  urgency_text: string | null
  scarcity_text: string | null
  bonus_text: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface CampaignPerformance {
  visitors: number
  sessions: number
  page_views: number
  cta_clicks: number
  add_to_carts: number
  checkouts: number
  purchases: number
  revenue: number
  currency: string
  ctr: number
  atc_rate: number
  checkout_rate: number
  conversion_rate: number
  revenue_per_visitor: number
  aov: number
}

export interface PerformanceTimelinePoint {
  date: string
  sessions: number
  page_views: number
  cta_clicks: number
  add_to_carts: number
  checkouts: number
  purchases: number
  revenue: number
}

export interface LandingVariant {
  id: string
  campaign_id: string
  name: string
  variant_key: string
  status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'ARCHIVED'
  traffic_weight: number
  selling_angle_id: string | null
  offer_id: string | null
  landing_page_id: string | null
  created_at: string | null
  updated_at: string | null
}

export interface VariantPerformance {
  variant_id: string | null
  variant_name: string
  variant_key: string
  status: string
  traffic_weight: number
  sessions: number
  cta_clicks: number
  add_to_carts: number
  checkouts: number
  purchases: number
  revenue: number
  conversion_rate: number
  aov: number
}

export interface AnglePerformance {
  angle_id: string
  angle_name: string
  sessions: number
  purchases: number
  revenue: number
  conversion_rate: number
  aov: number
}

export interface ExperimentAnalysis {
  status: string
  variant_id?: string
  variant_name?: string
  confidence?: number
  lift?: number
  reason?: string
  z_score?: number
  leader_conversion_rate?: number
  runner_conversion_rate?: number
  leader_sessions?: number
  runner_sessions?: number
  leader_purchases?: number
  runner_purchases?: number
}

export interface CampaignPerformanceInsight {
  id: string
  campaign_id: string
  summary: string
  winning_pattern: string | null
  weak_points: string[]
  recommended_actions: string[]
  next_test_type: string | null
  next_test_hypothesis: string | null
  confidence: number | null
  based_on_sessions: number
  generated_at: string | null
}

export interface DemoEventResult {
  total_events: number
  variant_a_events: number
  variant_b_events: number
}

export interface GoogleDriveStatus {
  connected: boolean
  google_email: string | null
  google_name: string | null
  connected_at: string | null
}

export interface GoogleDriveFile {
  id: string
  name: string
  mime_type: string
  size: number | null
  thumbnail_url: string | null
  created_time: string | null
  modified_time: string | null
  web_view_link: string | null
  is_folder: boolean
}

export interface GoogleDriveFolder {
  id: string
  name: string
  files: GoogleDriveFile[]
  folders: GoogleDriveFile[]
}

export interface GoogleDriveSearchResult {
  files: GoogleDriveFile[]
  next_page_token: string | null
}

export interface GoogleDriveImportResponse {
  id: string
  file_name: string | null
  file_type: string
  status: string
  storage_key: string | null
  image_url: string | null
  created_at: string
}

export interface ProductSourceDocument {
  id: string
  product_id: string
  external_file_id: string
  external_file_name: string | null
  file_type: string
  file_size: number | null
  status: string
  storage_key: string | null
  content_text: string | null
  extracted_text: string | null
  character_count: number | null
  page_count: number | null
  extraction_error: string | null
  processed_at: string | null
  error_message: string | null
  created_at: string
}

export interface KnowledgeSource {
  id: string
  workspace_id: string
  product_id: string | null
  campaign_id: string | null
  source_type: string
  content_type: string
  title: string
  content_text: string | null
  url: string | null
  source_document_id: string | null
  content_hash: string | null
  imported_at: string | null
  last_verified_at: string | null
  is_primary: boolean
  status: string
  created_by_user_id: string
  created_at: string
  updated_at: string
}

export interface CampaignBrief {
  id: string
  campaign_id: string
  workspace_id: string
  product_summary: string | null
  target_audience: string | null
  key_benefits: string | null
  tone_of_voice: string | null
  pricing_strategy: string | null
  positioning: string | null
  generated_by_user_id: string
  generated_at: string | null
  credit_cost: string | null
  created_at: string
  updated_at: string
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  if (amount == null || isNaN(amount)) return '$0.00'
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `$${amount.toFixed(2)}`
  }
}

export function formatNumber(n: number): string {
  if (n == null || isNaN(n)) return '0'
  return new Intl.NumberFormat('en-US').format(n)
}

export function formatPercent(n: number, decimals: number = 1): string {
  if (n == null || isNaN(n) || !isFinite(n)) return '0%'
  return `${(n * 100).toFixed(decimals)}%`
}

export function formatRate(n: number, decimals: number = 2): string {
  if (n == null || isNaN(n) || !isFinite(n)) return '0'
  return (n * 100).toFixed(decimals)
}

export function safeDivide(numerator: number, denominator: number, fallback: number = 0): number {
  if (!denominator || denominator === 0) return fallback
  return numerator / denominator
}

export function maskTrackingKey(key: string): string {
  if (!key || key.length < 8) return key || ''
  return key.slice(0, 3) + '\u2022\u2022\u2022\u2022' + key.slice(-4)
}

export function getDateRange(preset: string): { from?: string; to?: string } {
  const now = new Date()
  const to = now.toISOString()
  if (preset === '7d') {
    const from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()
    return { from, to }
  }
  if (preset === '30d') {
    const from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString()
    return { from, to }
  }
  return {}
}

export const variantStatusColors: Record<string, string> = {
  DRAFT: 'bg-zinc-500/20 text-zinc-400',
  ACTIVE: 'bg-green-500/20 text-green-400',
  PAUSED: 'bg-amber-500/20 text-amber-400',
  ARCHIVED: 'bg-zinc-600/20 text-zinc-500',
}

export const testTypeLabels: Record<string, string> = {
  HEADLINE_TEST: 'Headline Test',
  ANGLE_TEST: 'Angle Test',
  OFFER_TEST: 'Offer Test',
  PRICE_TEST: 'Price Test',
  HERO_IMAGE_TEST: 'Hero Image Test',
  CTA_TEST: 'CTA Test',
}

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, request } from '../lib/api'
import { formatCurrency, formatNumber, formatPercent, variantStatusColors } from '../lib/format'
import type { Campaign, ExperimentAnalysis, LandingVariant, VariantPerformance } from '../types'

interface Props {
  campaign: Campaign
}

type WinnerAnalysis = ExperimentAnalysis & {
  minimum_sessions_per_variant?: number
  minimum_purchases_per_variant?: number
  leader_variant_id?: string
  runner_variant_id?: string
}

export function CampaignExperimentsTab({ campaign }: Props) {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', clone_from_variant_id: '' as string | null })
  const [editingTraffic, setEditingTraffic] = useState(false)
  const [trafficWeights, setTrafficWeights] = useState<Record<string, number>>({})
  const [archiveConfirmId, setArchiveConfirmId] = useState<string | null>(null)

  const invalidateExperimentQueries = () => {
    queryClient.invalidateQueries({ queryKey: ['campaign-variants', campaign.id] })
    queryClient.invalidateQueries({ queryKey: ['campaign-variant-perf', campaign.id] })
    queryClient.invalidateQueries({ queryKey: ['campaign-experiment-winner', campaign.id] })
  }

  const { data: variants = [], isLoading } = useQuery({
    queryKey: ['campaign-variants', campaign.id],
    queryFn: () => api.variants.list(campaign.id),
  })

  const { data: variantPerf } = useQuery({
    queryKey: ['campaign-variant-perf', campaign.id],
    queryFn: () => api.performance.getVariants(campaign.id),
  })

  const { data: winner, isLoading: winnerLoading } = useQuery<WinnerAnalysis>({
    queryKey: ['campaign-experiment-winner', campaign.id],
    queryFn: () => request<WinnerAnalysis>(`/campaigns/${campaign.id}/performance/winner`),
  })

  const createMutation = useMutation({
    mutationFn: () => api.variants.create(campaign.id, {
      name: createForm.name,
      clone_from_variant_id: createForm.clone_from_variant_id || null,
    }),
    onSuccess: () => {
      invalidateExperimentQueries()
      setShowCreate(false)
      setCreateForm({ name: '', clone_from_variant_id: null })
    },
  })

  const updateTrafficMutation = useMutation({
    mutationFn: () => api.variants.updateTraffic(campaign.id, trafficWeights),
    onSuccess: () => {
      invalidateExperimentQueries()
      setEditingTraffic(false)
    },
  })

  const archiveMutation = useMutation({
    mutationFn: (variantId: string) => api.variants.update(campaign.id, variantId, { status: 'ARCHIVED' }),
    onSuccess: () => {
      invalidateExperimentQueries()
      setArchiveConfirmId(null)
    },
  })

  const pauseMutation = useMutation({
    mutationFn: ({ variantId, status }: { variantId: string; status: string }) =>
      api.variants.update(campaign.id, variantId, { status }),
    onSuccess: invalidateExperimentQueries,
  })

  if (isLoading) {
    return <div className="text-center py-12 text-zinc-400">Loading experiment variants...</div>
  }

  const activeVariants = variants.filter((variant: LandingVariant) => variant.status !== 'ARCHIVED')
  const perfMap: Record<string, VariantPerformance> = {}
  variantPerf?.variants?.forEach((variant: VariantPerformance) => {
    if (variant.variant_id) perfMap[variant.variant_id] = variant
  })

  const startEditTraffic = () => {
    const weights: Record<string, number> = {}
    activeVariants.forEach((variant: LandingVariant) => {
      weights[variant.id] = variant.traffic_weight || 0
    })
    setTrafficWeights(weights)
    setEditingTraffic(true)
  }

  const currentTrafficTotal = activeVariants.reduce(
    (sum: number, variant: LandingVariant) => sum + (variant.traffic_weight || 0),
    0,
  )
  const editedTrafficTotal = Object.values(trafficWeights).reduce((sum, weight) => sum + weight, 0)
  const trafficDraftValid = Math.abs(editedTrafficTotal - 100) < 0.01
  const hasTraffic = activeVariants.some(
    (variant: LandingVariant) => variant.status === 'ACTIVE' && variant.traffic_weight > 0,
  )

  const confirmedWinner = winner?.status === 'leader' && winner.variant_id
    ? perfMap[winner.variant_id]
    : undefined
  const confirmedWinnerVariant = winner?.status === 'leader' && winner.variant_id
    ? activeVariants.find((variant: LandingVariant) => variant.id === winner.variant_id)
    : undefined
  const winnerLabel = confirmedWinnerVariant
    ? `${confirmedWinnerVariant.variant_key} · ${confirmedWinnerVariant.name}`
    : winner?.variant_name || confirmedWinner?.variant_name || 'Winning variant'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-zinc-100">Experiments</h3>
          <p className="mt-1 text-xs text-zinc-500">
            Traffic is attributed by variant and purchases are verified from Shopify orders.
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-secondary">+ Create Variant</button>
      </div>

      {activeVariants.length >= 2 && (
        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
              hasTraffic ? 'bg-green-500/20 text-green-400' : 'bg-zinc-500/20 text-zinc-400'
            }`}>
              {hasTraffic ? 'Running' : 'No traffic'}
            </span>
            <span className="text-xs text-zinc-500">
              Traffic split: {activeVariants.map((variant: LandingVariant) => `${variant.variant_key} ${variant.traffic_weight || 0}%`).join(' / ')}
            </span>
            {Math.abs(currentTrafficTotal - 100) >= 0.01 && (
              <span className="text-xs text-amber-400">Configured total: {currentTrafficTotal}%</span>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-sm mb-4">
            {activeVariants.map((variant: LandingVariant) => {
              const performance = perfMap[variant.id]
              return (
                <div key={variant.id} className="bg-zinc-700/50 rounded-lg p-3">
                  <div className="font-medium text-zinc-100">{variant.variant_key} · {variant.name}</div>
                  <div className="text-zinc-400 text-xs mt-1">
                    {performance ? `${formatNumber(performance.sessions)} sessions · ${formatNumber(performance.purchases)} purchases` : 'No attributed sessions'}
                  </div>
                </div>
              )
            })}
          </div>

          {winnerLoading ? (
            <div className="p-4 bg-zinc-700/50 rounded-lg text-sm text-zinc-400">
              Calculating statistical significance...
            </div>
          ) : confirmedWinner ? (
            <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
              <div className="text-xs font-medium text-green-400 uppercase tracking-wide mb-1">
                Statistically significant winner
              </div>
              <p className="text-sm text-zinc-200">
                {winnerLabel} is winning at {formatPercent(confirmedWinner.conversion_rate)} conversion.
                {typeof winner?.lift === 'number' && ` Lift: ${winner.lift >= 0 ? '+' : ''}${winner.lift.toFixed(1)}%.`}
                {typeof winner?.confidence === 'number' && ` Confidence: ${(winner.confidence * 100).toFixed(1)}%.`}
              </p>
            </div>
          ) : (
            <div className="p-4 bg-zinc-700/50 border border-zinc-700 rounded-lg">
              <div className="text-xs font-medium text-zinc-300 uppercase tracking-wide mb-1">
                Collecting evidence
              </div>
              <p className="text-sm text-zinc-400">
                {winner?.reason || 'More attributed traffic is needed before Velnio can call a winner.'}
              </p>
              {(winner?.minimum_sessions_per_variant || winner?.minimum_purchases_per_variant) && (
                <p className="mt-2 text-xs text-zinc-500">
                  Minimum gate: {winner.minimum_sessions_per_variant ?? 0} sessions and {winner.minimum_purchases_per_variant ?? 0} purchases per variant, plus statistical significance.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {activeVariants.length === 0 ? (
        <div className="bg-zinc-800 rounded-xl p-6 text-center py-12 border border-zinc-700">
          <p className="text-zinc-400 mb-4">No variants yet. Generate a landing or create a variant to start experimenting.</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary">+ Create Variant</button>
        </div>
      ) : (
        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-zinc-100">Variants</h4>
            {activeVariants.length >= 2 && (
              <button onClick={startEditTraffic} className="btn-ghost text-xs">
                Manage Traffic
              </button>
            )}
          </div>

          {editingTraffic && (
            <div className="mb-4 p-4 bg-zinc-700/50 rounded-lg space-y-3">
              <div className="text-xs text-zinc-400 mb-2">Traffic weights must sum to 100%</div>
              {activeVariants.map((variant: LandingVariant) => (
                <div key={variant.id} className="flex items-center gap-3">
                  <span className="text-sm text-zinc-300 min-w-28">{variant.variant_key} · {variant.name}</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="5"
                    className="input w-24"
                    value={trafficWeights[variant.id] ?? 0}
                    onChange={(event) => setTrafficWeights({
                      ...trafficWeights,
                      [variant.id]: Number(event.target.value),
                    })}
                  />
                  <span className="text-xs text-zinc-500">%</span>
                </div>
              ))}
              <div className="flex items-center gap-3 pt-2">
                <span className="text-xs text-zinc-400">Total: {editedTrafficTotal}%</span>
                {!trafficDraftValid && <span className="text-xs text-red-400">Must equal 100%</span>}
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={() => setEditingTraffic(false)} className="btn-ghost text-xs">Cancel</button>
                <button
                  onClick={() => updateTrafficMutation.mutate()}
                  className="btn-primary text-xs"
                  disabled={updateTrafficMutation.isPending || !trafficDraftValid}
                >
                  {updateTrafficMutation.isPending ? 'Saving...' : 'Save Traffic Split'}
                </button>
              </div>
              {updateTrafficMutation.isError && (
                <p className="text-xs text-red-400">{updateTrafficMutation.error.message}</p>
              )}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-700">
                  <th className="text-left py-2 px-3 text-xs font-medium text-zinc-500">Variant</th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-zinc-500">Status</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Traffic</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Sessions</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Purchases</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">CVR</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Revenue</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeVariants.map((variant: LandingVariant) => {
                  const performance = perfMap[variant.id]
                  const isWinner = winner?.status === 'leader' && winner.variant_id === variant.id
                  return (
                    <tr key={variant.id} className={`border-b border-zinc-700/50 last:border-0 ${isWinner ? 'bg-green-500/5' : ''}`}>
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <span className="text-zinc-100 font-medium">{variant.variant_key}</span>
                          <span className="text-zinc-400">{variant.name}</span>
                          {isWinner && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-500/20 text-green-400">
                              Winner
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${variantStatusColors[variant.status] || ''}`}>
                          {variant.status}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right text-zinc-300">{variant.traffic_weight || 0}%</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{performance ? formatNumber(performance.sessions) : '-'}</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{performance ? formatNumber(performance.purchases) : '-'}</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{performance ? formatPercent(performance.conversion_rate) : '-'}</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{performance ? formatCurrency(performance.revenue, campaign.currency) : '-'}</td>
                      <td className="py-2 px-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {variant.status === 'ACTIVE' && (
                            <button
                              onClick={() => pauseMutation.mutate({ variantId: variant.id, status: 'PAUSED' })}
                              className="text-xs px-2 py-1 text-zinc-400 hover:text-amber-400 transition-colors"
                            >
                              Pause
                            </button>
                          )}
                          {variant.status === 'PAUSED' && (
                            <button
                              onClick={() => pauseMutation.mutate({ variantId: variant.id, status: 'ACTIVE' })}
                              className="text-xs px-2 py-1 text-zinc-400 hover:text-green-400 transition-colors"
                            >
                              Activate
                            </button>
                          )}
                          <button
                            onClick={() => setArchiveConfirmId(variant.id)}
                            className="text-xs px-2 py-1 text-zinc-400 hover:text-red-400 transition-colors"
                          >
                            Archive
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-zinc-800 rounded-xl p-6 w-full max-w-md border border-zinc-700">
            <h3 className="text-lg font-semibold text-zinc-100 mb-4">Create Variant</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Variant Name</label>
                <input
                  className="input"
                  placeholder="e.g. Benefit-led hero"
                  value={createForm.name}
                  onChange={(event) => setCreateForm({ ...createForm, name: event.target.value })}
                />
              </div>
              {variants.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Clone from</label>
                  <select
                    className="input"
                    value={createForm.clone_from_variant_id || ''}
                    onChange={(event) => setCreateForm({
                      ...createForm,
                      clone_from_variant_id: event.target.value || null,
                    })}
                  >
                    <option value="">None (create empty)</option>
                    {variants.map((variant: LandingVariant) => (
                      <option key={variant.id} value={variant.id}>{variant.variant_key} · {variant.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            {createMutation.isError && (
              <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                {createMutation.error.message || 'Failed to create variant'}
              </div>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => {
                  setShowCreate(false)
                  setCreateForm({ name: '', clone_from_variant_id: null })
                }}
                className="btn-ghost"
              >
                Cancel
              </button>
              <button
                onClick={() => createMutation.mutate()}
                className="btn-primary"
                disabled={createMutation.isPending || !createForm.name.trim()}
              >
                {createMutation.isPending ? 'Creating...' : 'Create Draft Variant'}
              </button>
            </div>
          </div>
        </div>
      )}

      {archiveConfirmId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-zinc-800 rounded-xl p-6 w-full max-w-sm border border-zinc-700">
            <h3 className="text-lg font-semibold text-zinc-100 mb-2">Archive this variant?</h3>
            <p className="text-sm text-zinc-400 mb-6">Historical performance data will remain available.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setArchiveConfirmId(null)} className="btn-ghost">Cancel</button>
              <button
                onClick={() => archiveMutation.mutate(archiveConfirmId)}
                className="px-4 py-2.5 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-500 transition-colors"
                disabled={archiveMutation.isPending}
              >
                {archiveMutation.isPending ? 'Archiving...' : 'Archive'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

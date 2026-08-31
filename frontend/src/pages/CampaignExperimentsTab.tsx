import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { formatCurrency, formatNumber, formatPercent, variantStatusColors } from '../lib/format'
import type { Campaign, LandingVariant, VariantPerformance } from '../types'

interface Props {
  campaign: Campaign
}

export function CampaignExperimentsTab({ campaign }: Props) {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', clone_from_variant_id: '' as string | null })
  const [editingTraffic, setEditingTraffic] = useState(false)
  const [trafficWeights, setTrafficWeights] = useState<Record<string, number>>({})
  const [archiveConfirmId, setArchiveConfirmId] = useState<string | null>(null)

  const { data: variants = [], isLoading } = useQuery({
    queryKey: ['campaign-variants', campaign.id],
    queryFn: () => api.variants.list(campaign.id),
  })

  const { data: variantPerf } = useQuery({
    queryKey: ['campaign-variant-perf', campaign.id],
    queryFn: () => api.performance.getVariants(campaign.id),
  })

  const createMutation = useMutation({
    mutationFn: () => api.variants.create(campaign.id, {
      name: createForm.name,
      clone_from_variant_id: createForm.clone_from_variant_id || null,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign-variants', campaign.id] })
      setShowCreate(false)
      setCreateForm({ name: '', clone_from_variant_id: null })
    },
  })

  const updateTrafficMutation = useMutation({
    mutationFn: () => api.variants.updateTraffic(campaign.id, trafficWeights),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign-variants', campaign.id] })
      queryClient.invalidateQueries({ queryKey: ['campaign-variant-perf', campaign.id] })
      setEditingTraffic(false)
    },
  })

  const archiveMutation = useMutation({
    mutationFn: (variantId: string) => api.variants.update(campaign.id, variantId, { status: 'ARCHIVED' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign-variants', campaign.id] })
      setArchiveConfirmId(null)
    },
  })

  const pauseMutation = useMutation({
    mutationFn: ({ variantId, status }: { variantId: string; status: string }) =>
      api.variants.update(campaign.id, variantId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-variants', campaign.id] }),
  })

  if (isLoading) {
    return <div className="text-center py-12 text-zinc-400">Loading experiment variants...</div>
  }

  const activeVariants = variants.filter((v: LandingVariant) => v.status !== 'ARCHIVED')
  const perfMap: Record<string, VariantPerformance> = {}
  if (variantPerf?.variants) {
    variantPerf.variants.forEach((v: VariantPerformance) => {
      if (v.variant_id) perfMap[v.variant_id] = v
    })
  }

  const totalTraffic = activeVariants.reduce((sum: number, v: LandingVariant) => sum + (v.traffic_weight || 0), 0)
  const trafficValid = Math.abs(totalTraffic - 100) < 0.01

  const startEditTraffic = () => {
    const w: Record<string, number> = {}
    activeVariants.forEach((v: LandingVariant) => { w[v.id] = v.traffic_weight || 0 })
    setTrafficWeights(w)
    setEditingTraffic(true)
  }

  const leader = variantPerf?.variants?.reduce((best: VariantPerformance | null, v: VariantPerformance) => {
    if (!best || v.conversion_rate > best.conversion_rate) return v
    return best
  }, null)

  const controlPerf = variantPerf?.variants?.find((v: VariantPerformance) => v.variant_key === 'A')
  const lift = leader && controlPerf && controlPerf.conversion_rate > 0
    ? ((leader.conversion_rate - controlPerf.conversion_rate) / controlPerf.conversion_rate * 100)
    : null

  const hasTraffic = activeVariants.some((v: LandingVariant) => v.traffic_weight > 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-zinc-100">Experiments</h3>
        <button onClick={() => setShowCreate(true)} className="btn-secondary">+ Create Variant</button>
      </div>

      {/* Experiment Summary */}
      {activeVariants.length >= 2 && (
        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <div className="flex items-center gap-3 mb-3">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
              hasTraffic ? 'bg-green-500/20 text-green-400' : 'bg-zinc-500/20 text-zinc-400'
            }`}>
              {hasTraffic ? 'Running' : 'No traffic'}
            </span>
            <span className="text-xs text-zinc-500">
              Traffic split: {activeVariants.map((v: LandingVariant) => `${v.variant_key} ${v.traffic_weight || 0}%`).join(' / ')}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm mb-4">
            {activeVariants.map((v: LandingVariant) => {
              const p = perfMap[v.id]
              return (
                <div key={v.id} className="bg-zinc-700/50 rounded-lg p-3">
                  <div className="font-medium text-zinc-100">{v.variant_key} &middot; {v.name}</div>
                  <div className="text-zinc-400 text-xs mt-1">
                    {p ? `${formatNumber(p.sessions)} sessions` : 'No sessions'}
                  </div>
                </div>
              )
            })}
          </div>

          {leader && leader.variant_key !== 'A' && lift != null && (
            <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
              <div className="text-xs font-medium text-green-400 uppercase tracking-wide mb-1">Analysis</div>
              <p className="text-sm text-zinc-200">
                Variant {leader.variant_name || leader.variant_key} is currently leading with a{' '}
                {formatPercent(leader.conversion_rate)} conversion rate vs {formatPercent(controlPerf?.conversion_rate || 0)}.
                {lift > 0 && ` Lift: +${lift.toFixed(0)}%`}
              </p>
            </div>
          )}

          {leader && leader.variant_key === 'A' && (
            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <div className="text-xs font-medium text-blue-400 uppercase tracking-wide mb-1">Analysis</div>
              <p className="text-sm text-zinc-200">
                Control (A) is currently the best performer at {formatPercent(controlPerf?.conversion_rate || 0)} conversion rate.
                Consider testing new variants to find a winning combination.
              </p>
            </div>
          )}

          {!leader && (
            <div className="p-4 bg-zinc-700/50 rounded-lg">
              <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-1">Analysis</div>
              <p className="text-sm text-zinc-400">More traffic needed to identify a leader.</p>
            </div>
          )}
        </div>
      )}

      {/* Variants Table */}
      {activeVariants.length === 0 ? (
        <div className="bg-zinc-800 rounded-xl p-6 text-center py-12 border border-zinc-700">
          <p className="text-zinc-400 mb-4">No variants yet. Create your first variant to start experimenting.</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary">+ Create Variant</button>
        </div>
      ) : (
        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-zinc-100">Variants</h4>
            {activeVariants.length >= 2 && (
              <button onClick={startEditTraffic} className="btn-ghost text-xs">
                {editingTraffic ? '' : 'Manage Traffic'}
              </button>
            )}
          </div>

          {editingTraffic && (
            <div className="mb-4 p-4 bg-zinc-700/50 rounded-lg space-y-3">
              <div className="text-xs text-zinc-400 mb-2">Traffic weights must sum to 100%</div>
              {activeVariants.map((v: LandingVariant) => (
                <div key={v.id} className="flex items-center gap-3">
                  <span className="text-sm text-zinc-300 w-16">{v.variant_key} &middot; {v.name}</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="5"
                    className="input w-24"
                    value={trafficWeights[v.id] ?? 0}
                    onChange={(e) => setTrafficWeights({ ...trafficWeights, [v.id]: Number(e.target.value) })}
                  />
                  <span className="text-xs text-zinc-500">%</span>
                </div>
              ))}
              <div className="flex items-center gap-3 pt-2">
                <span className="text-xs text-zinc-400">Total: {Object.values(trafficWeights).reduce((a, b) => a + b, 0)}%</span>
                {!trafficValid && <span className="text-xs text-red-400">Must equal 100%</span>}
              </div>
              <div className="flex gap-2 pt-1">
                <button onClick={() => setEditingTraffic(false)} className="btn-ghost text-xs">Cancel</button>
                <button
                  onClick={() => updateTrafficMutation.mutate()}
                  className="btn-primary text-xs"
                  disabled={updateTrafficMutation.isPending || !trafficValid}
                >
                  {updateTrafficMutation.isPending ? 'Saving...' : 'Save Traffic Split'}
                </button>
              </div>
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
                {activeVariants.map((v: LandingVariant) => {
                  const p = perfMap[v.id]
                  const isLeader = leader && leader.variant_id === v.id
                  return (
                    <tr key={v.id} className={`border-b border-zinc-700/50 last:border-0 ${isLeader ? 'bg-green-500/5' : ''}`}>
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <span className="text-zinc-100 font-medium">{v.variant_key}</span>
                          <span className="text-zinc-400">{v.name}</span>
                          {isLeader && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-500/20 text-green-400">
                              Current leader
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${variantStatusColors[v.status] || ''}`}>
                          {v.status}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right text-zinc-300">{v.traffic_weight || 0}%</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{p ? formatNumber(p.sessions) : '-'}</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{p ? formatNumber(p.purchases) : '-'}</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{p ? formatPercent(p.conversion_rate) : '-'}</td>
                      <td className="py-2 px-3 text-right text-zinc-300">{p ? formatCurrency(p.revenue, campaign.currency) : '-'}</td>
                      <td className="py-2 px-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {v.status === 'ACTIVE' && (
                            <button
                              onClick={() => pauseMutation.mutate({ variantId: v.id, status: 'PAUSED' })}
                              className="text-xs px-2 py-1 text-zinc-400 hover:text-amber-400 transition-colors"
                              title="Pause"
                            >
                              Pause
                            </button>
                          )}
                          {v.status === 'PAUSED' && (
                            <button
                              onClick={() => pauseMutation.mutate({ variantId: v.id, status: 'ACTIVE' })}
                              className="text-xs px-2 py-1 text-zinc-400 hover:text-green-400 transition-colors"
                              title="Activate"
                            >
                              Activate
                            </button>
                          )}
                          <button
                            onClick={() => setArchiveConfirmId(v.id)}
                            className="text-xs px-2 py-1 text-zinc-400 hover:text-red-400 transition-colors"
                            title="Archive"
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

      {/* Create Variant Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-zinc-800 rounded-xl p-6 w-full max-w-md border border-zinc-700">
            <h3 className="text-lg font-semibold text-zinc-100 mb-4">Create Variant</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Variant Name</label>
                <input
                  className="input"
                  placeholder="e.g. Pet Hair Hook B"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                />
              </div>
              {variants.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Clone from</label>
                  <select
                    className="input"
                    value={createForm.clone_from_variant_id || ''}
                    onChange={(e) => setCreateForm({ ...createForm, clone_from_variant_id: e.target.value || null })}
                  >
                    <option value="">None (create empty)</option>
                    {variants.map((v: LandingVariant) => (
                      <option key={v.id} value={v.id}>{v.variant_key} &middot; {v.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            {createMutation.isError && (
              <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                {createMutation.error?.message || 'Failed to create variant'}
              </div>
            )}
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => { setShowCreate(false); setCreateForm({ name: '', clone_from_variant_id: null }) }} className="btn-ghost">
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

      {/* Archive Confirm */}
      {archiveConfirmId && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
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

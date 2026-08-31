import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { formatCurrency, formatNumber, formatPercent, getDateRange } from '../lib/format'
import type { Campaign, CampaignPerformance, PerformanceTimelinePoint, VariantPerformance, AnglePerformance, CampaignPerformanceInsight } from '../types'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface Props {
  campaign: Campaign
}

export function CampaignPerformanceTab({ campaign }: Props) {
  const queryClient = useQueryClient()
  const [dateRange, setDateRange] = useState('all')
  const [chartMetric, setChartMetric] = useState<'sessions' | 'purchases' | 'revenue'>('sessions')

  const range = getDateRange(dateRange)

  const { data: perf, isLoading: perfLoading } = useQuery({
    queryKey: ['campaign-performance', campaign.id, dateRange],
    queryFn: () => api.performance.getCampaign(campaign.id, range.from, range.to),
    enabled: true,
  })

  const { data: timelineData } = useQuery({
    queryKey: ['campaign-timeline', campaign.id, dateRange],
    queryFn: () => api.performance.getTimeline(campaign.id, range.from, range.to),
    enabled: true,
  })

  const { data: variantPerf } = useQuery({
    queryKey: ['campaign-variant-perf', campaign.id],
    queryFn: () => api.performance.getVariants(campaign.id),
    enabled: true,
  })

  const { data: anglePerf } = useQuery({
    queryKey: ['campaign-angle-perf', campaign.id],
    queryFn: () => api.performance.getAngles(campaign.id),
    enabled: true,
  })

  const analyzeMutation = useMutation({
    mutationFn: () => api.performance.analyze(campaign.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-insight', campaign.id] }),
  })

  const demoMutation = useMutation({
    mutationFn: () => api.demo.generateEvents(campaign.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign-performance', campaign.id] })
      queryClient.invalidateQueries({ queryKey: ['campaign-timeline', campaign.id] })
      queryClient.invalidateQueries({ queryKey: ['campaign-variant-perf', campaign.id] })
    },
  })

  const p: CampaignPerformance = perf || { visitors: 0, sessions: 0, page_views: 0, cta_clicks: 0, add_to_carts: 0, checkouts: 0, purchases: 0, revenue: 0, currency: campaign.currency || 'USD', ctr: 0, atc_rate: 0, checkout_rate: 0, conversion_rate: 0, revenue_per_visitor: 0, aov: 0 }
  const timeline: PerformanceTimelinePoint[] = timelineData?.timeline || []
  const hasData = p.sessions > 0

  const kpis = [
    { label: 'Visitors', value: formatNumber(p.visitors) },
    { label: 'Sessions', value: formatNumber(p.sessions) },
    { label: 'Purchases', value: formatNumber(p.purchases) },
    { label: 'Revenue', value: formatCurrency(p.revenue, p.currency) },
    { label: 'Conversion Rate', value: formatPercent(p.conversion_rate) },
    { label: 'AOV', value: formatCurrency(p.aov, p.currency) },
  ]

  const optionalKpis = [
    { label: 'CTR', value: formatPercent(p.ctr), show: p.cta_clicks > 0 },
    { label: 'Add to Cart Rate', value: formatPercent(p.atc_rate), show: p.add_to_carts > 0 },
    { label: 'Checkout Rate', value: formatPercent(p.checkout_rate), show: p.checkouts > 0 },
  ]

  const funnelStages = [
    { label: 'Sessions', count: p.sessions, key: 'sessions' },
    { label: 'CTA Click', count: p.cta_clicks, key: 'cta' },
    { label: 'Add to Cart', count: p.add_to_carts, key: 'atc' },
    { label: 'Checkout', count: p.checkouts, key: 'checkout' },
    { label: 'Purchase', count: p.purchases, key: 'purchase' },
  ]

  if (perfLoading) {
    return <div className="text-center py-12 text-zinc-400">Loading performance data...</div>
  }

  if (!hasData) {
    return (
      <div className="space-y-6">
        <div className="bg-zinc-800 rounded-xl p-6 text-center py-16">
          <div className="text-4xl mb-4 text-zinc-600">&#128200;</div>
          <h3 className="text-lg font-semibold text-zinc-100 mb-2">No performance data yet</h3>
          <p className="text-zinc-400 max-w-md mx-auto mb-6">
            Your campaign hasn't received tracked traffic yet. Once visitors start interacting with your campaign, Velnio will show conversion metrics here.
          </p>
          <div className="space-y-3">
            <button onClick={() => demoMutation.mutate()} className="btn-secondary" disabled={demoMutation.isPending}>
              {demoMutation.isPending ? 'Generating...' : 'Generate demo traffic'}
            </button>
            <p className="text-xs text-zinc-600 italic">Development only</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-zinc-100">Performance</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Date range:</span>
          {['7d', '30d', 'all'].map((r) => (
            <button
              key={r}
              onClick={() => setDateRange(r)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                dateRange === r ? 'bg-indigo-600 text-white' : 'bg-zinc-700 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {r === '7d' ? 'Last 7 days' : r === '30d' ? 'Last 30 days' : 'All time'}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-zinc-800 rounded-xl p-4 border border-zinc-700">
            <div className="text-xs text-zinc-500 mb-1">{kpi.label}</div>
            <div className="text-lg font-bold text-zinc-100">{kpi.value}</div>
          </div>
        ))}
      </div>

      {optionalKpis.some((k) => k.show) && (
        <div className="grid grid-cols-3 gap-3">
          {optionalKpis.filter((k) => k.show).map((kpi) => (
            <div key={kpi.label} className="bg-zinc-800 rounded-xl p-4 border border-zinc-700">
              <div className="text-xs text-zinc-500 mb-1">{kpi.label}</div>
              <div className="text-lg font-bold text-zinc-100">{kpi.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Funnel */}
      <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
        <h4 className="font-medium text-zinc-100 mb-4">Funnel</h4>
        <div className="space-y-1">
          {funnelStages.map((stage, i) => {
            const prevCount = i > 0 ? funnelStages[i - 1].count : null
            const rate = prevCount && prevCount > 0 ? ((stage.count / prevCount) * 100).toFixed(0) : null
            const widthPct = p.sessions > 0 ? Math.max((stage.count / p.sessions) * 100, 4) : 4
            return (
              <div key={stage.key}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-zinc-300">{stage.label}</span>
                  <span className="text-zinc-400">{formatNumber(stage.count)}</span>
                </div>
                <div className="w-full bg-zinc-700 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-indigo-600/80 h-full rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                    style={{ width: `${widthPct}%` }}
                  >
                    {widthPct > 15 && <span className="text-xs text-white font-medium">{formatNumber(stage.count)}</span>}
                  </div>
                </div>
                {i > 0 && rate && (
                  <div className="text-xs text-zinc-500 mt-0.5 mb-2">
                    &#8595; {rate}% from {funnelStages[i - 1].label}
                  </div>
                )}
                {i === 0 && <div className="mb-2" />}
              </div>
            )
          })}
        </div>
      </div>

      {/* Timeline Chart */}
      {timeline.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-zinc-100">Timeline</h4>
            <div className="flex gap-1">
              {([['sessions', 'Sessions'], ['purchases', 'Purchases'], ['revenue', 'Revenue']] as const).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setChartMetric(key)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    chartMetric === key ? 'bg-indigo-600 text-white' : 'bg-zinc-700 text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#71717a' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 11, fill: '#71717a' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px', fontSize: '12px' }}
                  labelStyle={{ color: '#a1a1aa' }}
                  formatter={(value: any, name: any) => {
                    if (chartMetric === 'revenue') return [formatCurrency(Number(value), p.currency), String(name)]
                    return [formatNumber(Number(value)), String(name)]
                  }}
                />
                <Line
                  type="monotone"
                  dataKey={chartMetric}
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={{ fill: '#6366f1', r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Variant Performance */}
      {variantPerf?.variants && variantPerf.variants.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <h4 className="font-medium text-zinc-100 mb-4">Variant Performance</h4>
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
                </tr>
              </thead>
              <tbody>
                {variantPerf.variants.map((v: VariantPerformance) => (
                  <tr key={v.variant_id} className="border-b border-zinc-700/50 last:border-0">
                    <td className="py-2 px-3">
                      <span className="text-zinc-100 font-medium">{v.variant_key}</span>
                      <span className="text-zinc-500 ml-2">{v.variant_name}</span>
                    </td>
                    <td className="py-2 px-3 text-zinc-400">{v.status}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{v.traffic_weight}%</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatNumber(v.sessions)}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatNumber(v.purchases)}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatPercent(v.conversion_rate)}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatCurrency(v.revenue, p.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Angle Performance */}
      {anglePerf?.angles && anglePerf.angles.length > 0 && (
        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <h4 className="font-medium text-zinc-100 mb-4">Selling Angle Performance</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-700">
                  <th className="text-left py-2 px-3 text-xs font-medium text-zinc-500">Angle</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Sessions</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Purchases</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">CVR</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-zinc-500">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {anglePerf.angles.map((a: AnglePerformance) => (
                  <tr key={a.angle_id} className="border-b border-zinc-700/50 last:border-0">
                    <td className="py-2 px-3 text-zinc-100 font-medium">{a.angle_name}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatNumber(a.sessions)}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatNumber(a.purchases)}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatPercent(a.conversion_rate)}</td>
                    <td className="py-2 px-3 text-right text-zinc-300">{formatCurrency(a.revenue, p.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AI Analysis */}
      <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h4 className="font-medium text-zinc-100">Velnio AI Analysis</h4>
            <p className="text-xs text-zinc-500 mt-1">AI-powered performance insights and recommendations</p>
          </div>
          <button
            onClick={() => analyzeMutation.mutate()}
            className="btn-secondary"
            disabled={analyzeMutation.isPending || p.sessions < 50}
          >
            {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze Performance'}
          </button>
        </div>

        {analyzeMutation.isError && (
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg text-sm text-amber-400">
            {analyzeMutation.error?.message?.includes('Insufficient data')
              ? 'Not enough data yet. Velnio needs more campaign traffic before generating a reliable performance analysis.'
              : analyzeMutation.error?.message?.includes('credits')
                ? 'Not enough credits. View your credit balance to continue.'
                : 'Analysis failed. Please try again.'}
          </div>
        )}

        {analyzeMutation.data && (
          <InsightDisplay insight={analyzeMutation.data as CampaignPerformanceInsight} />
        )}

        {!analyzeMutation.data && !analyzeMutation.isError && !analyzeMutation.isPending && (
          <p className="text-zinc-500 text-sm">
            {p.sessions < 50
              ? `Need at least 50 sessions for analysis (currently ${p.sessions}).`
              : 'Click "Analyze Performance" to get AI-powered insights about your campaign.'}
          </p>
        )}
      </div>
    </div>
  )
}

function InsightDisplay({ insight }: { insight: CampaignPerformanceInsight }) {
  return (
    <div className="space-y-4">
      {insight.summary && (
        <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
          <div className="text-xs font-medium text-indigo-400 uppercase tracking-wide mb-1">What we're seeing</div>
          <p className="text-sm text-zinc-200">{insight.summary}</p>
        </div>
      )}

      {insight.winning_pattern && (
        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
          <div className="text-xs font-medium text-green-400 uppercase tracking-wide mb-1">Strongest signal</div>
          <p className="text-sm text-zinc-200">{insight.winning_pattern}</p>
        </div>
      )}

      {insight.weak_points && insight.weak_points.length > 0 && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
          <div className="text-xs font-medium text-amber-400 uppercase tracking-wide mb-1">Weak points</div>
          <ul className="space-y-1">
            {insight.weak_points.map((wp, i) => (
              <li key={i} className="text-sm text-zinc-200">{wp}</li>
            ))}
          </ul>
        </div>
      )}

      {insight.recommended_actions && insight.recommended_actions.length > 0 && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <div className="text-xs font-medium text-blue-400 uppercase tracking-wide mb-1">Recommended next step</div>
          <ul className="space-y-1">
            {insight.recommended_actions.map((ra, i) => (
              <li key={i} className="text-sm text-zinc-200">{ra}</li>
            ))}
          </ul>
        </div>
      )}

      {insight.next_test_type && (
        <div className="p-4 bg-zinc-700/50 border border-zinc-600 rounded-lg">
          <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Next Test</div>
          <div className="text-sm font-semibold text-zinc-100 mb-1">{insight.next_test_type.replace(/_/g, ' ')}</div>
          {insight.next_test_hypothesis && (
            <p className="text-xs text-zinc-400 italic">"{insight.next_test_hypothesis}"</p>
          )}
        </div>
      )}

      <div className="flex items-center gap-4 text-xs text-zinc-500">
        {insight.confidence != null && (
          <span>Confidence: {(insight.confidence * 100).toFixed(0)}%</span>
        )}
        <span>Based on {formatNumber(insight.based_on_sessions)} sessions</span>
        {insight.generated_at && (
          <span>{new Date(insight.generated_at).toLocaleDateString()}</span>
        )}
      </div>
    </div>
  )
}

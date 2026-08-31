import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

const productStatusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  ANALYZING: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  ANALYZED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  READY: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  PUBLISHED: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  FAILED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

const campaignStatusColors: Record<string, string> = {
  DRAFT: 'bg-gray-500/20 text-gray-400',
  ANALYZING: 'bg-blue-500/20 text-blue-400',
  ANGLE_READY: 'bg-purple-500/20 text-purple-400',
  OFFER_READY: 'bg-indigo-500/20 text-indigo-400',
  LANDING_READY: 'bg-teal-500/20 text-teal-400',
  PUBLISHED: 'bg-green-500/20 text-green-400',
  FAILED: 'bg-red-500/20 text-red-400',
}

export function DashboardPage() {
  const { data: summary, isLoading: loadingSummary } = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard.summary })
  const { data: products = [], isLoading: loadingProducts } = useQuery({ queryKey: ['products'], queryFn: api.products.list })
  const { data: campaigns = [], isLoading: loadingCampaigns } = useQuery({ queryKey: ['campaigns'], queryFn: api.campaigns.list })

  const publishedCampaigns = campaigns.filter((c: any) => c.status === 'PUBLISHED').length
  const draftCampaigns = campaigns.filter((c: any) => c.status !== 'PUBLISHED' && c.status !== 'FAILED').length
  const failedCampaigns = campaigns.filter((c: any) => c.status === 'FAILED').length

  const cards = [
    { label: 'Products', value: summary?.total_products ?? 0 },
    { label: 'Analyzed', value: summary?.analyzed_products ?? 0 },
    { label: 'Landings', value: summary?.total_landings ?? 0 },
    { label: 'Published', value: summary?.published_products ?? 0 },
    { label: 'Credits', value: summary?.credits_remaining ?? 0 },
  ]

  const campaignCards = [
    { label: 'Total Campaigns', value: campaigns.length },
    { label: 'Published', value: publishedCampaigns },
    { label: 'In Progress', value: draftCampaigns },
    { label: 'Failed', value: failedCampaigns },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex gap-2">
          <Link to="/campaigns/new" className="btn-primary">New Campaign</Link>
          <Link to="/products/new" className="btn-primary">Launch Product</Link>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className="card">
            <div className="text-sm text-[var(--text-secondary)] mb-1">{c.label}</div>
            <div className="text-2xl font-bold">{loadingSummary ? '-' : c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {campaignCards.map((c) => (
          <div key={c.label} className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
            <div className="text-sm text-zinc-400 mb-1">{c.label}</div>
            <div className="text-2xl font-bold text-zinc-100">{loadingCampaigns ? '-' : c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Recent Products</h2>
            <Link to="/products" className="text-sm text-[var(--accent)] hover:underline">View all</Link>
          </div>
          {loadingProducts ? (
            <div className="text-sm text-[var(--text-secondary)] py-8 text-center">Loading...</div>
          ) : products.length === 0 ? (
            <div className="text-sm text-[var(--text-secondary)] py-8 text-center">
              No products yet. <Link to="/products/new" className="text-[var(--accent)] hover:underline">Create your first product</Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-color)]">
                    <th className="text-left text-xs font-medium text-[var(--text-tertiary)] py-3 px-4">Product</th>
                    <th className="text-left text-xs font-medium text-[var(--text-tertiary)] py-3 px-4">Country</th>
                    <th className="text-left text-xs font-medium text-[var(--text-tertiary)] py-3 px-4">Status</th>
                    <th className="text-left text-xs font-medium text-[var(--text-tertiary)] py-3 px-4">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {products.slice(0, 5).map((p: any) => (
                    <tr key={p.id} className="border-b border-[var(--border-color)] last:border-0 hover:bg-[var(--bg-secondary)]">
                      <td className="py-3 px-4">
                        <Link to={`/products/${p.id}`} className="font-medium text-sm hover:text-[var(--accent)]">{p.name}</Link>
                      </td>
                      <td className="py-3 px-4 text-sm text-[var(--text-secondary)]">{p.target_country}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${productStatusColors[p.status] || ''}`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-[var(--text-secondary)]">
                        {new Date(p.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-zinc-100">Recent Campaigns</h2>
            <Link to="/campaigns" className="text-sm text-indigo-400 hover:underline">View all</Link>
          </div>
          {loadingCampaigns ? (
            <div className="text-sm text-zinc-400 py-8 text-center">Loading...</div>
          ) : campaigns.length === 0 ? (
            <div className="text-sm text-zinc-400 py-8 text-center">
              No campaigns yet. <Link to="/campaigns/new" className="text-indigo-400 hover:underline">Create your first campaign</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {campaigns.slice(0, 5).map((c: any) => (
                <Link key={c.id} to={`/campaigns/${c.id}`} className="flex items-center justify-between p-3 rounded-lg hover:bg-zinc-700/50 transition-colors">
                  <div>
                    <h4 className="font-medium text-sm text-zinc-100">{c.name}</h4>
                    <p className="text-xs text-zinc-400">{c.target_country}</p>
                  </div>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${campaignStatusColors[c.status] || ''}`}>
                    {c.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

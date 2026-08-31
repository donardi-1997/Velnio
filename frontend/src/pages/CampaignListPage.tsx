import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-500/20 text-gray-400',
  ANALYZING: 'bg-blue-500/20 text-blue-400',
  ANGLE_READY: 'bg-purple-500/20 text-purple-400',
  OFFER_READY: 'bg-indigo-500/20 text-indigo-400',
  LANDING_READY: 'bg-teal-500/20 text-teal-400',
  PUBLISHED: 'bg-green-500/20 text-green-400',
  FAILED: 'bg-red-500/20 text-red-400',
}

export function CampaignListPage() {
  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: api.campaigns.list,
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Campaigns</h1>
        <Link to="/campaigns/new" className="btn-primary">Create Campaign</Link>
      </div>
      {isLoading ? (
        <div className="text-center py-12 text-zinc-400">Loading...</div>
      ) : campaigns.length === 0 ? (
        <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
          <p className="text-zinc-400 mb-4">No campaigns yet</p>
          <Link to="/campaigns/new" className="btn-primary">Create your first campaign</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {campaigns.map((c: any) => (
            <Link
              key={c.id}
              to={`/campaigns/${c.id}`}
              className="bg-zinc-800 rounded-xl p-6 flex items-center justify-between border border-zinc-700 hover:border-zinc-500 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div>
                  <h3 className="font-medium text-zinc-100">{c.name}</h3>
                  <p className="text-sm text-zinc-400">
                    {c.product?.name || c.product_id} &middot; {c.target_country}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {c.store?.name && (
                  <span className="text-sm text-zinc-400">{c.store.name}</span>
                )}
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[c.status] || ''}`}>
                  {c.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

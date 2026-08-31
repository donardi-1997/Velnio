import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'

export function StoresPage() {
  const queryClient = useQueryClient()
  const { data: stores = [], isLoading } = useQuery({ queryKey: ['stores'], queryFn: api.stores.list })
  const connectMutation = useMutation({
    mutationFn: () => api.stores.mockConnect({ name: 'My Shopify Store', shop_domain: 'my-store.myshopify.com' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stores'] }),
  })
  const disconnectMutation = useMutation({
    mutationFn: (id: string) => api.stores.disconnect(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stores'] }),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Stores</h1>
        <button onClick={() => connectMutation.mutate()} className="btn-primary" disabled={connectMutation.isPending}>
          {connectMutation.isPending ? 'Connecting...' : 'Connect Store'}
        </button>
      </div>
      {isLoading ? (
        <div className="text-center py-12">Loading...</div>
      ) : stores.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-[var(--text-secondary)] mb-4">No stores connected</p>
          <button onClick={() => connectMutation.mutate()} className="btn-primary" disabled={connectMutation.isPending}>
            Connect a Store
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {stores.map((s: any) => (
            <div key={s.id} className="card flex items-center justify-between">
              <div>
                <h3 className="font-medium">{s.name}</h3>
                <p className="text-sm text-[var(--text-secondary)]">{s.shop_domain} &middot; {s.platform}</p>
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${s.status === 'CONNECTED' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-600'}`}>
                  {s.status}
                </span>
                <button onClick={() => disconnectMutation.mutate(s.id)} className="btn-ghost text-sm text-red-500">Disconnect</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

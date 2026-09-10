import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api'
import { startShopifyOAuth } from '../lib/shopify'

export function StoresPage() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [shopDomain, setShopDomain] = useState('')
  const { data: stores = [], isLoading } = useQuery({ queryKey: ['stores'], queryFn: api.stores.list })

  const connectMutation = useMutation({
    mutationFn: async () => {
      const result = await startShopifyOAuth(shopDomain)
      window.location.assign(result.auth_url)
    },
  })
  const mockMutation = useMutation({
    mutationFn: () => api.stores.mockConnect({ name: 'Demo Shopify Store', shop_domain: 'demo-store.myshopify.com' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stores'] }),
  })
  const disconnectMutation = useMutation({
    mutationFn: (id: string) => api.stores.disconnect(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stores'] }),
  })

  const handleConnect = (event: React.FormEvent) => {
    event.preventDefault()
    if (!shopDomain.trim()) return
    connectMutation.mutate()
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Stores</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-2">
          Connect Shopify so Velnio can publish products and campaign pages to your store.
        </p>
      </div>

      {searchParams.get('shopify') === 'connected' && (
        <div className="mb-6 rounded-xl border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm text-green-500">
          Shopify connected successfully. Your onboarding progress has been updated.
        </div>
      )}

      <div className="card mb-8">
        <h2 className="font-semibold mb-2">Connect Shopify</h2>
        <p className="text-sm text-[var(--text-secondary)] mb-5">
          Enter your permanent <strong>myshopify.com</strong> domain. You will be redirected to Shopify to approve the requested permissions.
        </p>
        <form onSubmit={handleConnect} className="flex flex-col sm:flex-row gap-3">
          <input
            className="input flex-1"
            value={shopDomain}
            onChange={(event) => setShopDomain(event.target.value)}
            placeholder="your-store.myshopify.com"
            autoComplete="off"
            required
          />
          <button type="submit" className="btn-primary whitespace-nowrap" disabled={connectMutation.isPending}>
            {connectMutation.isPending ? 'Preparing Shopify...' : 'Connect with Shopify'}
          </button>
        </form>
        {connectMutation.isError && (
          <p className="text-sm text-red-500 mt-3">{connectMutation.error.message}</p>
        )}
        <p className="text-xs text-[var(--text-tertiary)] mt-4">
          Velnio stores Shopify credentials encrypted and never displays your access token.
        </p>
        {import.meta.env.DEV && (
          <div className="mt-5 pt-5 border-t border-[var(--border-color)]">
            <button onClick={() => mockMutation.mutate()} className="btn-ghost text-sm" disabled={mockMutation.isPending}>
              {mockMutation.isPending ? 'Connecting demo...' : 'Connect demo store (development only)'}
            </button>
          </div>
        )}
      </div>

      <h2 className="font-semibold mb-4">Connected stores</h2>
      {isLoading ? (
        <div className="text-center py-12 text-[var(--text-secondary)]">Loading...</div>
      ) : stores.length === 0 ? (
        <div className="card text-center py-12">
          <p className="font-medium">No stores connected yet</p>
          <p className="text-sm text-[var(--text-secondary)] mt-2">Connect your first Shopify store above to continue your first launch.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {stores.map((store: any) => (
            <div key={store.id} className="card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{store.name}</h3>
                  <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                    store.status === 'CONNECTED'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : store.status === 'ERROR'
                        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
                  }`}>
                    {store.status}
                  </span>
                </div>
                <p className="text-sm text-[var(--text-secondary)] mt-1">{store.shop_domain} · {store.currency} · {store.country}</p>
                {store.status === 'ERROR' && (
                  <p className="text-xs text-red-500 mt-1">Authorization needs attention. Reconnect the store above.</p>
                )}
              </div>
              <button
                onClick={() => disconnectMutation.mutate(store.id)}
                className="btn-ghost text-sm text-red-500 self-start sm:self-auto"
                disabled={disconnectMutation.isPending}
              >
                Disconnect
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

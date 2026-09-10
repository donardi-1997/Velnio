import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { GoogleDriveBrowser } from '../components/GoogleDriveBrowser'
import { useMe } from '../hooks/useAuth'
import { api } from '../lib/api'
import { metaAdsApi } from '../lib/metaAds'

export function SettingsPage() {
  const { data: user } = useMe()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [showDriveBrowser, setShowDriveBrowser] = useState(false)

  const { data: driveStatus } = useQuery({
    queryKey: ['drive-status'],
    queryFn: () => api.googleDrive.getStatus(),
  })

  const { data: metaStatus, isLoading: metaStatusLoading } = useQuery({
    queryKey: ['meta-ads-status'],
    queryFn: metaAdsApi.status,
  })

  const { data: metaAdAccounts = [], isLoading: metaAccountsLoading, error: metaAccountsError } = useQuery({
    queryKey: ['meta-ads-ad-accounts'],
    queryFn: metaAdsApi.adAccounts,
    enabled: Boolean(metaStatus?.connected && !metaStatus?.expired),
  })

  const disconnectMutation = useMutation({
    mutationFn: () => api.googleDrive.disconnect(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drive-status'] }),
  })

  const connectMutation = useMutation({
    mutationFn: () => api.googleDrive.connectMock(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drive-status'] }),
  })

  const connectMetaMutation = useMutation({
    mutationFn: async () => {
      if (metaStatus?.mode === 'mock') {
        await metaAdsApi.connectMock()
        return { redirecting: false }
      }
      const result = await metaAdsApi.startConnection()
      window.location.assign(result.auth_url)
      return { redirecting: true }
    },
    onSuccess: (result) => {
      if (!result.redirecting) {
        queryClient.invalidateQueries({ queryKey: ['meta-ads-status'] })
        queryClient.invalidateQueries({ queryKey: ['meta-ads-ad-accounts'] })
      }
    },
  })

  const disconnectMetaMutation = useMutation({
    mutationFn: metaAdsApi.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-ads-status'] })
      queryClient.removeQueries({ queryKey: ['meta-ads-ad-accounts'] })
    },
  })

  const metaCallbackStatus = searchParams.get('meta_ads')
  const metaError = connectMetaMutation.error instanceof Error
    ? connectMetaMutation.error.message
    : disconnectMetaMutation.error instanceof Error
      ? disconnectMetaMutation.error.message
      : null

  return (
    <div>
      <h1 className="text-2xl font-bold mb-8">Settings</h1>
      <div className="space-y-6 max-w-2xl">
        <div className="card">
          <h2 className="font-semibold mb-4">Account</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center gap-4 py-2 border-b border-[var(--border-color)]">
              <span className="text-sm text-[var(--text-secondary)]">Name</span>
              <span className="text-sm font-medium text-right">{user?.first_name} {user?.last_name}</span>
            </div>
            <div className="flex justify-between items-center gap-4 py-2 border-b border-[var(--border-color)]">
              <span className="text-sm text-[var(--text-secondary)]">Email</span>
              <span className="text-sm font-medium text-right break-all">{user?.email}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-[var(--text-secondary)]">Status</span>
              <span className="text-sm font-medium text-green-600">Active</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Google Drive</h2>
            {driveStatus?.connected && (
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Connected</span>
            )}
          </div>
          <div className="space-y-4">
            {driveStatus?.connected ? (
              <>
                <div className="flex justify-between items-center gap-4 py-2 border-b border-[var(--border-color)]">
                  <span className="text-sm text-[var(--text-secondary)]">Account</span>
                  <span className="text-sm font-medium text-right break-all">{driveStatus.google_email}</span>
                </div>
                <div className="flex justify-between items-center gap-4 py-2 border-b border-[var(--border-color)]">
                  <span className="text-sm text-[var(--text-secondary)]">Name</span>
                  <span className="text-sm font-medium text-right">{driveStatus.google_name}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-[var(--text-secondary)]">Status</span>
                  <span className="text-sm font-medium text-green-400">Active</span>
                </div>
                <div className="flex flex-col gap-2 pt-2 sm:flex-row">
                  <button
                    onClick={() => setShowDriveBrowser(!showDriveBrowser)}
                    className="btn-secondary text-sm"
                  >
                    {showDriveBrowser ? 'Hide Browser' : 'Browse Files'}
                  </button>
                  <button
                    onClick={() => disconnectMutation.mutate()}
                    className="text-sm text-red-400 hover:text-red-300 px-3 py-1.5"
                    disabled={disconnectMutation.isPending}
                  >
                    {disconnectMutation.isPending ? 'Disconnecting...' : 'Disconnect'}
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-zinc-400 mb-3">Connect your Google Drive to import images and documents.</p>
                <button
                  onClick={() => connectMutation.mutate()}
                  className="btn-primary"
                  disabled={connectMutation.isPending}
                >
                  {connectMutation.isPending ? 'Connecting...' : 'Connect Google Drive'}
                </button>
              </div>
            )}
          </div>
          {showDriveBrowser && driveStatus?.connected && (
            <div className="mt-4">
              <GoogleDriveBrowser onClose={() => setShowDriveBrowser(false)} />
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <h2 className="font-semibold">Meta Ads</h2>
              <p className="text-xs text-[var(--text-tertiary)] mt-1">Connect an ad account for campaign publishing and performance workflows.</p>
            </div>
            {metaStatus?.connected && !metaStatus.expired && (
              <span className="shrink-0 text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Connected</span>
            )}
            {metaStatus?.connected && metaStatus.expired && (
              <span className="shrink-0 text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">Reconnect</span>
            )}
          </div>

          {metaCallbackStatus === 'connected' && (
            <div className="mb-4 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-300">
              Meta Ads connected successfully.
            </div>
          )}
          {metaCallbackStatus === 'denied' && (
            <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
              Meta authorization was cancelled or denied. No connection was created.
            </div>
          )}
          {metaError && (
            <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {metaError}
            </div>
          )}

          {metaStatusLoading ? (
            <div className="py-6 text-sm text-zinc-400 text-center">Loading Meta Ads status...</div>
          ) : metaStatus?.connected ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-[var(--border-color)] p-3">
                  <div className="text-xs text-[var(--text-tertiary)]">Meta profile</div>
                  <div className="text-sm font-medium mt-1">{metaStatus.meta_user_name || 'Connected Meta user'}</div>
                  <div className="text-xs text-[var(--text-secondary)] mt-1 break-all">{metaStatus.meta_user_id}</div>
                </div>
                <div className="rounded-lg border border-[var(--border-color)] p-3">
                  <div className="text-xs text-[var(--text-tertiary)]">Access</div>
                  <div className={`text-sm font-medium mt-1 ${metaStatus.expired ? 'text-amber-400' : 'text-green-400'}`}>
                    {metaStatus.expired ? 'Expired — reconnect required' : 'Active'}
                  </div>
                  {metaStatus.expires_at && (
                    <div className="text-xs text-[var(--text-secondary)] mt-1">
                      Expires {new Date(metaStatus.expires_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>

              {!metaStatus.expired && (
                <div>
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <h3 className="text-sm font-medium">Available ad accounts</h3>
                    <span className="text-xs text-[var(--text-tertiary)]">{metaAdAccounts.length} found</span>
                  </div>
                  {metaAccountsLoading ? (
                    <div className="rounded-lg border border-[var(--border-color)] p-4 text-sm text-zinc-400 text-center">Loading ad accounts...</div>
                  ) : metaAccountsError instanceof Error ? (
                    <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{metaAccountsError.message}</div>
                  ) : metaAdAccounts.length === 0 ? (
                    <div className="rounded-lg border border-[var(--border-color)] p-4 text-sm text-zinc-400 text-center">No accessible Meta ad accounts were found.</div>
                  ) : (
                    <div className="space-y-2">
                      {metaAdAccounts.map((account) => (
                        <div key={account.id} className="rounded-lg border border-[var(--border-color)] p-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <div className="min-w-0">
                            <div className="text-sm font-medium truncate">{account.name}</div>
                            <div className="text-xs text-[var(--text-secondary)] mt-1">{account.id}</div>
                          </div>
                          <div className="flex flex-wrap gap-2 text-xs text-[var(--text-secondary)]">
                            {account.currency && <span className="rounded bg-zinc-700/60 px-2 py-1">{account.currency}</span>}
                            {account.timezone_name && <span className="rounded bg-zinc-700/60 px-2 py-1">{account.timezone_name}</span>}
                            <span className={`rounded px-2 py-1 ${account.account_status === 1 ? 'bg-green-500/10 text-green-400' : 'bg-zinc-700/60'}`}>
                              {account.account_status === 1 ? 'Active' : `Status ${account.account_status ?? 'unknown'}`}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="flex flex-col gap-2 pt-2 sm:flex-row">
                {metaStatus.expired && (
                  <button
                    onClick={() => connectMetaMutation.mutate()}
                    className="btn-primary text-sm"
                    disabled={connectMetaMutation.isPending}
                  >
                    {connectMetaMutation.isPending ? 'Connecting...' : 'Reconnect Meta Ads'}
                  </button>
                )}
                <button
                  onClick={() => disconnectMetaMutation.mutate()}
                  className="text-sm text-red-400 hover:text-red-300 px-3 py-1.5"
                  disabled={disconnectMetaMutation.isPending || connectMetaMutation.isPending}
                >
                  {disconnectMetaMutation.isPending ? 'Disconnecting...' : 'Disconnect'}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-5">
              <p className="text-sm text-zinc-400 mb-2">Authorize Velnio to discover the Meta ad accounts you can access.</p>
              <p className="text-xs text-zinc-500 mb-4">This phase only connects and reads account metadata. It does not create ads or spend budget.</p>
              <button
                onClick={() => connectMetaMutation.mutate()}
                className="btn-primary"
                disabled={connectMetaMutation.isPending || !metaStatus}
              >
                {connectMetaMutation.isPending ? 'Connecting...' : 'Connect Meta Ads'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

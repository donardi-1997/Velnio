import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { metaAdsApi, type MetaAdsCampaignPublication } from '../lib/metaAds'
import { MetaDeliveryConfigEditor } from './MetaDeliveryConfigEditor'

interface MetaAdsPublishPanelProps {
  campaignId: string
}

export function MetaAdsPublishPanel({ campaignId }: MetaAdsPublishPanelProps) {
  const queryClient = useQueryClient()
  const [selectedAccountId, setSelectedAccountId] = useState('')
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const statusQuery = useQuery({
    queryKey: ['meta-ads-status'],
    queryFn: metaAdsApi.status,
  })

  const accountsQuery = useQuery({
    queryKey: ['meta-ads-accounts'],
    queryFn: metaAdsApi.adAccounts,
    enabled: Boolean(statusQuery.data?.connected && !statusQuery.data?.expired),
  })

  const resourcesQuery = useQuery({
    queryKey: ['meta-ads-delivery-resources', selectedAccountId],
    queryFn: () => metaAdsApi.deliveryResources(selectedAccountId),
    enabled: Boolean(selectedAccountId && statusQuery.data?.connected && !statusQuery.data?.expired),
  })

  const publicationsQuery = useQuery({
    queryKey: ['meta-ads-publications', campaignId],
    queryFn: () => metaAdsApi.campaignPublications(campaignId),
  })

  const publishMutation = useMutation({
    mutationFn: (adAccountId: string) => metaAdsApi.publishCampaignPaused(campaignId, adAccountId),
    onMutate: () => setFeedback(null),
    onSuccess: (publication) => {
      queryClient.invalidateQueries({ queryKey: ['meta-ads-publications', campaignId] })
      setFeedback({
        type: 'success',
        message: publication.reused
          ? 'Existing paused Meta campaign reconciled. No duplicate campaign was created.'
          : 'Meta campaign created in PAUSED state. No Ad Set, ad, or budget was activated.',
      })
    },
    onError: (error: Error) => {
      setFeedback({
        type: 'error',
        message: error.message || 'Could not create the paused Meta campaign.',
      })
    },
  })

  const accounts = accountsQuery.data || []
  const publications = publicationsQuery.data || []
  const selectedAccount = accounts.find((account) => account.id === selectedAccountId)
  const activeAccount = selectedAccount?.account_status == null || selectedAccount?.account_status === 1
  const resources = resourcesQuery.data
  const hasPixel = Boolean(resources?.pixels.length)
  const hasPage = Boolean(resources?.pages.length)
  const deliveryPrerequisitesReady = hasPixel && hasPage
  const canPublish = Boolean(
    statusQuery.data?.connected &&
      !statusQuery.data?.expired &&
      selectedAccountId &&
      activeAccount &&
      !publishMutation.isPending,
  )

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-800 p-6 space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-zinc-100">Meta Ads</h3>
            {statusQuery.data?.connected && !statusQuery.data?.expired && (
              <span className="rounded-full bg-green-500/15 px-2 py-0.5 text-xs font-medium text-green-400">Connected</span>
            )}
            {statusQuery.data?.expired && (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-400">Reconnect required</span>
            )}
          </div>
          <p className="mt-1 max-w-2xl text-sm text-zinc-400">
            Create or reconcile the Meta Campaign layer only. Velnio always creates it as PAUSED in this phase.
          </p>
        </div>
        <Link to="/settings" className="btn-secondary text-sm whitespace-nowrap">
          Meta settings
        </Link>
      </div>

      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-200">
        No Ad Set, creative, ad, budget, or automatic activation is created here. Creating this paused campaign does not start ad delivery.
      </div>

      {statusQuery.isLoading ? (
        <p className="text-sm text-zinc-400">Checking Meta Ads connection...</p>
      ) : !statusQuery.data?.connected || statusQuery.data?.expired ? (
        <div className="rounded-lg border border-zinc-700 bg-zinc-900/40 p-4">
          <p className="text-sm text-zinc-300">
            {statusQuery.data?.expired
              ? 'The Meta Ads connection has expired. Reconnect it before publishing.'
              : 'Connect Meta Ads before publishing a campaign.'}
          </p>
          <Link to="/settings" className="mt-3 inline-flex text-sm font-medium text-indigo-400 hover:text-indigo-300">
            Open Settings
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="space-y-3">
            <label className="block text-sm font-medium text-zinc-300" htmlFor="meta-ad-account">
              Ad account
            </label>
            <select
              id="meta-ad-account"
              className="input"
              value={selectedAccountId}
              onChange={(event) => {
                setSelectedAccountId(event.target.value)
                setFeedback(null)
              }}
              disabled={accountsQuery.isLoading || publishMutation.isPending}
            >
              <option value="">Select an ad account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id} disabled={account.account_status != null && account.account_status !== 1}>
                  {account.name} ({account.id}){account.currency ? ` · ${account.currency}` : ''}
                  {account.account_status != null && account.account_status !== 1 ? ' · inactive' : ''}
                </option>
              ))}
            </select>
            {accountsQuery.isError && (
              <p className="text-sm text-red-400">Could not load Meta ad accounts. Check the connection in Settings.</p>
            )}
            {!accountsQuery.isLoading && !accountsQuery.isError && accounts.length === 0 && (
              <p className="text-sm text-amber-400">No accessible Meta ad accounts were returned by this connection.</p>
            )}
            {selectedAccount && (
              <div className="grid gap-2 rounded-lg border border-zinc-700 bg-zinc-900/40 p-3 text-sm sm:grid-cols-3">
                <div>
                  <span className="block text-xs uppercase tracking-wide text-zinc-500">Account</span>
                  <span className="text-zinc-200">{selectedAccount.name}</span>
                </div>
                <div>
                  <span className="block text-xs uppercase tracking-wide text-zinc-500">Currency</span>
                  <span className="text-zinc-200">{selectedAccount.currency || '—'}</span>
                </div>
                <div>
                  <span className="block text-xs uppercase tracking-wide text-zinc-500">Timezone</span>
                  <span className="text-zinc-200">{selectedAccount.timezone_name || '—'}</span>
                </div>
              </div>
            )}
          </div>

          {selectedAccountId && (
            <div className="rounded-lg border border-zinc-700 bg-zinc-900/40 p-4">
              <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-zinc-200">Delivery prerequisites</h4>
                  <p className="mt-1 text-xs text-zinc-500">Read-only discovery. Velnio does not modify these Meta resources.</p>
                </div>
                {!resourcesQuery.isLoading && !resourcesQuery.isError && (
                  <span className={`w-fit rounded-full px-2 py-0.5 text-xs font-medium ${deliveryPrerequisitesReady ? 'bg-green-500/15 text-green-400' : 'bg-amber-500/15 text-amber-400'}`}>
                    {deliveryPrerequisitesReady ? 'Core resources found' : 'Setup incomplete'}
                  </span>
                )}
              </div>

              {resourcesQuery.isLoading ? (
                <p className="text-sm text-zinc-400">Discovering Meta resources...</p>
              ) : resourcesQuery.isError ? (
                <p className="text-sm text-red-400">Could not load delivery resources for this ad account.</p>
              ) : resources ? (
                <div className="grid gap-3 sm:grid-cols-3">
                  <ResourceCard
                    label="Pixels"
                    count={resources.pixels.length}
                    primary={resources.pixels[0]?.name || resources.pixels[0]?.id}
                    required
                  />
                  <ResourceCard
                    label="Pages"
                    count={resources.pages.length}
                    primary={resources.pages[0]?.name || resources.pages[0]?.id}
                    required
                  />
                  <ResourceCard
                    label="Instagram"
                    count={resources.instagram_accounts.length}
                    primary={resources.instagram_accounts[0]?.username ? `@${resources.instagram_accounts[0].username}` : resources.instagram_accounts[0]?.name || resources.instagram_accounts[0]?.id}
                  />
                </div>
              ) : null}
            </div>
          )}

          {feedback && (
            <div className={`rounded-lg border px-4 py-3 text-sm ${feedback.type === 'success' ? 'border-green-500/30 bg-green-500/10 text-green-300' : 'border-red-500/30 bg-red-500/10 text-red-300'}`}>
              {feedback.message}
            </div>
          )}

          <button
            type="button"
            className="btn-primary"
            disabled={!canPublish}
            onClick={() => selectedAccountId && publishMutation.mutate(selectedAccountId)}
          >
            {publishMutation.isPending ? 'Creating paused Meta campaign...' : 'Create paused Meta campaign'}
          </button>
        </div>
      )}

      <div className="border-t border-zinc-700 pt-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-zinc-200">Meta publications</h4>
          {publicationsQuery.isFetching && <span className="text-xs text-zinc-500">Refreshing...</span>}
        </div>
        {publicationsQuery.isError ? (
          <p className="text-sm text-red-400">Could not load Meta campaign publications.</p>
        ) : publications.length === 0 ? (
          <p className="text-sm text-zinc-500">No Meta campaign has been created for this Velnio campaign yet.</p>
        ) : (
          <div className="space-y-3">
            {publications.map((publication: MetaAdsCampaignPublication) => (
              <div key={publication.id} className="rounded-lg border border-zinc-700 bg-zinc-900/40 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-zinc-200">{publication.remote_campaign_name}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {publication.ad_account_id} · Meta ID {publication.remote_campaign_id}
                    </p>
                  </div>
                  <span className={`w-fit rounded-full px-2 py-0.5 text-xs font-medium ${publication.remote_status === 'PAUSED' ? 'bg-amber-500/15 text-amber-400' : 'bg-zinc-700 text-zinc-300'}`}>
                    {publication.remote_status}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500">
                  <span>{publication.objective}</span>
                  <span>{new Date(publication.created_at).toLocaleString()}</span>
                </div>
                <MetaDeliveryConfigEditor campaignId={campaignId} publication={publication} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ResourceCard({
  label,
  count,
  primary,
  required = false,
}: {
  label: string
  count: number
  primary?: string
  required?: boolean
}) {
  const available = count > 0
  return (
    <div className={`rounded-lg border p-3 ${available ? 'border-zinc-700 bg-zinc-800/60' : required ? 'border-amber-500/25 bg-amber-500/5' : 'border-zinc-700 bg-zinc-800/60'}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</span>
        <span className={`text-xs font-medium ${available ? 'text-green-400' : required ? 'text-amber-400' : 'text-zinc-500'}`}>
          {count}
        </span>
      </div>
      <p className="mt-2 truncate text-sm text-zinc-200">{primary || (required ? 'Required before Ad Set' : 'Optional')}</p>
    </div>
  )
}

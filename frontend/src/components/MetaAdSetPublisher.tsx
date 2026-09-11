import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { metaAdsApi, type MetaAdsCampaignPublication } from '../lib/metaAds'
import { MetaCreativePublisher } from './MetaCreativePublisher'

interface MetaAdSetPublisherProps {
  campaignId: string
  publication: MetaAdsCampaignPublication
}

export function MetaAdSetPublisher({ campaignId, publication }: MetaAdSetPublisherProps) {
  const queryClient = useQueryClient()
  const [dailyBudget, setDailyBudget] = useState('')
  const [targetCountry, setTargetCountry] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)

  const configured = Boolean(
    publication.pixel_id && publication.page_id && publication.delivery_configured_at,
  )

  const accountsQuery = useQuery({
    queryKey: ['meta-ads-accounts'],
    queryFn: metaAdsApi.adAccounts,
    enabled: configured,
  })

  const adSetQuery = useQuery({
    queryKey: ['meta-ads-ad-set', campaignId, publication.id],
    queryFn: () => metaAdsApi.getAdSet(campaignId, publication.id),
  })

  const publishMutation = useMutation({
    mutationFn: (input: { daily_budget_minor: number; target_country?: string | null }) =>
      metaAdsApi.publishAdSetPaused(campaignId, publication.id, input),
    onMutate: () => setFeedback(null),
    onSuccess: (adSet) => {
      queryClient.setQueryData(['meta-ads-ad-set', campaignId, publication.id], adSet)
      setFeedback(
        adSet.reused
          ? 'Existing PAUSED Meta Ad Set reconciled. No duplicate was created.'
          : 'Meta Ad Set created in PAUSED state. Budget is configured, but delivery has not started.',
      )
    },
  })

  const account = (accountsQuery.data || []).find((item) => item.id === publication.ad_account_id)
  const parsedBudget = Number(dailyBudget)
  const validBudget = /^\d+$/.test(dailyBudget) && Number.isSafeInteger(parsedBudget) && parsedBudget > 0
  const validCountry = targetCountry === '' || /^[A-Za-z]{2}$/.test(targetCountry)
  const canPublish = Boolean(
    configured &&
      publication.remote_status === 'PAUSED' &&
      !adSetQuery.data &&
      validBudget &&
      validCountry &&
      !publishMutation.isPending,
  )

  return (
    <div className="mt-4 border-t border-zinc-700 pt-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-zinc-300">Ad Set</span>
            {adSetQuery.data ? (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-400">
                {adSetQuery.data.remote_status}
              </span>
            ) : (
              <span className="rounded-full bg-zinc-700 px-2 py-0.5 text-[11px] font-medium text-zinc-400">
                Not created
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            L2 delivery container. Velnio only creates it as PAUSED in this phase.
          </p>
        </div>
        {account?.currency && (
          <span className="rounded-full bg-zinc-700 px-2 py-1 text-xs font-medium text-zinc-300">
            Account currency: {account.currency}
          </span>
        )}
      </div>

      {adSetQuery.isLoading ? (
        <p className="mt-3 text-sm text-zinc-400">Checking Meta Ad Set...</p>
      ) : adSetQuery.isError ? (
        <p className="mt-3 text-sm text-red-400">Could not load the Meta Ad Set state.</p>
      ) : adSetQuery.data ? (
        <div className="mt-3 space-y-4">
          <div className="grid gap-2 rounded-lg border border-zinc-700 bg-zinc-950/30 p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <Detail label="Budget" value={`${adSetQuery.data.daily_budget_minor} ${adSetQuery.data.currency} minor units`} />
            <Detail label="Country" value={adSetQuery.data.target_country} />
            <Detail label="Optimization" value={adSetQuery.data.optimization_goal} />
            <Detail label="Meta ID" value={adSetQuery.data.remote_ad_set_id} />
          </div>
          <MetaCreativePublisher
            campaignId={campaignId}
            publication={publication}
            adSet={adSetQuery.data}
          />
        </div>
      ) : !configured ? (
        <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-950/30 px-3 py-2 text-sm text-zinc-400">
          Configure a Pixel and Facebook Page before creating the Ad Set.
        </div>
      ) : (
        <div className="mt-4 space-y-4 rounded-lg border border-zinc-700 bg-zinc-950/30 p-4">
          <div className="rounded-lg border border-amber-500/25 bg-amber-500/5 px-3 py-2 text-sm text-amber-200">
            This action configures a budget but creates the Ad Set as PAUSED. It does not create a creative or ad and cannot start delivery.
          </div>

          {publication.remote_status !== 'PAUSED' && (
            <div className="rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              Ad Set creation is locked because the parent Meta Campaign is not PAUSED.
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor={`meta-budget-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
                Daily budget in Meta minor units <span className="text-red-400">*</span>
              </label>
              <input
                id={`meta-budget-${publication.id}`}
                type="text"
                inputMode="numeric"
                className="input"
                value={dailyBudget}
                placeholder="2500"
                onChange={(event) => setDailyBudget(event.target.value.trim())}
                disabled={publishMutation.isPending || publication.remote_status !== 'PAUSED'}
              />
              <p className="mt-1 text-xs text-zinc-500">
                Enter the exact positive integer sent to Meta. It is interpreted in the ad account currency{account?.currency ? ` (${account.currency})` : ''}.
              </p>
            </div>

            <div>
              <label htmlFor={`meta-country-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
                Target country <span className="font-normal text-zinc-500">(optional override)</span>
              </label>
              <input
                id={`meta-country-${publication.id}`}
                type="text"
                maxLength={2}
                className="input uppercase"
                value={targetCountry}
                placeholder="Campaign country"
                onChange={(event) => setTargetCountry(event.target.value)}
                disabled={publishMutation.isPending || publication.remote_status !== 'PAUSED'}
              />
              <p className="mt-1 text-xs text-zinc-500">Leave blank to use this Velnio campaign's target country.</p>
            </div>
          </div>

          {!validCountry && <p className="text-sm text-red-400">Target country must be a two-letter ISO code.</p>}
          {dailyBudget !== '' && !validBudget && (
            <p className="text-sm text-red-400">Daily budget must be a positive whole number within JavaScript safe integer range.</p>
          )}
          {accountsQuery.isError && (
            <p className="text-sm text-red-400">Could not verify the Meta ad account currency.</p>
          )}
          {publishMutation.isError && (
            <div className="rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {(publishMutation.error as Error)?.message || 'Could not create the PAUSED Meta Ad Set.'}
            </div>
          )}
          {feedback && (
            <div className="rounded-lg border border-green-500/25 bg-green-500/10 px-3 py-2 text-sm text-green-300">
              {feedback}
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="button"
              className="btn-primary text-sm"
              disabled={!canPublish}
              onClick={() => publishMutation.mutate({
                daily_budget_minor: parsedBudget,
                target_country: targetCountry ? targetCountry.toUpperCase() : null,
              })}
            >
              {publishMutation.isPending ? 'Creating PAUSED Ad Set...' : 'Create PAUSED Ad Set'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <span className="block text-[11px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className="block truncate text-xs text-zinc-200" title={value}>{value}</span>
    </div>
  )
}

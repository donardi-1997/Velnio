import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { metaAdsApi, type MetaAdPublication } from '../lib/metaAds'


interface MetaLaunchReadinessProps {
  campaignId: string
  publicationId: string
  ad: MetaAdPublication
}

export function MetaLaunchReadiness({ campaignId, publicationId, ad }: MetaLaunchReadinessProps) {
  const queryClient = useQueryClient()
  const [spendAcknowledged, setSpendAcknowledged] = useState(false)

  const readinessQuery = useQuery({
    queryKey: ['meta-ads-launch-readiness', campaignId, publicationId, ad.id],
    queryFn: () => metaAdsApi.launchReadiness(campaignId, publicationId, ad.id),
    enabled: false,
  })

  const intentMutation = useMutation({
    mutationFn: () => metaAdsApi.createLaunchIntent(campaignId, publicationId, ad.id),
    onMutate: () => setSpendAcknowledged(false),
  })

  const readiness = readinessQuery.data
  const intent = intentMutation.data

  const confirmationMutation = useMutation({
    mutationFn: async () => {
      if (!intent || !readiness) {
        throw new Error('Prepare a fresh launch intent before activation.')
      }
      return metaAdsApi.confirmLaunch(
        campaignId,
        publicationId,
        ad.id,
        intent,
        readiness.launch_plan.daily_budget_minor,
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-ads-ads', campaignId, publicationId] })
      queryClient.invalidateQueries({ queryKey: ['meta-ads-ad-remote-state', campaignId, publicationId, ad.id] })
      setSpendAcknowledged(false)
    },
  })

  const confirmation = confirmationMutation.data
  const failedChecks = readiness?.checks.filter((check) => check.status === 'FAIL') || []
  const intentExpired = intent ? Date.now() >= new Date(intent.expires_at).getTime() : false

  const refreshReadiness = () => {
    intentMutation.reset()
    confirmationMutation.reset()
    setSpendAcknowledged(false)
    void readinessQuery.refetch()
  }

  return (
    <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950/40 p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium text-zinc-200">Launch readiness</p>
          <p className="mt-1 text-[11px] text-zinc-500">
            Read-only preflight. It verifies current Shopify, Meta, delivery, budget and hierarchy state without activating anything.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary shrink-0 text-xs"
          onClick={refreshReadiness}
          disabled={readinessQuery.isFetching || intentMutation.isPending || confirmationMutation.isPending}
        >
          {readinessQuery.isFetching
            ? 'Checking readiness...'
            : readiness
              ? 'Refresh readiness'
              : 'Check launch readiness'}
        </button>
      </div>

      {readinessQuery.isError && (
        <div className="mt-3 rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-xs text-red-300">
          {(readinessQuery.error as Error)?.message || 'Could not evaluate launch readiness.'}
        </div>
      )}

      {readiness && (
        <div className="mt-3 space-y-3">
          <div
            className={
              readiness.ready
                ? 'rounded-lg border border-green-500/25 bg-green-500/10 px-3 py-2 text-xs text-green-300'
                : 'rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-xs text-red-300'
            }
          >
            {readiness.ready
              ? 'All launch checks pass. No status was changed; explicit confirmation is still required.'
              : `${failedChecks.length} launch check${failedChecks.length === 1 ? '' : 's'} failed. Nothing was activated.`}
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <PlanValue
              label="Daily budget"
              value={`${readiness.launch_plan.daily_budget_minor} ${readiness.launch_plan.currency} minor units`}
            />
            <PlanValue label="Country" value={readiness.launch_plan.target_country} />
            <PlanValue label="Meta Ad" value={readiness.launch_plan.remote_ad_id} />
            <PlanValue label="Meta Creative" value={readiness.launch_plan.remote_creative_id} />
          </div>

          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
            <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-400">Potential launch plan</p>
            <div className="mt-2 grid gap-2 sm:grid-cols-3">
              {(['campaign', 'ad_set', 'ad'] as const).map((resource) => (
                <div key={resource} className="rounded-md bg-zinc-950/60 px-3 py-2 text-xs">
                  <span className="block text-zinc-500">{resource === 'ad_set' ? 'Ad Set' : resource === 'campaign' ? 'Campaign' : 'Ad'}</span>
                  <span className="mt-1 block text-zinc-200">
                    {readiness.launch_plan.current_configured_statuses[resource] || 'unknown'} → {readiness.launch_plan.proposed_statuses[resource]}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-2 truncate text-[11px] text-zinc-500" title={readiness.launch_plan.destination_url}>
              Destination: {readiness.launch_plan.destination_url}
            </p>
            <p className="mt-1 text-[11px] text-zinc-500">
              Preflight fingerprint: {readiness.readiness_fingerprint.slice(0, 16)}…
            </p>
            <p className="mt-1 text-[11px] text-zinc-500">
              Side effects performed by this check: {readiness.side_effects_performed ? 'yes' : 'no'}
            </p>
          </div>

          {readiness.ready && (
            <div className="rounded-lg border border-amber-500/25 bg-amber-500/5 p-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs font-medium text-amber-200">Secure launch intent</p>
                  <p className="mt-1 text-[11px] text-amber-100/70">
                    Creates a short-lived, one-time confirmation token bound to this exact preflight. Preparing the intent does not activate Meta resources.
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-secondary shrink-0 text-xs"
                  disabled={intentMutation.isPending || readinessQuery.isFetching || confirmationMutation.isPending || Boolean(confirmation)}
                  onClick={() => {
                    confirmationMutation.reset()
                    intentMutation.mutate()
                  }}
                >
                  {intentMutation.isPending
                    ? 'Preparing intent...'
                    : confirmation
                      ? 'Campaign activated'
                      : intent
                        ? 'Replace launch intent'
                        : 'Prepare secure launch intent'}
                </button>
              </div>

              {intentMutation.isError && (
                <div className="mt-3 rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                  {(intentMutation.error as Error)?.message || 'Could not prepare the launch intent.'}
                </div>
              )}

              {intent && !confirmation && (
                <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-xs">
                  <div className="flex flex-wrap items-center gap-2 text-zinc-300">
                    <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
                      {intent.status}
                    </span>
                    <span>Intent {intent.id.slice(0, 8)}</span>
                  </div>
                  <p className="mt-2 text-zinc-500">Expires: {new Date(intent.expires_at).toLocaleString()}</p>
                  <p className="mt-1 text-zinc-500">Bound fingerprint: {intent.readiness_fingerprint.slice(0, 16)}…</p>

                  <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-red-200">
                    <p className="font-semibold">Activation can start real advertising spend.</p>
                    <p className="mt-1 text-[11px] text-red-200/80">
                      Velnio will attempt Ad → Ad Set → Campaign activation. The Campaign is activated last. Daily budget: {readiness.launch_plan.daily_budget_minor} {readiness.launch_plan.currency} minor units.
                    </p>
                    <label className="mt-3 flex cursor-pointer items-start gap-2 text-[11px]">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={spendAcknowledged}
                        onChange={(event) => setSpendAcknowledged(event.target.checked)}
                        disabled={confirmationMutation.isPending || intentExpired}
                      />
                      <span>
                        I understand that activating this Meta Campaign can start spend using the budget shown above.
                      </span>
                    </label>

                    {intentExpired && (
                      <p className="mt-2 text-[11px] font-medium">This launch intent has expired. Prepare a new intent.</p>
                    )}

                    <div className="mt-3 flex justify-end">
                      <button
                        type="button"
                        className="inline-flex items-center justify-center rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={!spendAcknowledged || intentExpired || confirmationMutation.isPending}
                        onClick={() => confirmationMutation.mutate()}
                      >
                        {confirmationMutation.isPending ? 'Activating Meta hierarchy...' : 'Activate Meta campaign'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {confirmationMutation.isError && (
                <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
                  <p className="font-medium">Launch did not complete successfully.</p>
                  <p className="mt-1">
                    {(confirmationMutation.error as Error)?.message || 'Could not confirm the Meta Ads launch.'}
                  </p>
                  <p className="mt-1 text-[11px] text-red-200/80">
                    If the message says the state is uncertain, verify the Campaign, Ad Set and Ad directly in Meta Ads Manager before taking another action.
                  </p>
                </div>
              )}

              {confirmation && (
                <div className="mt-3 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-3 text-xs text-green-200">
                  <p className="font-semibold">Meta Campaign activated.</p>
                  <p className="mt-1 text-[11px] text-green-200/80">
                    Campaign, Ad Set and Ad were confirmed ACTIVE. Daily budget: {confirmation.daily_budget_minor} {confirmation.currency} minor units. Activated {new Date(confirmation.activated_at).toLocaleString()}.
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="space-y-1.5">
            {readiness.checks.map((check) => (
              <div
                key={check.key}
                className="flex items-start gap-2 rounded-md border border-zinc-800 bg-zinc-950/30 px-3 py-2 text-xs"
              >
                <span
                  className={
                    check.status === 'PASS'
                      ? 'mt-0.5 rounded-full bg-green-500/15 px-2 py-0.5 text-[10px] font-medium text-green-300'
                      : 'mt-0.5 rounded-full bg-red-500/15 px-2 py-0.5 text-[10px] font-medium text-red-300'
                  }
                >
                  {check.status}
                </span>
                <div className="min-w-0">
                  <p className="font-medium text-zinc-300">{check.key.replace(/_/g, ' ')}</p>
                  <p className="mt-0.5 text-zinc-500">{check.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PlanValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-zinc-800 bg-zinc-950/30 px-3 py-2">
      <span className="block text-[10px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className="mt-1 block truncate text-xs text-zinc-200" title={value}>{value}</span>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'

import { metaAdsApi, type MetaAdPublication } from '../lib/metaAds'


interface MetaLaunchReadinessProps {
  campaignId: string
  publicationId: string
  ad: MetaAdPublication
}

export function MetaLaunchReadiness({ campaignId, publicationId, ad }: MetaLaunchReadinessProps) {
  const readinessQuery = useQuery({
    queryKey: ['meta-ads-launch-readiness', campaignId, publicationId, ad.id],
    queryFn: () => metaAdsApi.launchReadiness(campaignId, publicationId, ad.id),
    enabled: false,
  })

  const readiness = readinessQuery.data
  const failedChecks = readiness?.checks.filter((check) => check.status === 'FAIL') || []

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
          onClick={() => readinessQuery.refetch()}
          disabled={readinessQuery.isFetching}
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
              ? 'All launch checks pass. No status was changed; an explicit launch workflow is still required.'
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
              Side effects performed by this check: {readiness.side_effects_performed ? 'yes' : 'no'}
            </p>
          </div>

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
                  <p className="font-medium text-zinc-300">{check.key.replaceAll('_', ' ')}</p>
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

import { useQuery } from '@tanstack/react-query'

import { metaAdsApi, type MetaAdPublication } from '../lib/metaAds'


interface MetaAdLiveStateProps {
  campaignId: string
  publicationId: string
  ad: MetaAdPublication
}

export function MetaAdLiveState({ campaignId, publicationId, ad }: MetaAdLiveStateProps) {
  const stateQuery = useQuery({
    queryKey: ['meta-ads-ad-remote-state', campaignId, publicationId, ad.id],
    queryFn: () => metaAdsApi.adRemoteState(campaignId, publicationId, ad.id),
    staleTime: 15_000,
  })

  if (stateQuery.isLoading) {
    return <p className="mt-2 text-[11px] text-zinc-500">Verifying live state with Meta...</p>
  }

  if (stateQuery.isError || !stateQuery.data) {
    return (
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
        <span className="text-red-400">Live Meta state unavailable.</span>
        <span className="text-zinc-500">Local snapshot: {ad.remote_status}</span>
        <button
          type="button"
          className="text-zinc-300 underline decoration-zinc-600 underline-offset-2 hover:text-white"
          onClick={() => stateQuery.refetch()}
          disabled={stateQuery.isFetching}
        >
          {stateQuery.isFetching ? 'Checking...' : 'Retry'}
        </button>
      </div>
    )
  }

  const state = stateQuery.data
  const configuredSafe = state.configured_status === 'PAUSED'

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
      <span className="text-zinc-500">Live Meta:</span>
      <span
        className={
          configuredSafe
            ? 'rounded-full bg-amber-500/15 px-2 py-0.5 font-medium text-amber-300'
            : 'rounded-full bg-red-500/15 px-2 py-0.5 font-medium text-red-300'
        }
      >
        Configured {state.configured_status}
      </span>
      <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-zinc-300">
        Effective {state.effective_status || 'unknown'}
      </span>
      <button
        type="button"
        className="text-zinc-400 underline decoration-zinc-700 underline-offset-2 hover:text-zinc-200"
        onClick={() => stateQuery.refetch()}
        disabled={stateQuery.isFetching}
      >
        {stateQuery.isFetching ? 'Refreshing...' : 'Refresh'}
      </button>
    </div>
  )
}

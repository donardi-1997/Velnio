import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  metaAdsApi,
  type MetaAdsCampaignPublication,
} from '../lib/metaAds'

interface MetaDeliveryConfigEditorProps {
  campaignId: string
  publication: MetaAdsCampaignPublication
}

export function MetaDeliveryConfigEditor({ campaignId, publication }: MetaDeliveryConfigEditorProps) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [pixelId, setPixelId] = useState(publication.pixel_id || '')
  const [pageId, setPageId] = useState(publication.page_id || '')
  const [instagramAccountId, setInstagramAccountId] = useState(publication.instagram_account_id || '')
  const [feedback, setFeedback] = useState<string | null>(null)

  useEffect(() => {
    setPixelId(publication.pixel_id || '')
    setPageId(publication.page_id || '')
    setInstagramAccountId(publication.instagram_account_id || '')
  }, [publication.pixel_id, publication.page_id, publication.instagram_account_id])

  const resourcesQuery = useQuery({
    queryKey: ['meta-ads-delivery-resources', publication.ad_account_id],
    queryFn: () => metaAdsApi.deliveryResources(publication.ad_account_id),
    enabled: open,
  })

  const saveMutation = useMutation({
    mutationFn: () => metaAdsApi.configureDelivery(campaignId, publication.id, {
      pixel_id: pixelId,
      page_id: pageId,
      instagram_account_id: instagramAccountId || null,
    }),
    onMutate: () => setFeedback(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-ads-publications', campaignId] })
      setFeedback('Delivery configuration saved and revalidated against this Meta ad account.')
    },
  })

  const configured = Boolean(publication.pixel_id && publication.page_id && publication.delivery_configured_at)
  const canSave = Boolean(
    publication.remote_status === 'PAUSED' &&
      pixelId &&
      pageId &&
      !saveMutation.isPending,
  )

  return (
    <div className="mt-4 border-t border-zinc-700 pt-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-zinc-300">Delivery configuration</span>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${configured ? 'bg-green-500/15 text-green-400' : 'bg-zinc-700 text-zinc-400'}`}>
              {configured ? 'Configured' : 'Not configured'}
            </span>
          </div>
          {configured && (
            <p className="mt-1 text-xs text-zinc-500">
              Pixel {publication.pixel_id} · Page {publication.page_id}
              {publication.instagram_account_id ? ` · Instagram ${publication.instagram_account_id}` : ''}
            </p>
          )}
        </div>
        <button
          type="button"
          className="btn-secondary text-xs"
          onClick={() => {
            setOpen((value) => !value)
            setFeedback(null)
          }}
        >
          {open ? 'Close configuration' : configured ? 'Edit delivery' : 'Configure delivery'}
        </button>
      </div>

      {open && (
        <div className="mt-4 space-y-4 rounded-lg border border-zinc-700 bg-zinc-950/30 p-4">
          {publication.remote_status !== 'PAUSED' && (
            <div className="rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              Delivery configuration is locked because this Meta campaign is not PAUSED.
            </div>
          )}

          {resourcesQuery.isLoading ? (
            <p className="text-sm text-zinc-400">Loading resources from this Meta ad account...</p>
          ) : resourcesQuery.isError ? (
            <p className="text-sm text-red-400">Could not load Meta delivery resources. The connection or account access may have changed.</p>
          ) : resourcesQuery.data ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label htmlFor={`pixel-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
                    Pixel <span className="text-red-400">*</span>
                  </label>
                  <select
                    id={`pixel-${publication.id}`}
                    className="input"
                    value={pixelId}
                    onChange={(event) => setPixelId(event.target.value)}
                    disabled={saveMutation.isPending || publication.remote_status !== 'PAUSED'}
                  >
                    <option value="">Select a Pixel</option>
                    {resourcesQuery.data.pixels.map((pixel) => (
                      <option key={pixel.id} value={pixel.id}>
                        {pixel.name || 'Unnamed Pixel'} ({pixel.id})
                      </option>
                    ))}
                  </select>
                  {resourcesQuery.data.pixels.length === 0 && (
                    <p className="mt-1 text-xs text-amber-400">No Pixel is available for this ad account.</p>
                  )}
                </div>

                <div>
                  <label htmlFor={`page-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
                    Facebook Page <span className="text-red-400">*</span>
                  </label>
                  <select
                    id={`page-${publication.id}`}
                    className="input"
                    value={pageId}
                    onChange={(event) => setPageId(event.target.value)}
                    disabled={saveMutation.isPending || publication.remote_status !== 'PAUSED'}
                  >
                    <option value="">Select a Page</option>
                    {resourcesQuery.data.pages.map((page) => (
                      <option key={page.id} value={page.id}>
                        {page.name || 'Unnamed Page'} ({page.id})
                      </option>
                    ))}
                  </select>
                  {resourcesQuery.data.pages.length === 0 && (
                    <p className="mt-1 text-xs text-amber-400">No promotable Page is available for this ad account.</p>
                  )}
                </div>

                <div className="md:col-span-2">
                  <label htmlFor={`instagram-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
                    Instagram account <span className="font-normal text-zinc-500">(optional)</span>
                  </label>
                  <select
                    id={`instagram-${publication.id}`}
                    className="input"
                    value={instagramAccountId}
                    onChange={(event) => setInstagramAccountId(event.target.value)}
                    disabled={saveMutation.isPending || publication.remote_status !== 'PAUSED'}
                  >
                    <option value="">No Instagram account</option>
                    {resourcesQuery.data.instagram_accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.username ? `@${account.username}` : account.name || 'Unnamed Instagram account'} ({account.id})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <p className="text-xs text-zinc-500">
                Saving re-checks every selected ID against the current Meta account before persisting it. This still does not create an Ad Set or spend budget.
              </p>

              {saveMutation.isError && (
                <div className="rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                  {(saveMutation.error as Error)?.message || 'Could not save delivery configuration.'}
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
                  disabled={!canSave}
                  onClick={() => saveMutation.mutate()}
                >
                  {saveMutation.isPending ? 'Validating and saving...' : 'Save delivery configuration'}
                </button>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  )
}

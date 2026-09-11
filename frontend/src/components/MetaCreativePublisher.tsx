import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api'
import {
  metaAdsApi,
  type MetaAdSetPublication,
  type MetaAdsCampaignPublication,
  type MetaCallToAction,
} from '../lib/metaAds'
import type { Campaign, CampaignImage } from '../types'


type CreativeCampaign = Campaign & {
  images?: CampaignImage[]
  external_page_url?: string | null
}

interface MetaCreativePublisherProps {
  campaignId: string
  publication: MetaAdsCampaignPublication
  adSet: MetaAdSetPublication
}

export function MetaCreativePublisher({ campaignId, publication, adSet }: MetaCreativePublisherProps) {
  const queryClient = useQueryClient()
  const [selectedImageId, setSelectedImageId] = useState('')
  const [primaryText, setPrimaryText] = useState('')
  const [headline, setHeadline] = useState('')
  const [callToAction, setCallToAction] = useState<MetaCallToAction>('SHOP_NOW')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [adFeedback, setAdFeedback] = useState<string | null>(null)

  const campaignQuery = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: async () => (await api.campaigns.get(campaignId)) as CreativeCampaign,
  })

  const creativesQuery = useQuery({
    queryKey: ['meta-ads-creatives', campaignId, publication.id],
    queryFn: () => metaAdsApi.creatives(campaignId, publication.id),
  })

  const adsQuery = useQuery({
    queryKey: ['meta-ads-ads', campaignId, publication.id],
    queryFn: () => metaAdsApi.ads(campaignId, publication.id),
  })

  const publishMutation = useMutation({
    mutationFn: () =>
      metaAdsApi.publishCreative(campaignId, publication.id, {
        product_image_id: selectedImageId,
        primary_text: primaryText.trim(),
        headline: headline.trim() || null,
        call_to_action: callToAction,
      }),
    onMutate: () => setFeedback(null),
    onSuccess: (creative) => {
      queryClient.invalidateQueries({ queryKey: ['meta-ads-creatives', campaignId, publication.id] })
      setFeedback(
        creative.reused
          ? 'Existing standalone Meta Creative reconciled. No duplicate was created.'
          : 'Standalone Meta Creative created. No Meta Ad was created or activated.',
      )
    },
  })

  const publishAdMutation = useMutation({
    mutationFn: (creativePublicationId: string) =>
      metaAdsApi.publishAdPaused(campaignId, publication.id, creativePublicationId),
    onMutate: () => setAdFeedback(null),
    onSuccess: (ad) => {
      queryClient.invalidateQueries({ queryKey: ['meta-ads-ads', campaignId, publication.id] })
      setAdFeedback(
        ad.reused
          ? 'Existing PAUSED Meta Ad reconciled. No duplicate was created.'
          : 'Meta Ad created in PAUSED state. Delivery is still disabled.',
      )
    },
  })

  const selectedImages = useMemo(
    () => (campaignQuery.data?.images || []).filter((image) => image.selected),
    [campaignQuery.data?.images],
  )
  const selectedImage = selectedImages.find((image) => image.id === selectedImageId)
  const campaignPublished = campaignQuery.data?.status === 'PUBLISHED'
  const parentsPaused = publication.remote_status === 'PAUSED' && adSet.remote_status === 'PAUSED'
  const validText = primaryText.trim().length > 0 && primaryText.length <= 5000
  const validHeadline = headline.length <= 255
  const canPublish = Boolean(
    campaignPublished &&
      parentsPaused &&
      selectedImageId &&
      validText &&
      validHeadline &&
      !publishMutation.isPending,
  )

  return (
    <div className="mt-4 border-t border-zinc-700 pt-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-zinc-300">Ad Creative</span>
            <span className="rounded-full bg-indigo-500/15 px-2 py-0.5 text-[11px] font-medium text-indigo-300">
              Standalone
            </span>
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            Creates the reusable Meta creative object first, then lets you attach it to a separate PAUSED Ad.
          </p>
        </div>
        <span className="rounded-full bg-zinc-700 px-2 py-1 text-xs font-medium text-zinc-300">
          {creativesQuery.data?.length || 0} creative{creativesQuery.data?.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="mt-3 rounded-lg border border-amber-500/25 bg-amber-500/5 px-3 py-2 text-sm text-amber-200">
        Creative creation does not create an Ad. When you explicitly create an Ad below, Velnio creates it as PAUSED only; this screen has no activation action.
      </div>

      {!parentsPaused && (
        <div className="mt-3 rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          Creative and Ad creation are locked because the Meta Campaign or Ad Set is not PAUSED.
        </div>
      )}

      {campaignQuery.isLoading ? (
        <p className="mt-3 text-sm text-zinc-400">Checking Shopify destination and selected assets...</p>
      ) : campaignQuery.isError ? (
        <p className="mt-3 text-sm text-red-400">Could not load campaign assets.</p>
      ) : !campaignPublished ? (
        <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-950/30 px-3 py-2 text-sm text-zinc-400">
          Publish the campaign to Shopify before creating a Meta Creative. Velnio uses the persisted Shopify landing URL as the destination.
        </div>
      ) : selectedImages.length === 0 ? (
        <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-950/30 px-3 py-2 text-sm text-zinc-400">
          Select at least one campaign asset in the Assets tab before creating a Meta Creative.
        </div>
      ) : (
        <div className="mt-4 space-y-4 rounded-lg border border-zinc-700 bg-zinc-950/30 p-4">
          <div>
            <label htmlFor={`meta-creative-image-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
              Selected campaign asset <span className="text-red-400">*</span>
            </label>
            <select
              id={`meta-creative-image-${publication.id}`}
              className="input"
              value={selectedImageId}
              onChange={(event) => setSelectedImageId(event.target.value)}
              disabled={!parentsPaused || publishMutation.isPending}
            >
              <option value="">Choose a selected asset</option>
              {selectedImages.map((image) => (
                <option key={image.id} value={image.id}>
                  {image.purpose || 'Campaign image'} · {image.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </div>

          {selectedImage && (
            <div className="flex items-center gap-3 rounded-lg border border-zinc-700 bg-zinc-900/60 p-3">
              <img
                src={selectedImage.image_url}
                alt="Selected Meta creative asset"
                className="h-20 w-20 rounded-lg object-cover"
              />
              <div className="min-w-0 text-xs">
                <p className="font-medium text-zinc-200">{selectedImage.purpose || 'Campaign image'}</p>
                <p className="mt-1 truncate text-zinc-500" title={selectedImage.image_url}>{selectedImage.image_url}</p>
                <p className="mt-1 text-zinc-500">This exact persisted image URL is sent to Meta.</p>
              </div>
            </div>
          )}

          <div>
            <label htmlFor={`meta-creative-text-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
              Primary text <span className="text-red-400">*</span>
            </label>
            <textarea
              id={`meta-creative-text-${publication.id}`}
              className="input min-h-28 resize-y"
              maxLength={5000}
              value={primaryText}
              onChange={(event) => setPrimaryText(event.target.value)}
              disabled={!parentsPaused || publishMutation.isPending}
              placeholder="Write the exact ad copy that Meta should store in this Creative."
            />
            <p className="mt-1 text-right text-xs text-zinc-500">{primaryText.length}/5000</p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor={`meta-creative-headline-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
                Headline <span className="font-normal text-zinc-500">(optional)</span>
              </label>
              <input
                id={`meta-creative-headline-${publication.id}`}
                type="text"
                className="input"
                maxLength={255}
                value={headline}
                onChange={(event) => setHeadline(event.target.value)}
                disabled={!parentsPaused || publishMutation.isPending}
                placeholder="Offer headline"
              />
            </div>

            <div>
              <label htmlFor={`meta-creative-cta-${publication.id}`} className="mb-1 block text-xs font-medium text-zinc-300">
                Call to action
              </label>
              <select
                id={`meta-creative-cta-${publication.id}`}
                className="input"
                value={callToAction}
                onChange={(event) => setCallToAction(event.target.value as MetaCallToAction)}
                disabled={!parentsPaused || publishMutation.isPending}
              >
                <option value="SHOP_NOW">Shop now</option>
                <option value="LEARN_MORE">Learn more</option>
                <option value="GET_OFFER">Get offer</option>
              </select>
            </div>
          </div>

          {publishMutation.isError && (
            <div className="rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {(publishMutation.error as Error)?.message || 'Could not create the standalone Meta Creative.'}
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
              onClick={() => publishMutation.mutate()}
            >
              {publishMutation.isPending ? 'Creating standalone Creative...' : 'Create standalone Creative'}
            </button>
          </div>
        </div>
      )}

      {adsQuery.isError && (
        <p className="mt-3 text-sm text-red-400">Could not load existing Meta Ads.</p>
      )}
      {adFeedback && (
        <div className="mt-3 rounded-lg border border-green-500/25 bg-green-500/10 px-3 py-2 text-sm text-green-300">
          {adFeedback}
        </div>
      )}

      {creativesQuery.isError ? (
        <p className="mt-3 text-sm text-red-400">Could not load existing Meta Creatives.</p>
      ) : (creativesQuery.data || []).length > 0 ? (
        <div className="mt-4 space-y-3">
          {(creativesQuery.data || []).map((creative) => {
            const existingAd = (adsQuery.data || []).find(
              (ad) => ad.creative_publication_id === creative.id,
            )
            const isCreatingThisAd = publishAdMutation.isPending && publishAdMutation.variables === creative.id
            const thisAdFailed = publishAdMutation.isError && publishAdMutation.variables === creative.id

            return (
              <div key={creative.id} className="rounded-lg border border-zinc-700 bg-zinc-950/30 p-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <img src={creative.image_url} alt="Meta creative" className="h-14 w-14 rounded-md object-cover" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-zinc-200">{creative.headline || creative.primary_text}</p>
                    <p className="mt-1 truncate text-[11px] text-zinc-500">Meta Creative ID {creative.remote_creative_id}</p>
                    <p className="mt-1 truncate text-[11px] text-zinc-500" title={creative.destination_url}>{creative.destination_url}</p>
                  </div>
                  <span className="w-fit rounded-full bg-indigo-500/15 px-2 py-0.5 text-[11px] font-medium text-indigo-300">
                    {creative.call_to_action}
                  </span>
                </div>

                <div className="mt-3 border-t border-zinc-800 pt-3">
                  {existingAd ? (
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-zinc-300">Meta Ad</span>
                          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-300">
                            {existingAd.remote_status}
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-zinc-500">Meta Ad ID {existingAd.remote_ad_id}</p>
                      </div>
                      <span className="text-xs text-zinc-500">No activation control in Velnio</span>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-xs font-medium text-zinc-300">Attach this Creative to a Meta Ad</p>
                        <p className="mt-1 text-[11px] text-zinc-500">
                          Velnio will revalidate the remote Campaign and Ad Set, then create the Ad as PAUSED.
                        </p>
                      </div>
                      <button
                        type="button"
                        className="btn-primary shrink-0 text-sm"
                        disabled={!parentsPaused || adsQuery.isLoading || publishAdMutation.isPending}
                        onClick={() => publishAdMutation.mutate(creative.id)}
                      >
                        {isCreatingThisAd ? 'Creating PAUSED Ad...' : 'Create PAUSED Ad'}
                      </button>
                    </div>
                  )}

                  {thisAdFailed && (
                    <div className="mt-3 rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                      {(publishAdMutation.error as Error)?.message || 'Could not create the PAUSED Meta Ad.'}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}

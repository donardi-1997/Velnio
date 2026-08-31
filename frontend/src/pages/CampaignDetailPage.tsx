import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Campaign, Offer, SellingAngle, CampaignImage, GoogleDriveFile } from '../types'
import { CampaignPerformanceTab } from './CampaignPerformanceTab'
import { CampaignExperimentsTab } from './CampaignExperimentsTab'
import { GoogleDriveBrowser } from '../components/GoogleDriveBrowser'

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-500/20 text-gray-400',
  ANALYZING: 'bg-blue-500/20 text-blue-400',
  ANGLE_READY: 'bg-purple-500/20 text-purple-400',
  OFFER_READY: 'bg-indigo-500/20 text-indigo-400',
  LANDING_READY: 'bg-teal-500/20 text-teal-400',
  PUBLISHED: 'bg-green-500/20 text-green-400',
  FAILED: 'bg-red-500/20 text-red-400',
}

const offerTypeLabels: Record<string, string> = {
  STANDARD: 'Standard',
  DISCOUNT: 'Discount',
  BUNDLE: 'Bundle',
  BOGO: 'Buy One Get One',
  FREE_SHIPPING: 'Free Shipping',
  COD: 'Cash on Delivery',
  CUSTOM: 'Custom',
}

type Tab = 'details' | 'angles' | 'offer' | 'visual-direction' | 'assets' | 'landing' | 'publish-readiness' | 'publish' | 'performance' | 'experiments'

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('details')
  const [editingOffer, setEditingOffer] = useState(false)
  const [offerForm, setOfferForm] = useState<Partial<Offer>>({})
  const [vdForm, setVdForm] = useState<any>({})
  const [showDriveBrowser, setShowDriveBrowser] = useState(false)

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => api.campaigns.get(id!),
  })

  const { data: angles = [] } = useQuery({
    queryKey: ['campaign-angles', id],
    queryFn: () => api.campaigns.angles.list(id!),
    enabled: activeTab === 'angles',
  })

  const { data: offer } = useQuery({
    queryKey: ['campaign-offer', id],
    queryFn: () => api.campaigns.offer.get(id!),
    enabled: activeTab === 'offer',
  })

  const { data: landing } = useQuery({
    queryKey: ['campaign-landing', id],
    queryFn: () => api.campaigns.landing.get(id!),
    enabled: activeTab === 'landing',
  })

  const { data: visualDirection } = useQuery({
    queryKey: ['campaign-vd', id],
    queryFn: () => api.campaigns.getVisualDirection(id!),
    enabled: activeTab === 'visual-direction',
  })

  const { data: publishReadiness } = useQuery({
    queryKey: ['campaign-readiness', id],
    queryFn: () => api.campaigns.getPublishReadiness(id!),
    enabled: activeTab === 'publish-readiness',
  })

  const { data: assets = [] } = useQuery({
    queryKey: ['campaign-assets', id],
    queryFn: () => api.campaigns.get(id!).then((c: any) => c.images || []),
    enabled: activeTab === 'assets',
  })

  const updateCampaignMutation = useMutation({
    mutationFn: (data: Partial<Campaign>) => api.campaigns.update(id!, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign', id] }),
  })

  const generateAnglesMutation = useMutation({
    mutationFn: () => api.campaigns.angles.generate(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-angles', id] }),
  })

  const selectAngleMutation = useMutation({
    mutationFn: (angleId: string) => api.campaigns.angles.select(id!, angleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-angles', id] }),
  })

  const generateOfferMutation = useMutation({
    mutationFn: () => api.campaigns.offer.generate(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-offer', id] }),
  })

  const generateLandingMutation = useMutation({
    mutationFn: () => api.campaigns.landing.generate(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-landing', id] }),
  })

  const publishMutation = useMutation({
    mutationFn: () => api.campaigns.publish(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign', id] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.campaigns.delete(id!),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['campaigns'] }); navigate('/campaigns') },
  })

  const generateVdMutation = useMutation({
    mutationFn: () => api.campaigns.generateVisualDirection(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-vd', id] }),
  })

  const updateVdMutation = useMutation({
    mutationFn: (data: any) => api.visualDirections.update(visualDirection.id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-vd', id] }),
  })

  const generateAssetsMutation = useMutation({
    mutationFn: () => api.campaigns.generateAssets(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-assets', id] }),
  })

  const selectAssetMutation = useMutation({
    mutationFn: ({ imageId, purpose }: { imageId: string; purpose: string }) => api.campaigns.selectAsset(id!, imageId, purpose),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-assets', id] }),
  })

  const importDriveAssetMutation = useMutation({
    mutationFn: (file: GoogleDriveFile) => api.googleDrive.importAsset({ file_id: file.id, campaign_id: id!, purpose: 'OTHER' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-assets', id] }),
  })

  if (isLoading || !campaign) {
    return <div className="text-center py-12 text-zinc-400">Loading...</div>
  }

  const selectedAngle = angles.find((a: SellingAngle) => a.selected)

  const [editForm, setEditForm] = useState({
    name: campaign.name,
    target_country: campaign.target_country,
    target_language: campaign.target_language,
    currency: campaign.currency,
    selling_price: campaign.selling_price?.toString() || '',
    supplier_price: campaign.supplier_price?.toString() || '',
    target_audience: campaign.target_audience || '',
    payment_strategy: campaign.payment_strategy || '',
    shipping_strategy: campaign.shipping_strategy || '',
    notes: campaign.notes || '',
  })

  const handleSaveDetails = () => {
    updateCampaignMutation.mutate({
      name: editForm.name,
      target_country: editForm.target_country,
      target_language: editForm.target_language,
      currency: editForm.currency,
      selling_price: editForm.selling_price ? Number(editForm.selling_price) : null,
      supplier_price: editForm.supplier_price ? Number(editForm.supplier_price) : null,
      target_audience: editForm.target_audience || null,
      payment_strategy: editForm.payment_strategy || null,
      shipping_strategy: editForm.shipping_strategy || null,
      notes: editForm.notes || null,
    })
  }

  const handleStartEditOffer = () => {
    if (offer) {
      setOfferForm({
        headline: offer.headline,
        offer_type: offer.offer_type,
        primary_price: offer.primary_price,
        compare_at_price: offer.compare_at_price,
        discount_percentage: offer.discount_percentage,
        bundle_quantity: offer.bundle_quantity,
        free_shipping: offer.free_shipping,
        cash_on_delivery: offer.cash_on_delivery,
        guarantee_days: offer.guarantee_days,
        urgency_text: offer.urgency_text,
        scarcity_text: offer.scarcity_text,
        bonus_text: offer.bonus_text,
      })
      setEditingOffer(true)
    }
  }

  const handleSaveOffer = () => {
    updateCampaignMutation.mutate({ offer: offerForm } as any)
    setEditingOffer(false)
  }

  const handleSaveVd = () => {
    if (visualDirection) {
      updateVdMutation.mutate(vdForm)
    }
  }

  const startEditVd = () => {
    if (visualDirection) {
      setVdForm({
        visual_style: visualDirection.visual_style,
        tone: visualDirection.tone,
        color_notes: visualDirection.color_notes || '',
        background_style: visualDirection.background_style || '',
        photography_style: visualDirection.photography_style || '',
        audience_context: visualDirection.audience_context || '',
        additional_instructions: visualDirection.additional_instructions || '',
      })
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'details', label: 'Details' },
    { key: 'angles', label: 'Angles' },
    { key: 'offer', label: 'Offer' },
    { key: 'visual-direction', label: 'Visual Direction' },
    { key: 'assets', label: 'Assets' },
    { key: 'landing', label: 'Landing' },
    { key: 'performance', label: 'Performance' },
    { key: 'experiments', label: 'Experiments' },
    { key: 'publish-readiness', label: 'Publish Readiness' },
    { key: 'publish', label: 'Publish' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link to="/campaigns" className="text-sm text-zinc-400 hover:text-zinc-200 mb-2 block">&larr; Campaigns</Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-zinc-100">{campaign.name}</h1>
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[campaign.status] || ''}`}>
              {campaign.status}
            </span>
          </div>
        </div>
        <button
          onClick={() => { if (confirm('Delete this campaign?')) deleteMutation.mutate() }}
          className="px-4 py-2.5 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors"
        >
          Delete
        </button>
      </div>

      <div className="flex gap-1 mb-6 border-b border-zinc-700 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap ${
              activeTab === tab.key
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'details' && (
        <div className="bg-zinc-800 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Name</label>
              <input className="input" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Target Country</label>
              <input className="input" value={editForm.target_country} onChange={(e) => setEditForm({ ...editForm, target_country: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Target Language</label>
              <input className="input" value={editForm.target_language} onChange={(e) => setEditForm({ ...editForm, target_language: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Currency</label>
              <input className="input" value={editForm.currency} onChange={(e) => setEditForm({ ...editForm, currency: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Selling Price</label>
              <input className="input" type="number" step="0.01" value={editForm.selling_price} onChange={(e) => setEditForm({ ...editForm, selling_price: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Supplier Price</label>
              <input className="input" type="number" step="0.01" value={editForm.supplier_price} onChange={(e) => setEditForm({ ...editForm, supplier_price: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Target Audience</label>
            <input className="input" value={editForm.target_audience} onChange={(e) => setEditForm({ ...editForm, target_audience: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Payment Strategy</label>
              <input className="input" value={editForm.payment_strategy} onChange={(e) => setEditForm({ ...editForm, payment_strategy: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Shipping Strategy</label>
              <input className="input" value={editForm.shipping_strategy} onChange={(e) => setEditForm({ ...editForm, shipping_strategy: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Notes</label>
            <textarea className="input min-h-[100px]" value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} />
          </div>
          <div className="flex justify-end">
            <button onClick={handleSaveDetails} className="btn-primary" disabled={updateCampaignMutation.isPending}>
              {updateCampaignMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'angles' && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-zinc-100">Selling Angles</h3>
            <button onClick={() => generateAnglesMutation.mutate()} className="btn-secondary" disabled={generateAnglesMutation.isPending}>
              {generateAnglesMutation.isPending ? 'Generating...' : 'Generate Angles'}
            </button>
          </div>
          {angles.length === 0 ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No angles generated yet</p>
              <button onClick={() => generateAnglesMutation.mutate()} className="btn-primary" disabled={generateAnglesMutation.isPending}>
                Generate Selling Angles
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-6">
              {angles.map((angle: SellingAngle) => (
                <div key={angle.id} className={`bg-zinc-800 rounded-xl p-6 border ${angle.selected ? 'border-indigo-500 ring-1 ring-indigo-500' : 'border-zinc-700'}`}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-semibold text-zinc-100">{angle.name}</span>
                    <span className="text-sm font-bold text-indigo-400">{angle.score}</span>
                  </div>
                  <div className="space-y-3 text-sm">
                    <div>
                      <span className="text-zinc-500 text-xs uppercase tracking-wide">Audience</span>
                      <p className="text-zinc-300">{angle.target_audience}</p>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-xs uppercase tracking-wide">Pain Point</span>
                      <p className="text-zinc-400">{angle.pain_point}</p>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-xs uppercase tracking-wide">Hook</span>
                      <p className="italic text-zinc-400">"{angle.hook}"</p>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-xs uppercase tracking-wide">Promise</span>
                      <p className="text-zinc-400">{angle.main_promise}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => selectAngleMutation.mutate(angle.id)}
                    disabled={angle.selected}
                    className={`w-full mt-4 py-2 rounded-lg text-sm font-medium transition-colors ${angle.selected ? 'bg-indigo-600 text-white' : 'btn-secondary'}`}
                  >
                    {angle.selected ? 'Selected' : 'Use this angle'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'offer' && (
        <div className="bg-zinc-800 rounded-xl p-6">
          {!offer && !editingOffer ? (
            <div className="text-center py-12">
              <p className="text-zinc-400 mb-4">No offer generated yet</p>
              <button onClick={() => generateOfferMutation.mutate()} className="btn-primary" disabled={generateOfferMutation.isPending}>
                {generateOfferMutation.isPending ? 'Generating...' : 'Generate Offer'}
              </button>
            </div>
          ) : editingOffer ? (
            <div className="space-y-4">
              <h3 className="font-semibold text-zinc-100">Edit Offer</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Headline</label>
                  <input className="input" value={offerForm.headline || ''} onChange={(e) => setOfferForm({ ...offerForm, headline: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Offer Type</label>
                  <select className="input" value={offerForm.offer_type || ''} onChange={(e) => setOfferForm({ ...offerForm, offer_type: e.target.value as any })}>
                    {Object.values(offerTypeLabels).map((label, i) => (
                      <option key={i} value={Object.keys(offerTypeLabels)[i]}>{label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Primary Price</label>
                  <input className="input" type="number" step="0.01" value={offerForm.primary_price || ''} onChange={(e) => setOfferForm({ ...offerForm, primary_price: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Compare At Price</label>
                  <input className="input" type="number" step="0.01" value={offerForm.compare_at_price || ''} onChange={(e) => setOfferForm({ ...offerForm, compare_at_price: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Discount %</label>
                  <input className="input" type="number" value={offerForm.discount_percentage || ''} onChange={(e) => setOfferForm({ ...offerForm, discount_percentage: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Guarantee Days</label>
                  <input className="input" type="number" value={offerForm.guarantee_days || ''} onChange={(e) => setOfferForm({ ...offerForm, guarantee_days: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Urgency Text</label>
                  <input className="input" value={offerForm.urgency_text || ''} onChange={(e) => setOfferForm({ ...offerForm, urgency_text: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Scarcity Text</label>
                  <input className="input" value={offerForm.scarcity_text || ''} onChange={(e) => setOfferForm({ ...offerForm, scarcity_text: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Bonus Text</label>
                  <input className="input" value={offerForm.bonus_text || ''} onChange={(e) => setOfferForm({ ...offerForm, bonus_text: e.target.value })} />
                </div>
                <div className="col-span-2 flex items-center gap-6">
                  <label className="flex items-center gap-2 text-sm text-zinc-300">
                    <input type="checkbox" checked={offerForm.free_shipping || false} onChange={(e) => setOfferForm({ ...offerForm, free_shipping: e.target.checked })} className="rounded" />
                    Free Shipping
                  </label>
                  <label className="flex items-center gap-2 text-sm text-zinc-300">
                    <input type="checkbox" checked={offerForm.cash_on_delivery || false} onChange={(e) => setOfferForm({ ...offerForm, cash_on_delivery: e.target.checked })} className="rounded" />
                    Cash on Delivery
                  </label>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button onClick={() => setEditingOffer(false)} className="btn-secondary">Cancel</button>
                <button onClick={handleSaveOffer} className="btn-primary">Save Offer</button>
              </div>
            </div>
          ) : offer ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-zinc-100">{offer.headline}</h3>
                <button onClick={handleStartEditOffer} className="btn-secondary">Edit</button>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-zinc-500 text-xs uppercase tracking-wide">Type</span>
                  <p className="text-zinc-200 mt-1">{offerTypeLabels[offer.offer_type] || offer.offer_type}</p>
                </div>
                <div>
                  <span className="text-zinc-500 text-xs uppercase tracking-wide">Price</span>
                  <p className="text-zinc-200 mt-1">${offer.primary_price}</p>
                </div>
                {offer.compare_at_price && (
                  <div>
                    <span className="text-zinc-500 text-xs uppercase tracking-wide">Compare At</span>
                    <p className="text-zinc-200 mt-1">${offer.compare_at_price}</p>
                  </div>
                )}
                {offer.discount_percentage && (
                  <div>
                    <span className="text-zinc-500 text-xs uppercase tracking-wide">Discount</span>
                    <p className="text-zinc-200 mt-1">{offer.discount_percentage}%</p>
                  </div>
                )}
                {offer.guarantee_days && (
                  <div>
                    <span className="text-zinc-500 text-xs uppercase tracking-wide">Guarantee</span>
                    <p className="text-zinc-200 mt-1">{offer.guarantee_days} days</p>
                  </div>
                )}
              </div>
              <div className="flex gap-4 text-sm">
                {offer.free_shipping && <span className="text-teal-400">Free Shipping</span>}
                {offer.cash_on_delivery && <span className="text-teal-400">COD</span>}
              </div>
              {offer.urgency_text && <p className="text-sm text-amber-400">{offer.urgency_text}</p>}
              {offer.scarcity_text && <p className="text-sm text-amber-400">{offer.scarcity_text}</p>}
              {offer.bonus_text && <p className="text-sm text-green-400">{offer.bonus_text}</p>}
            </div>
          ) : null}
        </div>
      )}

      {activeTab === 'visual-direction' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-zinc-100">Visual Direction</h3>
            <div className="flex gap-2">
              {visualDirection && (
                <button onClick={startEditVd} className="btn-secondary">Edit</button>
              )}
              <button onClick={() => generateVdMutation.mutate()} className="btn-secondary" disabled={generateVdMutation.isPending}>
                {generateVdMutation.isPending ? 'Generating...' : 'Generate Direction'}
              </button>
            </div>
          </div>
          {!visualDirection ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No visual direction generated yet</p>
              <button onClick={() => generateVdMutation.mutate()} className="btn-primary" disabled={generateVdMutation.isPending}>
                {generateVdMutation.isPending ? 'Generating...' : 'Generate Visual Direction'}
              </button>
            </div>
          ) : (
            <div className="bg-zinc-800 rounded-xl p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Visual Style</label>
                  <input className="input" value={vdForm.visual_style ?? visualDirection.visual_style} onChange={(e) => setVdForm({ ...vdForm, visual_style: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Tone</label>
                  <input className="input" value={vdForm.tone ?? visualDirection.tone} onChange={(e) => setVdForm({ ...vdForm, tone: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Color Notes</label>
                  <input className="input" value={vdForm.color_notes ?? visualDirection.color_notes ?? ''} onChange={(e) => setVdForm({ ...vdForm, color_notes: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Background Style</label>
                  <input className="input" value={vdForm.background_style ?? visualDirection.background_style ?? ''} onChange={(e) => setVdForm({ ...vdForm, background_style: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Photography Style</label>
                  <input className="input" value={vdForm.photography_style ?? visualDirection.photography_style ?? ''} onChange={(e) => setVdForm({ ...vdForm, photography_style: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Audience Context</label>
                  <input className="input" value={vdForm.audience_context ?? visualDirection.audience_context ?? ''} onChange={(e) => setVdForm({ ...vdForm, audience_context: e.target.value })} />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Additional Instructions</label>
                  <textarea className="input min-h-[80px]" value={vdForm.additional_instructions ?? visualDirection.additional_instructions ?? ''} onChange={(e) => setVdForm({ ...vdForm, additional_instructions: e.target.value })} />
                </div>
              </div>
              <div className="flex justify-end">
                <button onClick={handleSaveVd} className="btn-primary" disabled={updateVdMutation.isPending}>
                  {updateVdMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'assets' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-zinc-100">Visual Assets</h3>
            <div className="flex gap-2">
              <button onClick={() => setShowDriveBrowser(!showDriveBrowser)} className="btn-secondary text-sm">
                {showDriveBrowser ? 'Hide Drive' : 'Import from Drive'}
              </button>
              <button onClick={() => generateAssetsMutation.mutate()} className="btn-secondary" disabled={generateAssetsMutation.isPending}>
                {generateAssetsMutation.isPending ? 'Generating...' : 'Generate Launch Pack'}
              </button>
            </div>
          </div>
          {showDriveBrowser && (
            <GoogleDriveBrowser
              selectionMode="asset"
              onSelect={(file) => { importDriveAssetMutation.mutate(file); setShowDriveBrowser(false) }}
              onClose={() => setShowDriveBrowser(false)}
            />
          )}
          {assets.length === 0 ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No assets generated yet</p>
              <button onClick={() => generateAssetsMutation.mutate()} className="btn-primary" disabled={generateAssetsMutation.isPending}>
                {generateAssetsMutation.isPending ? 'Generating...' : 'Generate Launch Pack'}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              {assets.map((asset: CampaignImage) => (
                <div key={asset.id} className={`bg-zinc-800 rounded-xl overflow-hidden border ${asset.selected ? 'border-indigo-500' : 'border-zinc-700'}`}>
                  <div className="aspect-square bg-zinc-700">
                    <img src={asset.image_url} alt={asset.purpose} className="w-full h-full object-cover" />
                  </div>
                  <div className="p-3 flex items-center justify-between">
                    <div>
                      <span className="text-xs font-medium text-zinc-300 uppercase">{asset.purpose}</span>
                      <span className="text-xs text-zinc-500 ml-2">({asset.source_type})</span>
                    </div>
                    {!asset.selected ? (
                      <div className="flex gap-1">
                        <button onClick={() => selectAssetMutation.mutate({ imageId: asset.id, purpose: 'HERO' })} className="text-xs px-2 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-500">
                          Use as Hero
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-indigo-400 font-medium">Selected</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'landing' && (
        <div>
          {!landing ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No landing page generated yet</p>
              <button onClick={() => generateLandingMutation.mutate()} className="btn-primary" disabled={generateLandingMutation.isPending}>
                {generateLandingMutation.isPending ? 'Generating...' : 'Generate Landing'}
              </button>
              {!selectedAngle && <p className="text-xs text-zinc-500 mt-2">Select a selling angle first</p>}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-zinc-100">{landing.title}</h3>
                  <p className="text-sm text-zinc-400">Version {landing.version} &middot; {landing.status}</p>
                </div>
                <Link to={`/campaigns/${id}/landing`} className="btn-secondary">Preview</Link>
              </div>
              <div className="space-y-3">
                {landing.sections.map((section: any) => (
                  <div key={section.id} className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
                    <div className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-2">{section.section_type}</div>
                    <pre className="text-xs text-zinc-400 overflow-auto max-h-32">{JSON.stringify(section.content, null, 2)}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'publish-readiness' && (
        <div className="space-y-6">
          <h3 className="font-semibold text-zinc-100">Publish Readiness</h3>
          {!publishReadiness ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">Click to check publish readiness</p>
              <button onClick={() => queryClient.invalidateQueries({ queryKey: ['campaign-readiness', id] })} className="btn-primary">
                Check Readiness
              </button>
            </div>
          ) : (
            <div className="bg-zinc-800 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-3 mb-4">
                {publishReadiness.ready ? (
                  <span className="text-lg font-semibold text-green-400">Ready to Publish</span>
                ) : (
                  <span className="text-lg font-semibold text-amber-400">Not Ready</span>
                )}
              </div>
              <div className="space-y-2">
                {publishReadiness.checks.map((check: any) => (
                  <div key={check.key} className="flex items-center gap-3 p-3 bg-zinc-700/30 rounded-lg">
                    <span className={`text-lg ${check.status === 'pass' ? 'text-green-400' : check.status === 'fail' ? 'text-red-400' : 'text-zinc-400'}`}>
                      {check.status === 'pass' ? '\u2713' : check.status === 'fail' ? '\u2717' : '\u2014'}
                    </span>
                    <div>
                      <span className="text-sm font-medium text-zinc-200">{check.key.replace(/_/g, ' ')}</span>
                      {check.message && <span className="text-xs text-zinc-400 ml-2">({check.message})</span>}
                    </div>
                  </div>
                ))}
              </div>
              {publishReadiness.ready && (
                <button onClick={() => publishMutation.mutate()} className="btn-primary mt-4" disabled={publishMutation.isPending}>
                  {publishMutation.isPending ? 'Publishing...' : 'Publish Campaign'}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'publish' && (
        <div className="bg-zinc-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="font-semibold text-zinc-100 mb-2">Publish Status</h3>
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[campaign.status] || ''}`}>
                {campaign.status}
              </span>
              {campaign.published_at && (
                <span className="text-sm text-zinc-400">Published {new Date(campaign.published_at).toLocaleString()}</span>
              )}
            </div>
            {campaign.last_publish_error && (
              <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                {campaign.last_publish_error}
              </div>
            )}
          </div>
          <div>
            <button onClick={() => publishMutation.mutate()} className="btn-primary" disabled={publishMutation.isPending || campaign.status === 'PUBLISHED'}>
              {publishMutation.isPending ? 'Publishing...' : campaign.status === 'PUBLISHED' ? 'Already Published' : 'Publish Campaign'}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'performance' && (
        <CampaignPerformanceTab campaign={campaign} />
      )}

      {activeTab === 'experiments' && (
        <CampaignExperimentsTab campaign={campaign} />
      )}
    </div>
  )
}

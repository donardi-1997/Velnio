import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { SellingAngle } from '../types'

const steps = ['Setup', 'Product', 'Angles', 'Offer', 'Visual Direction', 'Visual Assets', 'Landing', 'Publish Readiness', 'Publish']

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-500/20 text-gray-400',
  ANALYZING: 'bg-blue-500/20 text-blue-400',
  ANGLE_READY: 'bg-purple-500/20 text-purple-400',
  OFFER_READY: 'bg-indigo-500/20 text-indigo-400',
  LANDING_READY: 'bg-teal-500/20 text-teal-400',
  PUBLISHED: 'bg-green-500/20 text-green-400',
  FAILED: 'bg-red-500/20 text-red-400',
}

export function CampaignWizardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [step, setStep] = useState(0)
  const [campaignId, setCampaignId] = useState<string | null>(null)
  const [setupForm, setSetupForm] = useState({
    name: '',
    target_country: 'US',
    target_language: 'en',
    currency: 'USD',
    selling_price: '',
    supplier_price: '',
    target_audience: '',
    payment_strategy: '',
    shipping_strategy: '',
    notes: '',
  })
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null)
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null)
  const [vdForm, setVdForm] = useState({
    visual_style: '',
    tone: '',
    color_notes: '',
    background_style: '',
    photography_style: '',
    audience_context: '',
    additional_instructions: '',
  })

  const { data: stores = [] } = useQuery({ queryKey: ['stores'], queryFn: api.stores.list })
  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: api.products.list })

  const { data: campaign } = useQuery({
    queryKey: ['campaign', campaignId],
    queryFn: () => api.campaigns.get(campaignId!),
    enabled: !!campaignId,
  })

  const { data: angles = [] } = useQuery({
    queryKey: ['campaign-angles', campaignId],
    queryFn: () => api.campaigns.angles.list(campaignId!),
    enabled: !!campaignId && step >= 2,
  })

  const { data: offer } = useQuery({
    queryKey: ['campaign-offer', campaignId],
    queryFn: () => api.campaigns.offer.get(campaignId!),
    enabled: !!campaignId && step >= 3,
  })

  const { data: visualDirection } = useQuery({
    queryKey: ['campaign-vd', campaignId],
    queryFn: () => api.campaigns.getVisualDirection(campaignId!),
    enabled: !!campaignId && step >= 4,
  })

  const { data: landing } = useQuery({
    queryKey: ['campaign-landing', campaignId],
    queryFn: () => api.campaigns.landing.get(campaignId!),
    enabled: !!campaignId && step >= 6,
  })

  const { data: publishReadiness } = useQuery({
    queryKey: ['campaign-readiness', campaignId],
    queryFn: () => api.campaigns.getPublishReadiness(campaignId!),
    enabled: !!campaignId && step === 7,
  })

  const { data: assets = [] } = useQuery({
    queryKey: ['campaign-assets', campaignId],
    queryFn: () => api.campaigns.get(campaignId!).then((c: any) => c.images || []),
    enabled: !!campaignId && step === 5,
  })

  const createCampaignMutation = useMutation({
    mutationFn: (data: any) => api.campaigns.create(data),
    onSuccess: (data) => { setCampaignId(data.id); setStep(1) },
  })

  const updateCampaignMutation = useMutation({
    mutationFn: (data: any) => api.campaigns.update(campaignId!, data),
    onSuccess: () => setStep(step + 1),
  })

  const generateAnglesMutation = useMutation({
    mutationFn: () => api.campaigns.angles.generate(campaignId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-angles', campaignId] }),
  })

  const selectAngleMutation = useMutation({
    mutationFn: (angleId: string) => api.campaigns.angles.select(campaignId!, angleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-angles', campaignId] }),
  })

  const generateOfferMutation = useMutation({
    mutationFn: () => api.campaigns.offer.generate(campaignId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-offer', campaignId] }),
  })

  const generateVdMutation = useMutation({
    mutationFn: () => api.campaigns.generateVisualDirection(campaignId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-vd', campaignId] }),
  })

  const updateVdMutation = useMutation({
    mutationFn: (data: any) => api.visualDirections.update(visualDirection!.id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-vd', campaignId] }),
  })

  const generateAssetsMutation = useMutation({
    mutationFn: () => api.campaigns.generateAssets(campaignId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-assets', campaignId] }),
  })

  const generateLandingMutation = useMutation({
    mutationFn: () => api.campaigns.landing.generate(campaignId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaign-landing', campaignId] }),
  })

  const publishMutation = useMutation({
    mutationFn: () => api.campaigns.publish(campaignId!),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['campaign', campaignId] }); navigate(`/campaigns/${campaignId}`) },
  })

  const handleSetupSubmit = () => {
    createCampaignMutation.mutate({
      name: setupForm.name,
      store_id: selectedStoreId,
      target_country: setupForm.target_country,
      target_language: setupForm.target_language,
      currency: setupForm.currency,
      selling_price: setupForm.selling_price ? Number(setupForm.selling_price) : null,
      supplier_price: setupForm.supplier_price ? Number(setupForm.supplier_price) : null,
      target_audience: setupForm.target_audience || null,
      payment_strategy: setupForm.payment_strategy || null,
      shipping_strategy: setupForm.shipping_strategy || null,
      notes: setupForm.notes || null,
    })
  }

  const handleLinkProduct = () => {
    if (selectedProductId) {
      updateCampaignMutation.mutate({ product_id: selectedProductId })
    }
  }

  const handleSaveVd = () => {
    if (visualDirection) {
      updateVdMutation.mutate(vdForm)
    }
  }

  const selectedAngle = angles.find((a: SellingAngle) => a.selected)

  return (
    <div className="max-w-4xl mx-auto">
      <Link to="/campaigns" className="text-sm text-zinc-400 hover:text-zinc-200 mb-6 block">&larr; Campaigns</Link>
      <h1 className="text-2xl font-bold text-zinc-100 mb-8">Create Campaign</h1>

      {/* Stepper */}
      <div className="flex items-center mb-10 overflow-x-auto pb-2">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0 ${
                i < step ? 'bg-indigo-600 text-white' :
                i === step ? 'bg-indigo-600 text-white ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-900' :
                'bg-zinc-700 text-zinc-400'
              }`}>
                {i < step ? '\u2713' : i + 1}
              </div>
              <span className={`text-sm font-medium whitespace-nowrap ${i === step ? 'text-zinc-100' : 'text-zinc-500'}`}>{s}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`w-12 h-px mx-3 shrink-0 ${i < step ? 'bg-indigo-600' : 'bg-zinc-700'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step 0: Setup */}
      {step === 0 && (
        <div className="bg-zinc-800 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-zinc-100 mb-4">Campaign Setup</h2>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Campaign Name *</label>
            <input className="input" placeholder="e.g. Summer Sale Campaign" value={setupForm.name} onChange={(e) => setSetupForm({ ...setupForm, name: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Store</label>
            <select className="input" value={selectedStoreId || ''} onChange={(e) => setSelectedStoreId(e.target.value || null)}>
              <option value="">Select a store</option>
              {stores.map((s: any) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Target Country</label>
              <input className="input" value={setupForm.target_country} onChange={(e) => setSetupForm({ ...setupForm, target_country: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Target Language</label>
              <input className="input" value={setupForm.target_language} onChange={(e) => setSetupForm({ ...setupForm, target_language: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Currency</label>
              <input className="input" value={setupForm.currency} onChange={(e) => setSetupForm({ ...setupForm, currency: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Selling Price</label>
              <input className="input" type="number" step="0.01" value={setupForm.selling_price} onChange={(e) => setSetupForm({ ...setupForm, selling_price: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Supplier Price</label>
              <input className="input" type="number" step="0.01" value={setupForm.supplier_price} onChange={(e) => setSetupForm({ ...setupForm, supplier_price: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Target Audience</label>
            <input className="input" value={setupForm.target_audience} onChange={(e) => setSetupForm({ ...setupForm, target_audience: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Payment Strategy</label>
              <input className="input" value={setupForm.payment_strategy} onChange={(e) => setSetupForm({ ...setupForm, payment_strategy: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Shipping Strategy</label>
              <input className="input" value={setupForm.shipping_strategy} onChange={(e) => setSetupForm({ ...setupForm, shipping_strategy: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Notes</label>
            <textarea className="input min-h-[80px]" value={setupForm.notes} onChange={(e) => setSetupForm({ ...setupForm, notes: e.target.value })} />
          </div>
          <div className="flex justify-end pt-2">
            <button onClick={handleSetupSubmit} className="btn-primary" disabled={!setupForm.name || createCampaignMutation.isPending}>
              {createCampaignMutation.isPending ? 'Creating...' : 'Next: Link Product \u2192'}
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Product */}
      {step === 1 && (
        <div className="bg-zinc-800 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-zinc-100 mb-4">Link Product</h2>
          {campaign?.product ? (
            <div className="p-4 bg-zinc-700/50 rounded-lg">
              <p className="text-sm text-zinc-300">Linked to: <span className="font-medium text-zinc-100">{campaign.product.name}</span></p>
              <p className="text-xs text-zinc-500 mt-1">{campaign.product_id}</p>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Select Product</label>
                <select className="input" value={selectedProductId || ''} onChange={(e) => setSelectedProductId(e.target.value || null)}>
                  <option value="">Choose a product</option>
                  {products.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-500">
                <span>or</span>
                <Link to="/products/new" className="text-indigo-400 hover:underline">Create new product</Link>
              </div>
            </>
          )}
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(0)} className="btn-secondary">\u2190 Back</button>
            <button onClick={handleLinkProduct} className="btn-primary" disabled={!selectedProductId && !campaign?.product_id || updateCampaignMutation.isPending}>
              {updateCampaignMutation.isPending ? 'Linking...' : 'Next: Generate Angles \u2192'}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Angles */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="bg-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-zinc-100">Selling Angles</h2>
              <button onClick={() => generateAnglesMutation.mutate()} className="btn-secondary" disabled={generateAnglesMutation.isPending}>
                {generateAnglesMutation.isPending ? 'Generating...' : 'Generate Angles'}
              </button>
            </div>
            {angles.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-zinc-400 mb-4">No angles generated yet</p>
                <button onClick={() => generateAnglesMutation.mutate()} className="btn-primary" disabled={generateAnglesMutation.isPending}>
                  Generate Selling Angles
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {angles.map((angle: SellingAngle) => (
                  <div key={angle.id} className={`p-4 rounded-lg border ${angle.selected ? 'border-indigo-500 bg-indigo-500/10' : 'border-zinc-700 bg-zinc-700/30'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-zinc-100">{angle.name}</span>
                      <span className="text-sm font-bold text-indigo-400">{angle.score}</span>
                    </div>
                    <p className="text-sm text-zinc-400 mb-1">{angle.target_audience}</p>
                    <p className="text-xs text-zinc-500 italic mb-3">"{angle.hook}"</p>
                    <button
                      onClick={() => selectAngleMutation.mutate(angle.id)}
                      disabled={angle.selected}
                      className={`w-full py-1.5 rounded-lg text-sm font-medium transition-colors ${angle.selected ? 'bg-indigo-600 text-white' : 'bg-zinc-600 text-zinc-200 hover:bg-zinc-500'}`}
                    >
                      {angle.selected ? 'Selected' : 'Select'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(1)} className="btn-secondary">\u2190 Back</button>
            <button onClick={() => setStep(3)} className="btn-primary" disabled={!selectedAngle}>
              Next: Generate Offer \u2192
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Offer */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="bg-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-zinc-100">Offer</h2>
              {!offer && (
                <button onClick={() => generateOfferMutation.mutate()} className="btn-secondary" disabled={generateOfferMutation.isPending}>
                  {generateOfferMutation.isPending ? 'Generating...' : 'Generate Offer'}
                </button>
              )}
            </div>
            {!offer ? (
              <div className="text-center py-8">
                <p className="text-zinc-400 mb-4">No offer generated yet</p>
                <button onClick={() => generateOfferMutation.mutate()} className="btn-primary" disabled={generateOfferMutation.isPending}>
                  Generate Offer
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <h3 className="text-lg font-medium text-zinc-100">{offer.headline}</h3>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div><span className="text-zinc-500">Type:</span> <span className="text-zinc-200 ml-1">{offer.offer_type}</span></div>
                  <div><span className="text-zinc-500">Price:</span> <span className="text-zinc-200 ml-1">${offer.primary_price}</span></div>
                  {offer.compare_at_price && <div><span className="text-zinc-500">Compare:</span> <span className="text-zinc-200 ml-1">${offer.compare_at_price}</span></div>}
                </div>
                <div className="flex gap-4 text-sm">
                  {offer.free_shipping && <span className="text-teal-400">Free Shipping</span>}
                  {offer.cash_on_delivery && <span className="text-teal-400">COD</span>}
                </div>
                {offer.urgency_text && <p className="text-sm text-amber-400">{offer.urgency_text}</p>}
              </div>
            )}
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="btn-secondary">\u2190 Back</button>
            <button onClick={() => setStep(4)} className="btn-primary" disabled={!offer}>
              Next: Visual Direction \u2192
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Visual Direction */}
      {step === 4 && (
        <div className="space-y-4">
          <div className="bg-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-zinc-100">Visual Direction</h2>
              {!visualDirection && (
                <button onClick={() => generateVdMutation.mutate()} className="btn-secondary" disabled={generateVdMutation.isPending}>
                  {generateVdMutation.isPending ? 'Generating...' : 'Generate Direction'}
                </button>
              )}
            </div>
            {!visualDirection ? (
              <div className="text-center py-8">
                <p className="text-zinc-400 mb-4">Generate a visual direction to guide asset creation</p>
                <button onClick={() => generateVdMutation.mutate()} className="btn-primary" disabled={generateVdMutation.isPending}>
                  {generateVdMutation.isPending ? 'Generating...' : 'Generate Visual Direction'}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-1">Visual Style</label>
                    <input className="input" value={vdForm.visual_style || visualDirection.visual_style} onChange={(e) => setVdForm({ ...vdForm, visual_style: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-1">Tone</label>
                    <input className="input" value={vdForm.tone || visualDirection.tone} onChange={(e) => setVdForm({ ...vdForm, tone: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-1">Color Notes</label>
                    <input className="input" value={vdForm.color_notes || visualDirection.color_notes || ''} onChange={(e) => setVdForm({ ...vdForm, color_notes: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-1">Background Style</label>
                    <input className="input" value={vdForm.background_style || visualDirection.background_style || ''} onChange={(e) => setVdForm({ ...vdForm, background_style: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-1">Photography Style</label>
                    <input className="input" value={vdForm.photography_style || visualDirection.photography_style || ''} onChange={(e) => setVdForm({ ...vdForm, photography_style: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-1">Audience Context</label>
                    <input className="input" value={vdForm.audience_context || visualDirection.audience_context || ''} onChange={(e) => setVdForm({ ...vdForm, audience_context: e.target.value })} />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-zinc-300 mb-1">Additional Instructions</label>
                    <textarea className="input min-h-[80px]" value={vdForm.additional_instructions || visualDirection.additional_instructions || ''} onChange={(e) => setVdForm({ ...vdForm, additional_instructions: e.target.value })} />
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
          <div className="flex justify-between">
            <button onClick={() => setStep(3)} className="btn-secondary">\u2190 Back</button>
            <button onClick={() => setStep(5)} className="btn-primary" disabled={!visualDirection}>
              Next: Visual Assets \u2192
            </button>
          </div>
        </div>
      )}

      {/* Step 5: Visual Assets */}
      {step === 5 && (
        <div className="space-y-4">
          <div className="bg-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-zinc-100">Visual Assets</h2>
              <button onClick={() => generateAssetsMutation.mutate()} className="btn-secondary" disabled={generateAssetsMutation.isPending}>
                {generateAssetsMutation.isPending ? 'Generating...' : 'Generate Launch Pack'}
              </button>
            </div>
            {assets.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-zinc-400 mb-4">No assets generated yet</p>
                <button onClick={() => generateAssetsMutation.mutate()} className="btn-primary" disabled={generateAssetsMutation.isPending}>
                  {generateAssetsMutation.isPending ? 'Generating...' : 'Generate Launch Pack'}
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-4">
                {assets.map((asset: any) => (
                  <div key={asset.id} className="bg-zinc-700/30 rounded-lg overflow-hidden border border-zinc-700">
                    <div className="aspect-square bg-zinc-700">
                      <img src={asset.image_url} alt={asset.purpose} className="w-full h-full object-cover" />
                    </div>
                    <div className="p-2 text-center">
                      <span className="text-xs font-medium text-zinc-300 uppercase">{asset.purpose}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(4)} className="btn-secondary">\u2190 Back</button>
            <button onClick={() => setStep(6)} className="btn-primary">
              Next: Landing Page \u2192
            </button>
          </div>
        </div>
      )}

      {/* Step 6: Landing */}
      {step === 6 && (
        <div className="space-y-4">
          <div className="bg-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-zinc-100">Landing Page</h2>
              {!landing && (
                <button onClick={() => generateLandingMutation.mutate()} className="btn-secondary" disabled={generateLandingMutation.isPending}>
                  {generateLandingMutation.isPending ? 'Generating...' : 'Generate Landing'}
                </button>
              )}
            </div>
            {!landing ? (
              <div className="text-center py-8">
                <p className="text-zinc-400 mb-4">No landing page generated yet</p>
                <button onClick={() => generateLandingMutation.mutate()} className="btn-primary" disabled={generateLandingMutation.isPending}>
                  Generate Landing
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <h3 className="text-lg font-medium text-zinc-100">{landing.title}</h3>
                <p className="text-sm text-zinc-400">Version {landing.version}</p>
                <div className="space-y-2">
                  {landing.sections.map((section: any) => (
                    <div key={section.id} className="p-3 bg-zinc-700/30 rounded-lg border border-zinc-700">
                      <div className="text-xs font-medium text-zinc-500 uppercase">{section.section_type}</div>
                      <pre className="text-xs text-zinc-400 mt-1 overflow-auto max-h-20">{JSON.stringify(section.content, null, 2)}</pre>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(5)} className="btn-secondary">\u2190 Back</button>
            <button onClick={() => setStep(7)} className="btn-primary" disabled={!landing}>
              Next: Publish Readiness \u2192
            </button>
          </div>
        </div>
      )}

      {/* Step 7: Publish Readiness */}
      {step === 7 && (
        <div className="space-y-4">
          <div className="bg-zinc-800 rounded-xl p-6">
            <h2 className="font-semibold text-zinc-100 mb-4">Publish Readiness</h2>
            {!publishReadiness ? (
              <div className="text-center py-8">
                <p className="text-zinc-400 mb-4">Checking publish readiness...</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-3 mb-4">
                  {publishReadiness.ready ? (
                    <span className="text-lg font-semibold text-green-400">All checks passed</span>
                  ) : (
                    <span className="text-lg font-semibold text-amber-400">Some checks failed</span>
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
              </div>
            )}
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(6)} className="btn-secondary">\u2190 Back</button>
            <button onClick={() => setStep(8)} className="btn-primary" disabled={!publishReadiness?.ready}>
              Next: Publish \u2192
            </button>
          </div>
        </div>
      )}

      {/* Step 8: Publish */}
      {step === 8 && (
        <div className="bg-zinc-800 rounded-xl p-6 space-y-6">
          <h2 className="font-semibold text-zinc-100">Review & Publish</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><span className="text-zinc-500">Name:</span> <span className="text-zinc-200 ml-2">{campaign?.name}</span></div>
            <div><span className="text-zinc-500">Status:</span> <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[campaign?.status || ''] || ''}`}>{campaign?.status}</span></div>
            <div><span className="text-zinc-500">Country:</span> <span className="text-zinc-200 ml-2">{campaign?.target_country}</span></div>
            <div><span className="text-zinc-500">Language:</span> <span className="text-zinc-200 ml-2">{campaign?.target_language}</span></div>
            <div><span className="text-zinc-500">Price:</span> <span className="text-zinc-200 ml-2">{campaign?.selling_price ? `$${campaign.selling_price}` : '-'}</span></div>
            <div><span className="text-zinc-500">Angle:</span> <span className="text-zinc-200 ml-2">{selectedAngle?.name || 'None'}</span></div>
          </div>
          <div className="p-4 bg-zinc-700/30 rounded-lg text-sm text-zinc-400">
            <p className="mb-2">Publishing will make the landing page live and update the product on your store.</p>
            <p>This action can be reverted by unpublishing.</p>
          </div>
          <div className="flex justify-between">
            <button onClick={() => setStep(7)} className="btn-secondary">\u2190 Back</button>
            <button onClick={() => publishMutation.mutate()} className="btn-primary" disabled={publishMutation.isPending || campaign?.status === 'PUBLISHED'}>
              {publishMutation.isPending ? 'Publishing...' : 'Publish Campaign'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

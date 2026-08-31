import { useState, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ProductEnrichment } from '../types'

const campaignStatusColors: Record<string, string> = {
  DRAFT: 'bg-gray-500/20 text-gray-400',
  ANALYZING: 'bg-blue-500/20 text-blue-400',
  ANGLE_READY: 'bg-purple-500/20 text-purple-400',
  OFFER_READY: 'bg-indigo-500/20 text-indigo-400',
  LANDING_READY: 'bg-teal-500/20 text-teal-400',
  PUBLISHED: 'bg-green-500/20 text-green-400',
  FAILED: 'bg-red-500/20 text-red-400',
}

type Tab = 'overview' | 'import' | 'images' | 'enrichment' | 'analysis' | 'angles' | 'landing' | 'campaigns'

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [importUrl, setImportUrl] = useState('')
  const [importPreview, setImportPreview] = useState<any>(null)
  const [importForm, setImportForm] = useState<any>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: product } = useQuery({ queryKey: ['product', id], queryFn: () => api.products.get(id!) })
  const { data: analysis } = useQuery({ queryKey: ['analysis', id], queryFn: () => api.products.get(id!).then(p => p.analysis), enabled: activeTab === 'analysis' })
  const { data: angles = [] } = useQuery({ queryKey: ['angles', id], queryFn: () => api.angles.list(id!), enabled: activeTab === 'angles' })
  const { data: landing } = useQuery({ queryKey: ['landing', id], queryFn: () => api.landing.get(id!), enabled: activeTab === 'landing' })
  const { data: campaigns = [] } = useQuery({ queryKey: ['campaigns-for-product', id], queryFn: () => api.campaigns.byProduct(id!), enabled: activeTab === 'campaigns' })
  const { data: enrichment } = useQuery({ queryKey: ['enrichment', id], queryFn: () => api.products.getEnrichment(id!), enabled: activeTab === 'enrichment' })

  const analyzeMutation = useMutation({ mutationFn: () => api.products.analyze(id!), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['product', id] }) })
  const generateAnglesMutation = useMutation({ mutationFn: () => api.angles.generate(id!), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['angles', id] }) })
  const selectAngleMutation = useMutation({ mutationFn: (angleId: string) => api.angles.select(id!, angleId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['angles', id] }) })
  const generateLandingMutation = useMutation({ mutationFn: () => api.landing.generate(id!), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['landing', id] }); setActiveTab('landing') } })
  const publishMutation = useMutation({ mutationFn: () => api.products.publish(id!), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['product', id] }) })
  const enrichMutation = useMutation({ mutationFn: () => api.products.enrich(id!), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['enrichment', id] }) })
  const importPreviewMutation = useMutation({ mutationFn: (url: string) => api.products.importPreview(url), onSuccess: (data) => { setImportPreview(data); setImportForm({ ...data }) } })
  const importCreateMutation = useMutation({
    mutationFn: (data: any) => api.products.importCreate(data),
    onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ['products'] }); navigate(`/products/${data.id}`) },
  })
  const uploadImagesMutation = useMutation({
    mutationFn: (files: File[]) => api.products.uploadImages(id!, files),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['product', id] }),
  })

  const handleImportPreview = () => {
    if (importUrl) importPreviewMutation.mutate(importUrl)
  }

  const handleImportCreate = () => {
    if (importForm) {
      importCreateMutation.mutate({
        url: importPreview.source_url,
        name: importForm.name,
        description: importForm.description,
        price: importForm.price,
        currency: importForm.currency,
      })
    }
  }

  const handleFileUpload = (files: FileList | null) => {
    if (files && files.length > 0) {
      uploadImagesMutation.mutate(Array.from(files))
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    handleFileUpload(e.dataTransfer.files)
  }

  if (!product) return <div className="text-center py-12 text-zinc-400">Loading...</div>

  const selectedAngle = angles.find((a: any) => a.selected)

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'import', label: 'Import' },
    { key: 'images', label: 'Images' },
    { key: 'enrichment', label: 'Enrichment' },
    { key: 'analysis', label: 'Analysis' },
    { key: 'angles', label: 'Angles' },
    { key: 'landing', label: 'Landing' },
    { key: 'campaigns', label: 'Campaigns' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link to="/products" className="text-sm text-zinc-400 hover:text-zinc-200 mb-2 block">&larr; Products</Link>
          <h1 className="text-2xl font-bold text-zinc-100">{product.name}</h1>
        </div>
        <div className="flex gap-2">
          {product.status === 'PUBLISHED' && <span className="text-sm text-green-400 font-medium">Published</span>}
          <button onClick={() => publishMutation.mutate()} className="btn-secondary" disabled={publishMutation.isPending}>
            {publishMutation.isPending ? 'Publishing...' : 'Publish to Shopify'}
          </button>
          <Link to={`/products/${id}/landing`} className="btn-secondary">Preview Landing</Link>
        </div>
      </div>

      <div className="flex gap-1 mb-6 border-b border-zinc-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.key
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-zinc-800 rounded-xl p-6 space-y-4">
            <h3 className="font-semibold text-zinc-100">Product Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-zinc-400">Name</span><span className="text-zinc-200">{product.name}</span></div>
              <div className="flex justify-between"><span className="text-zinc-400">Status</span><span className="text-zinc-200">{product.status}</span></div>
              <div className="flex justify-between"><span className="text-zinc-400">Country</span><span className="text-zinc-200">{product.target_country}</span></div>
              <div className="flex justify-between"><span className="text-zinc-400">Selling Price</span><span className="text-zinc-200">{product.selling_price ? `$${product.selling_price}` : '-'}</span></div>
              <div className="flex justify-between"><span className="text-zinc-400">Supplier Price</span><span className="text-zinc-200">{product.supplier_price ? `$${product.supplier_price}` : '-'}</span></div>
              <div className="flex justify-between"><span className="text-zinc-400">Source</span><span className="text-zinc-200">{product.source_type}</span></div>
              {product.source_domain && <div className="flex justify-between"><span className="text-zinc-400">Domain</span><span className="text-zinc-200">{product.source_domain}</span></div>}
            </div>
          </div>
          <div className="bg-zinc-800 rounded-xl p-6">
            <h3 className="font-semibold mb-4 text-zinc-100">Actions</h3>
            <div className="space-y-3">
              <button onClick={() => analyzeMutation.mutate()} className="btn-primary w-full" disabled={analyzeMutation.isPending}>
                {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze Product'}
              </button>
              <button onClick={() => generateAnglesMutation.mutate()} className="btn-primary w-full" disabled={generateAnglesMutation.isPending || product.status === 'DRAFT'}>
                {generateAnglesMutation.isPending ? 'Generating...' : 'Generate Selling Angles'}
              </button>
              <button onClick={() => generateLandingMutation.mutate()} className="btn-primary w-full" disabled={generateLandingMutation.isPending || !selectedAngle}>
                {generateLandingMutation.isPending ? 'Generating...' : 'Generate Landing'}
              </button>
              <button onClick={() => { setActiveTab('enrichment'); enrichMutation.mutate() }} className="btn-primary w-full" disabled={enrichMutation.isPending}>
                {enrichMutation.isPending ? 'Enriching...' : 'Enrich Product'}
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'import' && (
        <div className="bg-zinc-800 rounded-xl p-6 space-y-6">
          <h3 className="font-semibold text-zinc-100">Import from URL</h3>
          <div className="flex gap-3">
            <input
              className="input flex-1"
              placeholder="Enter product URL (e.g. https://example.com/product)"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
            />
            <button onClick={handleImportPreview} className="btn-primary" disabled={!importUrl || importPreviewMutation.isPending}>
              {importPreviewMutation.isPending ? 'Fetching...' : 'Preview'}
            </button>
          </div>
          {importPreview && (
            <div className="space-y-4 pt-4 border-t border-zinc-700">
              <h4 className="font-medium text-zinc-200">Import Preview</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Name</label>
                  <input className="input" value={importForm?.name || ''} onChange={(e) => setImportForm({ ...importForm, name: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Price</label>
                  <input className="input" type="number" step="0.01" value={importForm?.price || ''} onChange={(e) => setImportForm({ ...importForm, price: Number(e.target.value) })} />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-zinc-300 mb-1">Description</label>
                  <textarea className="input min-h-[100px]" value={importForm?.description || ''} onChange={(e) => setImportForm({ ...importForm, description: e.target.value })} />
                </div>
              </div>
              {importPreview.images && importPreview.images.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">Images</label>
                  <div className="grid grid-cols-4 gap-3">
                    {importPreview.images.map((img: any, i: number) => (
                      <div key={i} className="aspect-square bg-zinc-700 rounded-lg overflow-hidden">
                        <img src={img.url} alt={`Preview ${i}`} className="w-full h-full object-cover" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {importPreview.metadata && Object.keys(importPreview.metadata).length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">Metadata</label>
                  <pre className="bg-zinc-900 rounded-lg p-3 text-xs text-zinc-400 overflow-auto max-h-32">
                    {JSON.stringify(importPreview.metadata, null, 2)}
                  </pre>
                </div>
              )}
              <div className="flex justify-end">
                <button onClick={handleImportCreate} className="btn-primary" disabled={importCreateMutation.isPending}>
                  {importCreateMutation.isPending ? 'Creating...' : 'Create Product'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'images' && (
        <div className="bg-zinc-800 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-zinc-100">Product Images</h3>
            <div className="flex gap-2">
              <input ref={fileInputRef} type="file" multiple accept="image/*" className="hidden" onChange={(e) => handleFileUpload(e.target.files)} />
              <button onClick={() => fileInputRef.current?.click()} className="btn-secondary" disabled={uploadImagesMutation.isPending}>
                {uploadImagesMutation.isPending ? 'Uploading...' : 'Upload Images'}
              </button>
            </div>
          </div>
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className="border-2 border-dashed border-zinc-600 rounded-xl p-8 text-center hover:border-zinc-500 transition-colors"
          >
            <p className="text-zinc-400 mb-2">Drag and drop images here, or click Upload</p>
            <p className="text-xs text-zinc-500">Supports JPG, PNG, WebP up to 10MB each</p>
          </div>
          {product.images && product.images.length > 0 ? (
            <div className="grid grid-cols-4 gap-4">
              {product.images.map((img: any) => (
                <div key={img.id} className="aspect-square bg-zinc-700 rounded-lg overflow-hidden relative group">
                  <img src={img.image_url} alt={img.image_type} className="w-full h-full object-cover" />
                  <div className="absolute bottom-0 inset-x-0 bg-black/60 px-2 py-1 text-xs text-zinc-300 flex items-center justify-between">
                    <span>{img.image_type}</span>
                    <span>#{img.position}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-zinc-400">No images uploaded yet</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'enrichment' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-zinc-100">Product Enrichment</h3>
            <button onClick={() => enrichMutation.mutate()} className="btn-secondary" disabled={enrichMutation.isPending}>
              {enrichMutation.isPending ? 'Enriching...' : 'Enrich Product'}
            </button>
          </div>
          {!enrichment ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No enrichment data yet</p>
              <button onClick={() => enrichMutation.mutate()} className="btn-primary" disabled={enrichMutation.isPending}>
                {enrichMutation.isPending ? 'Enriching...' : 'Enrich Product'}
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {enrichment.short_description && (
                <div className="bg-zinc-800 rounded-xl p-6">
                  <h4 className="font-medium text-zinc-200 mb-2">Short Description</h4>
                  <p className="text-sm text-zinc-400">{enrichment.short_description}</p>
                </div>
              )}
              {enrichment.enriched_description && (
                <div className="bg-zinc-800 rounded-xl p-6">
                  <h4 className="font-medium text-zinc-200 mb-2">Enriched Description</h4>
                  <p className="text-sm text-zinc-400 whitespace-pre-wrap">{enrichment.enriched_description}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-6">
                <EnrichmentCard title="Features" items={enrichment.features} color="indigo" />
                <EnrichmentCard title="Benefits" items={enrichment.benefits} color="green" />
                <EnrichmentCard title="Use Cases" items={enrichment.use_cases} color="amber" />
                <EnrichmentCard title="Suggested Audiences" items={enrichment.suggested_audiences} color="teal" />
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'analysis' && (
        <div>
          {!analysis ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No analysis yet</p>
              <button onClick={() => analyzeMutation.mutate()} className="btn-primary" disabled={analyzeMutation.isPending}>
                {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze Product'}
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="bg-zinc-800 rounded-xl p-6">
                <div className="flex items-center gap-6 mb-6">
                  <div className="text-center">
                    <div className="text-4xl font-bold text-indigo-400">{analysis.overall_score}</div>
                    <div className="text-xs text-zinc-400 mt-1">Overall Score</div>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-4">
                  {[
                    { label: 'Demand', value: analysis.demand_score },
                    { label: 'Visual', value: analysis.visual_score },
                    { label: 'Problem', value: analysis.problem_score },
                    { label: 'Margin', value: analysis.margin_score },
                    { label: 'Saturation', value: analysis.saturation_score },
                    { label: 'Ad Potential', value: analysis.ad_potential_score },
                    { label: 'Impulse', value: analysis.impulse_score },
                    { label: 'Return Risk', value: analysis.return_risk_score },
                  ].map((s) => (
                    <div key={s.label} className="text-center p-3 bg-zinc-700/30 rounded-lg">
                      <div className="text-lg font-semibold text-zinc-100">{s.value}</div>
                      <div className="text-xs text-zinc-400">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-zinc-800 rounded-xl p-6">
                <h3 className="font-semibold mb-3 text-zinc-100">Summary</h3>
                <p className="text-sm text-zinc-400">{analysis.summary}</p>
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div className="bg-zinc-800 rounded-xl p-6">
                  <h3 className="font-semibold mb-3 text-green-400">Strengths</h3>
                  <ul className="space-y-2">
                    {analysis.strengths.map((s: string, i: number) => (
                      <li key={i} className="text-sm flex items-start gap-2 text-zinc-300"><span className="text-green-500 mt-0.5">+</span>{s}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-zinc-800 rounded-xl p-6">
                  <h3 className="font-semibold mb-3 text-red-400">Risks</h3>
                  <ul className="space-y-2">
                    {analysis.risks.map((r: string, i: number) => (
                      <li key={i} className="text-sm flex items-start gap-2 text-zinc-300"><span className="text-red-500 mt-0.5">-</span>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
              {analysis.recommended_price_min && (
                <div className="bg-zinc-800 rounded-xl p-6">
                  <h3 className="font-semibold mb-2 text-zinc-100">Recommended Price</h3>
                  <p className="text-sm text-zinc-400">${analysis.recommended_price_min} - ${analysis.recommended_price_max}</p>
                </div>
              )}
            </div>
          )}
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
              {angles.map((angle: any) => (
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

      {activeTab === 'landing' && (
        <div>
          {!landing ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No landing page generated yet</p>
              <button onClick={() => generateLandingMutation.mutate()} className="btn-primary" disabled={generateLandingMutation.isPending || !selectedAngle}>
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
                <Link to={`/products/${id}/landing`} className="btn-primary">Preview Landing</Link>
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

      {activeTab === 'campaigns' && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-zinc-100">Campaigns</h3>
            <Link to={`/campaigns/new`} className="btn-secondary">Create Campaign</Link>
          </div>
          {campaigns.length === 0 ? (
            <div className="bg-zinc-800 rounded-xl p-6 text-center py-12">
              <p className="text-zinc-400 mb-4">No campaigns for this product yet</p>
              <Link to="/campaigns/new" className="btn-primary">Create your first campaign</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {campaigns.map((c: any) => (
                <Link key={c.id} to={`/campaigns/${c.id}`} className="bg-zinc-800 rounded-xl p-6 border border-zinc-700 flex items-center justify-between hover:border-indigo-500 transition-colors">
                  <div>
                    <h4 className="font-medium text-zinc-100">{c.name}</h4>
                    <p className="text-sm text-zinc-400">{c.target_country}</p>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${campaignStatusColors[c.status] || ''}`}>
                    {c.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function EnrichmentCard({ title, items, color }: { title: string; items: string[]; color: string }) {
  const colorMap: Record<string, string> = {
    indigo: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400',
    green: 'bg-green-500/10 border-green-500/20 text-green-400',
    amber: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    teal: 'bg-teal-500/10 border-teal-500/20 text-teal-400',
  }
  const dotColor: Record<string, string> = {
    indigo: 'bg-indigo-400',
    green: 'bg-green-400',
    amber: 'bg-amber-400',
    teal: 'bg-teal-400',
  }
  return (
    <div className={`bg-zinc-800 rounded-xl p-6 border ${colorMap[color]}`}>
      <h4 className={`font-medium mb-3 ${colorMap[color].split(' ').pop()}`}>{title}</h4>
      {items && items.length > 0 ? (
        <ul className="space-y-2">
          {items.map((item: string, i: number) => (
            <li key={i} className="text-sm flex items-start gap-2 text-zinc-300">
              <span className={`w-1.5 h-1.5 rounded-full mt-1.5 ${dotColor[color]} shrink-0`} />
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">No data available</p>
      )}
    </div>
  )
}

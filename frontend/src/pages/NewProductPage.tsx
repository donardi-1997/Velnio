import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'

type Step = 'source' | 'info' | 'market' | 'analyzing' | 'score' | 'angles' | 'generating'

export function NewProductPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [step, setStep] = useState<Step>('source')
  const [sourceType, setSourceType] = useState<'URL' | 'MANUAL'>('MANUAL')
  const [sourceUrl, setSourceUrl] = useState('')
  const [form, setForm] = useState({ name: '', description: '', supplier_price: '', selling_price: '', currency: 'USD' })
  const [market, setMarket] = useState({ country: 'US', language: 'en' })
  const [productId, setProductId] = useState<string | null>(null)
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [anglesData, setAnglesData] = useState<any[]>([])

  const countries = [
    { code: 'US', name: 'United States' },
    { code: 'CO', name: 'Colombia' },
    { code: 'MX', name: 'Mexico' },
    { code: 'ES', name: 'Spain' },
    { code: 'CL', name: 'Chile' },
    { code: 'PE', name: 'Peru' },
  ]

  const createMutation = useMutation({
    mutationFn: (data: any) => api.products.create(data),
    onSuccess: (product) => { setProductId(product.id); setStep('market') },
  })

  const analyzeMutation = useMutation({
    mutationFn: (id: string) => api.products.analyze(id),
    onSuccess: (data) => { setAnalysisData(data); setStep('score') },
    onError: () => setStep('info'),
  })

  const anglesMutation = useMutation({
    mutationFn: (id: string) => api.angles.generate(id),
    onSuccess: (data) => { setAnglesData(data); setStep('angles') },
    onError: () => setStep('score'),
  })

  const selectAngleMutation = useMutation({
    mutationFn: ({ productId, angleId }: { productId: string; angleId: string }) => api.angles.select(productId, angleId),
    onSuccess: () => setStep('generating'),
  })

  const landingMutation = useMutation({
    mutationFn: (id: string) => api.landing.generate(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      navigate(`/products/${id}`)
    },
    onError: () => setStep('angles'),
  })

  const handleCreate = () => {
    createMutation.mutate({
      name: form.name,
      description: form.description || undefined,
      supplier_price: form.supplier_price ? parseFloat(form.supplier_price) : undefined,
      selling_price: form.selling_price ? parseFloat(form.selling_price) : undefined,
      currency: form.currency,
      source_type: sourceType === 'URL' ? 'OTHER' : 'MANUAL',
      source_url: sourceUrl || undefined,
      target_country: market.country,
      target_language: market.language,
    })
  }

  const handleAnalyze = () => {
    if (!productId) return
    setStep('analyzing')
    analyzeMutation.mutate(productId)
  }

  const handleAngles = () => {
    if (!productId) return
    anglesMutation.mutate(productId)
  }

  const handleSelectAngle = (angleId: string) => {
    if (!productId) return
    selectAngleMutation.mutate({ productId, angleId })
  }

  const handleGenerateLanding = () => {
    if (!productId) return
    setStep('generating')
    landingMutation.mutate(productId)
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-8">Launch New Product</h1>

      <div className="flex gap-2 mb-8">
        {['source', 'info', 'market', 'analyzing', 'score', 'angles', 'generating'].map((s, i) => (
          <div key={s} className={`h-1 flex-1 rounded-full ${(['source', 'info', 'market', 'analyzing', 'score', 'angles', 'generating'].indexOf(step) >= i) ? 'bg-[var(--accent)]' : 'bg-[var(--bg-tertiary)]'}`} />
        ))}
      </div>

      {step === 'source' && (
        <div className="card space-y-6">
          <h2 className="text-lg font-semibold">Product Source</h2>
          <div className="grid grid-cols-2 gap-4">
            <button onClick={() => setSourceType('URL')} className={`card text-center ${sourceType === 'URL' ? 'border-[var(--accent)] ring-1 ring-[var(--accent)]' : ''}`}>
              <div className="text-sm font-medium">Product URL</div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">Paste a product link</div>
            </button>
            <button onClick={() => setSourceType('MANUAL')} className={`card text-center ${sourceType === 'MANUAL' ? 'border-[var(--accent)] ring-1 ring-[var(--accent)]' : ''}`}>
              <div className="text-sm font-medium">Manual Entry</div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">Enter details manually</div>
            </button>
          </div>
          {sourceType === 'URL' && (
            <div>
              <label className="block text-sm font-medium mb-1.5">Product URL</label>
              <input className="input" placeholder="https://..." value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} />
            </div>
          )}
          <button onClick={() => setStep('info')} className="btn-primary w-full">Continue</button>
        </div>
      )}

      {step === 'info' && (
        <div className="card space-y-6">
          <h2 className="text-lg font-semibold">Product Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">Product Name *</label>
              <input className="input" value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} required placeholder="e.g. Portable Car Vacuum" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Description</label>
              <textarea className="input" rows={3} value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Brief product description..." />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Supplier Cost ($)</label>
                <input type="number" step="0.01" className="input" value={form.supplier_price} onChange={(e) => setForm(f => ({ ...f, supplier_price: e.target.value }))} placeholder="9.99" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Selling Price ($)</label>
                <input type="number" step="0.01" className="input" value={form.selling_price} onChange={(e) => setForm(f => ({ ...f, selling_price: e.target.value }))} placeholder="29.99" />
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setStep('source')} className="btn-secondary flex-1">Back</button>
            <button onClick={handleCreate} className="btn-primary flex-1" disabled={!form.name || createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Continue'}
            </button>
          </div>
        </div>
      )}

      {step === 'market' && (
        <div className="card space-y-6">
          <h2 className="text-lg font-semibold">Target Market</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">Country</label>
              <select className="input" value={market.country} onChange={(e) => setMarket(m => ({ ...m, country: e.target.value }))}>
                {countries.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Language</label>
              <select className="input" value={market.language} onChange={(e) => setMarket(m => ({ ...m, language: e.target.value }))}>
                <option value="en">English</option>
                <option value="es">Spanish</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setStep('info')} className="btn-secondary flex-1">Back</button>
            <button onClick={handleAnalyze} className="btn-primary flex-1">Analyze Product</button>
          </div>
        </div>
      )}

      {step === 'analyzing' && (
        <div className="card text-center py-12">
          <div className="animate-spin w-8 h-8 border-2 border-[var(--accent)] border-t-transparent rounded-full mx-auto mb-4" />
          <h3 className="font-semibold mb-2">Analyzing product...</h3>
          <p className="text-sm text-[var(--text-secondary)]">Identifying customer pain points and evaluating selling potential...</p>
        </div>
      )}

      {step === 'score' && analysisData && (
        <div className="space-y-6">
          <div className="card">
            <div className="text-center mb-6">
              <div className="text-5xl font-bold text-[var(--accent)]">{analysisData.overall_score}</div>
              <div className="text-sm text-[var(--text-secondary)] mt-1">Overall Score</div>
            </div>
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Demand', value: analysisData.demand_score },
                { label: 'Visual', value: analysisData.visual_score },
                { label: 'Problem', value: analysisData.problem_score },
                { label: 'Margin', value: analysisData.margin_score },
                { label: 'Saturation', value: analysisData.saturation_score },
                { label: 'Ad Potential', value: analysisData.ad_potential_score },
                { label: 'Impulse', value: analysisData.impulse_score },
                { label: 'Return Risk', value: analysisData.return_risk_score },
              ].map(s => (
                <div key={s.label} className="text-center p-2 bg-[var(--bg-secondary)] rounded-lg">
                  <div className="text-sm font-semibold">{s.value}</div>
                  <div className="text-[10px] text-[var(--text-tertiary)]">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <p className="text-sm text-[var(--text-secondary)]">{analysisData.summary}</p>
          </div>
          <button onClick={handleAngles} className="btn-primary w-full">Generate Selling Angles</button>
        </div>
      )}

      {step === 'angles' && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold">Winning Angles</h2>
          <div className="grid grid-cols-3 gap-4">
            {anglesData.map((angle: any) => (
              <div key={angle.id} className="card cursor-pointer hover:border-[var(--accent)] transition-colors" onClick={() => handleSelectAngle(angle.id)}>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-semibold text-sm">{angle.name}</span>
                  <span className="text-sm font-bold text-[var(--accent)]">{angle.score}</span>
                </div>
                <div className="space-y-2 text-xs">
                  <div><span className="text-[var(--text-tertiary)]">Audience: </span>{angle.target_audience}</div>
                  <div><span className="text-[var(--text-tertiary)]">Hook: </span><em>"{angle.hook}"</em></div>
                  <div><span className="text-[var(--text-tertiary)]">Promise: </span>{angle.main_promise}</div>
                </div>
              </div>
            ))}
          </div>
          <p className="text-sm text-[var(--text-secondary)] text-center">Click an angle to select it</p>
        </div>
      )}

      {step === 'generating' && (
        <div className="card text-center py-12">
          <div className="animate-spin w-8 h-8 border-2 border-[var(--accent)] border-t-transparent rounded-full mx-auto mb-4" />
          <h3 className="font-semibold mb-2">Generating landing page...</h3>
          <p className="text-sm text-[var(--text-secondary)]">Writing conversion copy and building your offer...</p>
        </div>
      )}
    </div>
  )
}

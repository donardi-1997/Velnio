import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useState } from 'react'

function HeroSection({ content }: { content: any }) {
  return (
    <section className="bg-[var(--bg-secondary)] py-20 text-center">
      <div className="max-w-3xl mx-auto px-8">
        <h1 className="text-4xl font-bold tracking-tight mb-4">{content.headline}</h1>
        <p className="text-lg text-[var(--text-secondary)] mb-8">{content.subheadline}</p>
        <button className="btn-primary text-base px-8 py-3">{content.cta_text}</button>
      </div>
    </section>
  )
}

function ProblemSection({ content }: { content: any }) {
  return (
    <section className="py-16 max-w-3xl mx-auto px-8">
      <h2 className="text-2xl font-bold mb-4">{content.title}</h2>
      <p className="text-[var(--text-secondary)] mb-6">{content.description}</p>
      {content.items && (
        <ul className="space-y-3">
          {content.items.map((item: string, i: number) => (
            <li key={i} className="flex items-start gap-3 text-sm">
              <span className="text-red-500 mt-0.5">x</span>
              <span className="text-[var(--text-secondary)]">{item}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function BenefitsSection({ content }: { content: any }) {
  return (
    <section className="py-16 bg-[var(--bg-secondary)]">
      <div className="max-w-3xl mx-auto px-8">
        <h2 className="text-2xl font-bold mb-8 text-center">{content.title}</h2>
        <div className="grid grid-cols-3 gap-6">
          {content.items?.map((item: any, i: number) => (
            <div key={i} className="text-center">
              <div className="w-10 h-10 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center mx-auto mb-3">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="font-semibold text-sm mb-1">{item.title}</h3>
              <p className="text-xs text-[var(--text-secondary)]">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function OfferSection({ content }: { content: any }) {
  return (
    <section className="py-16 max-w-3xl mx-auto px-8">
      <div className="card text-center">
        <h2 className="text-2xl font-bold mb-6">{content.title}</h2>
        <div className="flex items-center justify-center gap-4 mb-4">
          {content.original_price && <span className="text-lg text-[var(--text-tertiary)] line-through">${content.original_price}</span>}
          {content.discount_price && <span className="text-3xl font-bold text-[var(--accent)]">${content.discount_price}</span>}
        </div>
        {content.savings && <p className="text-sm text-green-600 mb-2">Save ${content.savings}</p>}
        {content.bonus && <p className="text-sm text-[var(--text-secondary)] mb-4">{content.bonus}</p>}
        {content.urgency && <p className="text-xs text-[var(--text-tertiary)] mb-4">{content.urgency}</p>}
        <button className="btn-primary px-8 py-3">Order Now</button>
      </div>
    </section>
  )
}

function FaqSection({ content }: { content: any }) {
  return (
    <section className="py-16 max-w-3xl mx-auto px-8">
      <h2 className="text-2xl font-bold mb-8 text-center">{content.title}</h2>
      <div className="space-y-4">
        {content.items?.map((item: any, i: number) => (
          <div key={i} className="card">
            <h3 className="font-semibold text-sm mb-2">{item.question}</h3>
            <p className="text-sm text-[var(--text-secondary)]">{item.answer}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function GenericSection({ content, type }: { content: any; type: string }) {
  return (
    <section className="py-12 max-w-3xl mx-auto px-8">
      <div className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-2">{type}</div>
      <pre className="text-xs text-[var(--text-secondary)] overflow-auto bg-[var(--bg-secondary)] p-4 rounded-lg">{JSON.stringify(content, null, 2)}</pre>
    </section>
  )
}

const sectionComponents: Record<string, React.ComponentType<any>> = {
  HERO: HeroSection,
  PROBLEM: ProblemSection,
  BENEFITS: BenefitsSection,
  OFFER: OfferSection,
  FAQ: FaqSection,
}

export function LandingPreviewPage() {
  const { id } = useParams<{ id: string }>()!
  const [viewMode, setViewMode] = useState<'desktop' | 'mobile'>('desktop')
  const { data: landing, isLoading } = useQuery({ queryKey: ['landing', id], queryFn: () => api.landing.get(id!) })

  if (isLoading) return <div className="text-center py-12">Loading...</div>
  if (!landing) return <div className="text-center py-12">No landing page found</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link to={`/products/${id}`} className="text-sm text-[var(--text-secondary)] hover:text-[var(--accent)] mb-2 block">&larr; Back to product</Link>
          <h1 className="text-xl font-bold">Landing Preview</h1>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setViewMode('desktop')} className={`px-3 py-1.5 rounded-lg text-sm ${viewMode === 'desktop' ? 'bg-[var(--accent)] text-white' : 'btn-ghost'}`}>Desktop</button>
          <button onClick={() => setViewMode('mobile')} className={`px-3 py-1.5 rounded-lg text-sm ${viewMode === 'mobile' ? 'bg-[var(--accent)] text-white' : 'btn-ghost'}`}>Mobile</button>
        </div>
      </div>
      <div className={`mx-auto border border-[var(--border-color)] rounded-xl overflow-hidden bg-white ${viewMode === 'mobile' ? 'max-w-sm' : 'max-w-4xl'}`}>
        {landing.sections
          .sort((a: any, b: any) => a.position - b.position)
          .map((section: any) => {
            const Component = sectionComponents[section.section_type]
            if (Component) return <Component key={section.id} content={section.content} />
            return <GenericSection key={section.id} content={section.content} type={section.section_type} />
          })}
      </div>
    </div>
  )
}

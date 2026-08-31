import { Link } from 'react-router-dom'

const steps = [
  { step: '1', title: 'Add your product', desc: 'Paste a URL or enter details manually.' },
  { step: '2', title: 'Analyze the opportunity', desc: 'AI-powered scoring across 8 dimensions.' },
  { step: '3', title: 'Discover selling angles', desc: 'Find the best way to position your product.' },
  { step: '4', title: 'Build your campaign', desc: 'Generate a complete landing page.' },
  { step: '5', title: 'Publish to Shopify', desc: 'One click to go live.' },
]

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <nav className="flex items-center justify-between px-8 py-5 border-b border-[var(--border-color)]">
        <div className="text-xl font-bold"><span className="text-[var(--accent)]">V</span>elnio</div>
        <div className="flex items-center gap-4">
          <Link to="/login" className="btn-ghost">Log in</Link>
          <Link to="/register" className="btn-primary">Start for free</Link>
        </div>
      </nav>

      <section className="max-w-4xl mx-auto text-center px-8 py-24">
        <h1 className="text-5xl font-bold tracking-tight mb-6">
          Turn products into winning campaigns.
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-8 max-w-2xl mx-auto">
          Velnio analyzes your product, finds powerful selling angles, and builds a Shopify-ready landing page using AI.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link to="/register" className="btn-primary text-base px-6 py-3">Start for free</Link>
          <a href="#how-it-works" className="btn-secondary text-base px-6 py-3">See how it works</a>
        </div>
      </section>

      <section id="how-it-works" className="max-w-5xl mx-auto px-8 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">How it works</h2>
        <div className="grid grid-cols-5 gap-8">
          {steps.map((s) => (
            <div key={s.step} className="text-center">
              <div className="w-10 h-10 rounded-full bg-[var(--accent)] text-white flex items-center justify-center mx-auto mb-4 text-sm font-bold">
                {s.step}
              </div>
              <h3 className="font-semibold text-sm mb-2">{s.title}</h3>
              <p className="text-xs text-[var(--text-secondary)]">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-8 py-20">
        <h2 className="text-3xl font-bold text-center mb-4">Product Score</h2>
        <p className="text-center text-[var(--text-secondary)] mb-12 max-w-xl mx-auto">
          Every product is analyzed across 8 dimensions to give you a clear score before you invest in ads.
        </p>
        <div className="grid grid-cols-4 gap-6">
          {['Demand', 'Visual Appeal', 'Margin Potential', 'Ad Performance'].map((label) => (
            <div key={label} className="card text-center">
              <div className="text-3xl font-bold text-[var(--accent)] mb-2">{Math.floor(Math.random() * 20) + 80}</div>
              <div className="text-sm text-[var(--text-secondary)]">{label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-8 py-20">
        <h2 className="text-3xl font-bold text-center mb-4">Winning Angles</h2>
        <p className="text-center text-[var(--text-secondary)] mb-12 max-w-xl mx-auto">
          Discover the most effective way to position your product for different audiences.
        </p>
        <div className="grid grid-cols-3 gap-6">
          {[
            { audience: 'Pet Owners', hook: 'Your pet loves the car. The hair doesn\'t have to stay.', score: 92 },
            { audience: 'Parents', hook: 'Kids will be kids. Your car doesn\'t have to show it.', score: 86 },
            { audience: 'Rideshare Drivers', hook: 'Every ride is a new passenger. Keep your rating up.', score: 81 },
          ].map((a) => (
            <div key={a.audience} className="card">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium">{a.audience}</span>
                <span className="text-sm font-bold text-[var(--accent)]">{a.score}</span>
              </div>
              <p className="text-sm text-[var(--text-secondary)] italic">"{a.hook}"</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-8 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">Pricing</h2>
        <div className="grid grid-cols-4 gap-6">
          {[
            { name: 'Free', price: '$0', credits: '10 credits' },
            { name: 'Launch', price: '$19/mo', credits: '100 credits' },
            { name: 'Growth', price: '$49/mo', credits: '400 credits' },
            { name: 'Scale', price: '$99/mo', credits: '1,200 credits' },
          ].map((p) => (
            <div key={p.name} className={`card text-center ${p.name === 'Growth' ? 'border-[var(--accent)]' : ''}`}>
              <h3 className="font-semibold mb-2">{p.name}</h3>
              <div className="text-2xl font-bold mb-2">{p.price}</div>
              <p className="text-sm text-[var(--text-secondary)]">{p.credits}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-3xl mx-auto px-8 py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to launch?</h2>
        <p className="text-[var(--text-secondary)] mb-8">Start analyzing products and building campaigns today.</p>
        <Link to="/register" className="btn-primary text-base px-8 py-3">Start for free</Link>
      </section>

      <footer className="border-t border-[var(--border-color)] py-8 text-center text-sm text-[var(--text-tertiary)]">
        Velnio. Turn products into winning campaigns.
      </footer>
    </div>
  )
}

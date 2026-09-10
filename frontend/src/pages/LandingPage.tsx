import { Link } from 'react-router-dom'

const benefits = [
  {
    title: 'Valida antes de gastar en anuncios',
    description: 'Analiza demanda, margen, potencial visual, saturación y riesgo antes de comprometer presupuesto.',
    icon: '01',
  },
  {
    title: 'Encuentra el ángulo que vende',
    description: 'Convierte información del producto en audiencias, hooks y propuestas de valor listas para probar.',
    icon: '02',
  },
  {
    title: 'Crea la oferta y la landing',
    description: 'Pasa del producto a una estructura de venta coherente sin saltar entre documentos y herramientas.',
    icon: '03',
  },
  {
    title: 'Publica y aprende más rápido',
    description: 'Lleva la campaña a Shopify, prueba variantes y usa performance real para decidir qué escalar.',
    icon: '04',
  },
]

const workflow = [
  ['Producto', 'Agrega el producto y su contexto comercial.'],
  ['Análisis', 'Velnio identifica fortalezas, riesgos y oportunidad.'],
  ['Campaña', 'Genera ángulos, oferta, brief y estructura de venta.'],
  ['Landing', 'Construye una página enfocada en conversión.'],
  ['Publicación', 'Lleva la campaña a Shopify y mide resultados.'],
]

const plans = [
  {
    name: 'Starter',
    price: '29',
    description: 'Para empezar a lanzar con un proceso serio.',
    features: ['1 tienda', '100 créditos al mes', 'Hasta 10 productos al mes', 'Análisis, ángulos, ofertas y landings'],
    cta: 'Empezar con Starter',
  },
  {
    name: 'Growth',
    price: '79',
    description: 'Para operadores que prueban productos todas las semanas.',
    features: ['Hasta 3 tiendas', '400 créditos al mes', 'Hasta 30 productos al mes', 'Briefs, variantes y performance insights'],
    cta: 'Elegir Growth',
    featured: true,
  },
  {
    name: 'Scale',
    price: '149',
    description: 'Para equipos que necesitan más volumen y control.',
    features: ['Hasta 10 tiendas', '1.200 créditos al mes', 'Hasta 100 productos al mes', 'Más capacidad para experimentar y escalar'],
    cta: 'Escalar con Velnio',
  },
]

const faqs = [
  ['¿Velnio reemplaza Shopify?', 'No. Velnio organiza y acelera el proceso de crear campañas y páginas para tu tienda Shopify.'],
  ['¿Necesito saber copywriting?', 'No. Velnio genera una base estratégica y comercial para que puedas editar, aprobar y lanzar más rápido.'],
  ['¿Puedo modificar lo que genera la IA?', 'Sí. La idea es que la IA acelere el trabajo, no que te quite control sobre la campaña.'],
  ['¿Sirve si apenas estoy empezando?', 'Sí. Velnio te da un proceso claro para evitar lanzar productos sin análisis, oferta o posicionamiento.'],
  ['¿Puedo usar varias tiendas?', 'Sí. Growth y Scale están pensados para operar varias tiendas desde el mismo workspace.'],
]

function Check() {
  return (
    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600">
      <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2">
        <path d="m5 10 3 3 7-7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  )
}

function Arrow() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 10h12M11 5l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ProductMockup() {
  return (
    <div className="relative mx-auto max-w-5xl">
      <div className="absolute -inset-10 -z-10 rounded-[3rem] bg-gradient-to-r from-indigo-500/15 via-violet-500/10 to-cyan-400/15 blur-3xl" />
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_30px_90px_-35px_rgba(15,23,42,0.45)]">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
          </div>
          <div className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-medium text-slate-500 sm:text-xs">Campaign workspace</div>
          <div className="w-10" />
        </div>

        <div className="grid min-h-[440px] grid-cols-1 lg:grid-cols-[190px_1fr]">
          <aside className="hidden border-r border-slate-200 bg-slate-50/80 p-5 lg:block">
            <div className="mb-8 text-lg font-black tracking-tight text-slate-950"><span className="text-indigo-600">V</span>elnio</div>
            <div className="space-y-2 text-xs font-medium text-slate-500">
              <div className="rounded-lg bg-indigo-600 px-3 py-2.5 text-white">Campaigns</div>
              <div className="px-3 py-2.5">Products</div>
              <div className="px-3 py-2.5">Analytics</div>
              <div className="px-3 py-2.5">Stores</div>
            </div>
          </aside>

          <div className="p-4 sm:p-6 lg:p-8">
            <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-indigo-600">Campaign</div>
                <h3 className="text-xl font-bold text-slate-950 sm:text-2xl">Portable Car Vacuum</h3>
              </div>
              <div className="inline-flex w-fit items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Ready to launch
              </div>
            </div>

            <div className="mb-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs text-slate-500">Product score</div>
                <div className="mt-1 flex items-end gap-2"><span className="text-3xl font-black text-slate-950">91</span><span className="mb-1 text-xs font-medium text-emerald-600">Strong</span></div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs text-slate-500">Margin potential</div>
                <div className="mt-1 text-2xl font-black text-slate-950">62.8%</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs text-slate-500">Launch status</div>
                <div className="mt-2 text-sm font-bold text-indigo-600">4 / 5 complete</div>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1.15fr_.85fr]">
              <div className="rounded-xl border border-slate-200 p-4 sm:p-5">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500">Selected selling angle</div>
                    <div className="mt-1 font-bold text-slate-950">A clean car in 60 seconds</div>
                  </div>
                  <span className="rounded-md bg-indigo-50 px-2 py-1 text-[10px] font-bold text-indigo-600">92/100</span>
                </div>
                <div className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                  “Crumbs, pet hair and dust disappear before your next passenger gets in.”
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {['Pain-aware', 'Car owners', 'Convenience'].map((tag) => (
                    <span key={tag} className="rounded-full border border-slate-200 px-2.5 py-1 text-[10px] font-medium text-slate-500">{tag}</span>
                  ))}
                </div>
              </div>

              <div className="rounded-xl bg-slate-950 p-5 text-white">
                <div className="text-xs font-medium text-slate-400">Offer</div>
                <div className="mt-2 text-xl font-black">Buy 2, save 20%</div>
                <p className="mt-2 text-xs leading-5 text-slate-400">Landing copy, benefits and CTA aligned with the selected angle.</p>
                <div className="mt-5 space-y-2">
                  {['Hero section', 'Benefits', 'Objections', 'Final CTA'].map((item, index) => (
                    <div key={item} className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-xs">
                      <span>{item}</span>
                      <span className={index < 3 ? 'text-emerald-400' : 'text-amber-300'}>{index < 3 ? 'Ready' : 'Review'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function LandingPage() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-white text-slate-950">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
          <a href="#top" className="text-xl font-black tracking-tight"><span className="text-indigo-600">V</span>elnio</a>
          <nav className="hidden items-center gap-7 text-sm font-medium text-slate-600 md:flex">
            <a href="#producto" className="transition hover:text-slate-950">Producto</a>
            <a href="#como-funciona" className="transition hover:text-slate-950">Cómo funciona</a>
            <a href="#precios" className="transition hover:text-slate-950">Precios</a>
            <a href="#faq" className="transition hover:text-slate-950">FAQ</a>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link to="/login" className="hidden rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:text-slate-950 sm:inline-flex">Ingresar</Link>
            <Link to="/register" className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-600">
              Empezar gratis <span className="hidden sm:inline"><Arrow /></span>
            </Link>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="relative isolate px-5 pb-20 pt-20 sm:px-8 sm:pt-28 lg:pb-28">
          <div className="absolute left-1/2 top-10 -z-10 h-[460px] w-[720px] -translate-x-1/2 rounded-full bg-indigo-100/70 blur-[110px]" />
          <div className="mx-auto max-w-5xl text-center">
            <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" /> De producto a campaña en un solo flujo
            </div>
            <h1 className="mx-auto max-w-4xl text-4xl font-black tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-7xl">
              Lanza campañas para Shopify <span className="text-indigo-600">en horas, no en días.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
              Velnio analiza tu producto, encuentra ángulos de venta, construye la oferta y prepara una landing lista para convertir. Menos improvisación. Más campañas puestas a prueba.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link to="/register" className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-700 sm:w-auto">
                Crear mi primera campaña <Arrow />
              </Link>
              <a href="#producto" className="inline-flex w-full items-center justify-center rounded-xl border border-slate-300 bg-white px-6 py-3.5 text-sm font-bold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 sm:w-auto">
                Ver cómo funciona
              </a>
            </div>
            <div className="mt-5 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-1.5"><Check /> Empieza gratis</span>
              <span className="flex items-center gap-1.5"><Check /> Sin instalar software</span>
              <span className="flex items-center gap-1.5"><Check /> Diseñado para Shopify</span>
            </div>
          </div>

          <div id="producto" className="mx-auto mt-16 max-w-7xl sm:mt-20">
            <ProductMockup />
          </div>
        </section>

        <section className="border-y border-slate-200 bg-slate-50 px-5 py-8 sm:px-8">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-3 gap-y-3 text-xs font-bold uppercase tracking-[0.12em] text-slate-500 sm:text-sm">
            {workflow.map(([name], index) => (
              <div key={name} className="flex items-center gap-3">
                <span className={index === 2 ? 'text-indigo-600' : ''}>{name}</span>
                {index < workflow.length - 1 && <span className="text-slate-300">→</span>}
              </div>
            ))}
          </div>
        </section>

        <section className="px-5 py-24 sm:px-8 lg:py-32">
          <div className="mx-auto max-w-7xl">
            <div className="grid gap-12 lg:grid-cols-[.85fr_1.15fr] lg:items-end">
              <div>
                <p className="mb-3 text-xs font-black uppercase tracking-[0.18em] text-indigo-600">El problema</p>
                <h2 className="text-3xl font-black tracking-[-0.03em] sm:text-5xl">Una campaña no debería vivir en seis herramientas distintas.</h2>
              </div>
              <p className="max-w-2xl text-base leading-7 text-slate-600 lg:justify-self-end lg:text-lg">
                Research en una pestaña, ideas en otra, copy en un documento y la landing por separado. Cada cambio rompe el contexto. Velnio mantiene producto, ángulo, oferta, landing y performance dentro de la misma campaña.
              </p>
            </div>

            <div className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {benefits.map((item) => (
                <article key={item.title} className="group rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-slate-200/50">
                  <div className="mb-8 text-xs font-black tracking-[0.15em] text-indigo-600">{item.icon}</div>
                  <h3 className="text-lg font-bold tracking-tight">{item.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{item.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="como-funciona" className="bg-slate-950 px-5 py-24 text-white sm:px-8 lg:py-32">
          <div className="mx-auto max-w-7xl">
            <div className="max-w-2xl">
              <p className="mb-3 text-xs font-black uppercase tracking-[0.18em] text-indigo-400">Cómo funciona</p>
              <h2 className="text-3xl font-black tracking-[-0.03em] sm:text-5xl">Un proceso repetible para lanzar mejor.</h2>
              <p className="mt-5 text-base leading-7 text-slate-400">No necesitas pedirle a una IA cinco cosas aisladas. Velnio conserva el contexto y lo convierte en una campaña completa.</p>
            </div>

            <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 md:grid-cols-5">
              {workflow.map(([title, description], index) => (
                <div key={title} className="bg-slate-950 p-6 lg:p-7">
                  <div className="mb-8 flex h-8 w-8 items-center justify-center rounded-full border border-indigo-400/40 bg-indigo-400/10 text-xs font-black text-indigo-300">{index + 1}</div>
                  <h3 className="font-bold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="px-5 py-24 sm:px-8 lg:py-32">
          <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-7 sm:p-10">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Sin un sistema</p>
              <h3 className="mt-3 text-2xl font-black tracking-tight">Lanzas por intuición y reconstruyes el contexto cada vez.</h3>
              <div className="mt-8 space-y-4 text-sm text-slate-600">
                {['Analizar el producto manualmente', 'Inventar hooks desde cero', 'Copiar información entre herramientas', 'Construir la landing sin una estrategia común', 'No saber qué parte de la campaña mejorar'].map((item) => (
                  <div key={item} className="flex gap-3"><span className="text-slate-300">×</span><span>{item}</span></div>
                ))}
              </div>
            </div>
            <div className="relative overflow-hidden rounded-3xl bg-indigo-600 p-7 text-white sm:p-10">
              <div className="absolute -right-20 -top-20 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
              <p className="text-xs font-black uppercase tracking-[0.16em] text-indigo-200">Con Velnio</p>
              <h3 className="mt-3 text-2xl font-black tracking-tight">Cada decisión alimenta la siguiente parte de la campaña.</h3>
              <div className="mt-8 space-y-4 text-sm text-indigo-50">
                {['Score y diagnóstico antes de invertir', 'Ángulos ligados a audiencias y dolores', 'Oferta construida desde el ángulo elegido', 'Landing alineada con producto + oferta + contexto', 'Performance organizada para iterar con datos'].map((item) => (
                  <div key={item} className="flex gap-3"><Check /><span>{item}</span></div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="precios" className="border-y border-slate-200 bg-slate-50 px-5 py-24 sm:px-8 lg:py-32">
          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-2xl text-center">
              <p className="mb-3 text-xs font-black uppercase tracking-[0.18em] text-indigo-600">Precios</p>
              <h2 className="text-3xl font-black tracking-[-0.03em] sm:text-5xl">Empieza pequeño. Escala cuando tu operación lo pida.</h2>
              <p className="mt-5 text-base leading-7 text-slate-600">Tres planes claros para operadores que necesitan pasar de idea a campaña con menos fricción.</p>
            </div>

            <div className="mt-14 grid gap-5 lg:grid-cols-3 lg:items-stretch">
              {plans.map((plan) => (
                <article key={plan.name} className={`relative flex flex-col rounded-3xl p-7 sm:p-8 ${plan.featured ? 'bg-slate-950 text-white shadow-2xl shadow-slate-300' : 'border border-slate-200 bg-white'}`}>
                  {plan.featured && <div className="absolute right-6 top-6 rounded-full bg-indigo-500 px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-white">Más popular</div>}
                  <h3 className="text-lg font-black">{plan.name}</h3>
                  <p className={`mt-2 min-h-12 text-sm leading-6 ${plan.featured ? 'text-slate-400' : 'text-slate-600'}`}>{plan.description}</p>
                  <div className="mt-6 flex items-end gap-1">
                    <span className="text-sm font-bold">US$</span>
                    <span className="text-5xl font-black tracking-[-0.05em]">{plan.price}</span>
                    <span className={`mb-1 text-sm ${plan.featured ? 'text-slate-400' : 'text-slate-500'}`}>/mes</span>
                  </div>
                  <div className={`my-7 h-px ${plan.featured ? 'bg-white/10' : 'bg-slate-200'}`} />
                  <div className="flex-1 space-y-3.5">
                    {plan.features.map((feature) => (
                      <div key={feature} className={`flex gap-3 text-sm ${plan.featured ? 'text-slate-300' : 'text-slate-600'}`}><Check /><span>{feature}</span></div>
                    ))}
                  </div>
                  <Link to="/register" className={`mt-8 inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-bold transition ${plan.featured ? 'bg-indigo-500 text-white hover:bg-indigo-400' : 'bg-slate-950 text-white hover:bg-indigo-600'}`}>
                    {plan.cta} <Arrow />
                  </Link>
                </article>
              ))}
            </div>
            <p className="mt-5 text-center text-xs text-slate-500">Puedes crear tu cuenta gratis y probar el flujo antes de elegir un plan pago.</p>
          </div>
        </section>

        <section id="faq" className="px-5 py-24 sm:px-8 lg:py-32">
          <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[.7fr_1.3fr]">
            <div>
              <p className="mb-3 text-xs font-black uppercase tracking-[0.18em] text-indigo-600">Preguntas frecuentes</p>
              <h2 className="text-3xl font-black tracking-[-0.03em] sm:text-4xl">Lo que necesitas saber antes de lanzar.</h2>
            </div>
            <div className="divide-y divide-slate-200 border-y border-slate-200">
              {faqs.map(([question, answer]) => (
                <details key={question} className="group py-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-bold text-slate-900">
                    {question}
                    <span className="text-xl font-light text-slate-400 transition group-open:rotate-45">+</span>
                  </summary>
                  <p className="max-w-2xl pt-3 text-sm leading-6 text-slate-600">{answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="px-5 pb-24 sm:px-8 lg:pb-32">
          <div className="relative mx-auto max-w-7xl overflow-hidden rounded-3xl bg-slate-950 px-6 py-14 text-center text-white sm:px-12 sm:py-20">
            <div className="absolute left-1/2 top-0 h-64 w-96 -translate-x-1/2 rounded-full bg-indigo-600/30 blur-3xl" />
            <div className="relative mx-auto max-w-3xl">
              <p className="mb-4 text-xs font-black uppercase tracking-[0.18em] text-indigo-300">Tu próxima campaña</p>
              <h2 className="text-3xl font-black tracking-[-0.04em] sm:text-5xl">Deja de empezar desde cero cada vez que encuentras un producto.</h2>
              <p className="mx-auto mt-5 max-w-xl text-sm leading-6 text-slate-400 sm:text-base">Convierte tu proceso de lanzamiento en un sistema que puedas repetir, medir y mejorar.</p>
              <Link to="/register" className="mt-8 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-6 py-3.5 text-sm font-bold text-white transition hover:bg-indigo-400">
                Crear mi cuenta <Arrow />
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-sm text-slate-500 sm:flex-row">
          <div className="font-bold text-slate-900"><span className="text-indigo-600">V</span>elnio</div>
          <div>Producto → campaña → landing → aprendizaje.</div>
          <div className="flex gap-5"><Link to="/login" className="hover:text-slate-900">Ingresar</Link><Link to="/register" className="hover:text-slate-900">Crear cuenta</Link></div>
        </div>
      </footer>
    </div>
  )
}

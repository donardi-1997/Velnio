import { Link } from 'react-router-dom'
import { useOnboarding } from '../hooks/useOnboarding'

function StepStatus({ complete, index }: { complete: boolean; index: number }) {
  if (complete) {
    return (
      <div className="w-9 h-9 rounded-full bg-green-500/15 text-green-500 flex items-center justify-center font-semibold shrink-0">
        ✓
      </div>
    )
  }

  return (
    <div className="w-9 h-9 rounded-full bg-[var(--bg-tertiary)] text-[var(--text-secondary)] flex items-center justify-center font-semibold shrink-0">
      {index + 1}
    </div>
  )
}

export function OnboardingPage() {
  const onboarding = useOnboarding()

  if (onboarding.isLoading) {
    return <div className="text-center py-16 text-[var(--text-secondary)]">Loading your setup...</div>
  }

  if (onboarding.isError) {
    return (
      <div className="card text-center py-12">
        <h1 className="text-xl font-semibold mb-2">We could not load your setup progress</h1>
        <p className="text-sm text-[var(--text-secondary)]">Refresh the page and try again.</p>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--accent)]">Getting started</span>
            <h1 className="text-3xl font-bold mt-2 mb-3">
              {onboarding.isComplete ? 'Your launch workspace is ready' : 'Launch your first campaign with Velnio'}
            </h1>
            <p className="text-[var(--text-secondary)] max-w-2xl">
              {onboarding.isComplete
                ? 'You completed the core launch workflow. You can now repeat it for new products and campaigns.'
                : 'Follow the steps below. Progress is calculated from the real data in your workspace, so it stays up to date automatically.'}
            </p>
          </div>
          {!onboarding.isComplete && onboarding.nextStep && (
            <Link to={onboarding.nextStep.path} className="btn-primary shrink-0">
              Continue: {onboarding.nextStep.cta}
            </Link>
          )}
        </div>

        <div className="mt-6 card">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium">Launch progress</span>
            <span className="text-sm text-[var(--text-secondary)]">{onboarding.progress}%</span>
          </div>
          <div className="h-2.5 rounded-full bg-[var(--bg-tertiary)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all"
              style={{ width: `${onboarding.progress}%` }}
            />
          </div>
          <p className="text-xs text-[var(--text-tertiary)] mt-3">
            {onboarding.completed} of {onboarding.total} milestones complete
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {onboarding.steps.map((step, index) => {
          const isNext = onboarding.nextStep?.id === step.id
          return (
            <div
              key={step.id}
              className={`card flex flex-col gap-4 sm:flex-row sm:items-center ${isNext ? 'ring-1 ring-[var(--accent)]' : ''}`}
            >
              <StepStatus complete={step.complete} index={index} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="font-semibold">{step.title}</h2>
                  {step.complete && <span className="text-xs text-green-500 font-medium">Complete</span>}
                  {isNext && <span className="text-xs text-[var(--accent)] font-medium">Next</span>}
                </div>
                <p className="text-sm text-[var(--text-secondary)]">{step.description}</p>
              </div>
              <Link to={step.path} className={isNext ? 'btn-primary shrink-0' : 'btn-ghost shrink-0'}>
                {step.cta}
              </Link>
            </div>
          )
        })}
      </div>

      {onboarding.isComplete && (
        <div className="card mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold mb-1">Ready for the next launch</h2>
            <p className="text-sm text-[var(--text-secondary)]">Add another product or start a new campaign from an existing one.</p>
          </div>
          <div className="flex gap-2">
            <Link to="/products/new" className="btn-ghost">Add product</Link>
            <Link to="/campaigns/new" className="btn-primary">New campaign</Link>
          </div>
        </div>
      )}
    </div>
  )
}

import { Link } from 'react-router-dom'
import { useOnboarding } from '../hooks/useOnboarding'

export function OnboardingProgressCard() {
  const onboarding = useOnboarding()

  if (onboarding.isLoading || onboarding.isError || onboarding.isComplete) {
    return null
  }

  return (
    <div className="card mb-8 overflow-hidden relative">
      <div className="absolute inset-y-0 left-0 w-1 bg-[var(--accent)]" />
      <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between pl-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-[var(--accent)]">Getting started</span>
            <span className="text-xs text-[var(--text-tertiary)]">{onboarding.completed}/{onboarding.total} complete</span>
          </div>
          <h2 className="text-lg font-semibold mb-1">Launch your first Velnio campaign</h2>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            {onboarding.nextStep?.title}: {onboarding.nextStep?.description}
          </p>
          <div className="h-2 rounded-full bg-[var(--bg-tertiary)] overflow-hidden max-w-xl">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all"
              style={{ width: `${onboarding.progress}%` }}
            />
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <Link to="/onboarding" className="btn-ghost">View checklist</Link>
          {onboarding.nextStep && (
            <Link to={onboarding.nextStep.path} className="btn-primary">
              {onboarding.nextStep.cta}
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

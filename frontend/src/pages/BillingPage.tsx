import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { api } from '../lib/api'
import { billingApi } from '../lib/billing'

const statusLabel: Record<string, string> = {
  ACTIVE: 'Active',
  TRIALING: 'Trial',
  PAST_DUE: 'Payment due',
  CANCELED: 'Canceled',
}

function formatDate(value?: string | null) {
  if (!value) return null
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

export function BillingPage() {
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const checkoutState = searchParams.get('checkout')

  const { data: plans = [], isLoading: plansLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: api.billing.plans,
  })
  const { data: subscription, isLoading: subscriptionLoading } = useQuery({
    queryKey: ['subscription'],
    queryFn: api.billing.subscription,
  })
  const { data: entitlements } = useQuery({
    queryKey: ['billing-entitlements'],
    queryFn: billingApi.entitlements,
  })

  const checkout = useMutation({
    mutationFn: billingApi.checkout,
    onSuccess: ({ url }) => window.location.assign(url),
  })
  const portal = useMutation({
    mutationFn: billingApi.portal,
    onSuccess: ({ url }) => window.location.assign(url),
  })

  const paidPlans = [...plans]
    .filter((plan: any) => plan.monthly_price > 0)
    .sort((a: any, b: any) => a.monthly_price - b.monthly_price)

  const hasPaidSubscription = Boolean(
    subscription?.plan?.monthly_price > 0 &&
      ['ACTIVE', 'TRIALING'].includes(subscription?.status),
  )

  const refreshBilling = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['subscription'] }),
      queryClient.invalidateQueries({ queryKey: ['billing-entitlements'] }),
      queryClient.invalidateQueries({ queryKey: ['credits'] }),
    ])
  }

  if (plansLoading || subscriptionLoading) {
    return <div className="text-sm text-[var(--text-secondary)]">Loading billing…</div>
  }

  return (
    <div className="max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Billing</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          Manage your Velnio plan, usage limits and subscription.
        </p>
      </div>

      {checkoutState === 'success' && (
        <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300">
          Checkout completed. Stripe is confirming your subscription through the secure webhook.
          <button onClick={refreshBilling} className="ml-2 font-semibold underline">
            Refresh status
          </button>
        </div>
      )}
      {checkoutState === 'cancelled' && (
        <div className="mb-6 rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 text-sm text-[var(--text-secondary)]">
          Checkout was cancelled. Your current plan has not changed.
        </div>
      )}

      {subscription && (
        <div className="card mb-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-tertiary)]">
                Current plan
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-xl font-bold">{subscription.plan?.name || 'Free'}</h2>
                <span className="rounded-full bg-[var(--bg-tertiary)] px-3 py-1 text-xs font-semibold">
                  {statusLabel[subscription.status] || subscription.status}
                </span>
              </div>
              <div className="mt-3 space-y-1 text-sm text-[var(--text-secondary)]">
                {subscription.status === 'TRIALING' && subscription.trial_end && (
                  <div>Trial ends {formatDate(subscription.trial_end)}</div>
                )}
                {subscription.current_period_end && subscription.status !== 'TRIALING' && (
                  <div>Current period ends {formatDate(subscription.current_period_end)}</div>
                )}
                {subscription.cancel_at_period_end && (
                  <div className="font-medium text-amber-600">Cancellation scheduled for period end.</div>
                )}
              </div>
            </div>

            {hasPaidSubscription && (
              <button
                className="btn-secondary"
                onClick={() => portal.mutate()}
                disabled={portal.isPending}
              >
                {portal.isPending ? 'Opening…' : 'Manage subscription'}
              </button>
            )}
          </div>
        </div>
      )}

      {entitlements && (
        <div className="mb-10 grid gap-4 sm:grid-cols-3">
          <div className="card">
            <div className="text-sm text-[var(--text-secondary)]">Stores</div>
            <div className="mt-2 text-2xl font-bold">
              {entitlements.stores_used} / {entitlements.max_stores}
            </div>
          </div>
          <div className="card">
            <div className="text-sm text-[var(--text-secondary)]">Products this month</div>
            <div className="mt-2 text-2xl font-bold">
              {entitlements.products_used_this_month} / {entitlements.max_products_per_month}
            </div>
          </div>
          <div className="card">
            <div className="text-sm text-[var(--text-secondary)]">Included credits</div>
            <div className="mt-2 text-2xl font-bold">{entitlements.included_credits}</div>
          </div>
        </div>
      )}

      <div className="mb-5">
        <h2 className="text-xl font-bold">Choose your plan</h2>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Your first paid subscription can include a trial when eligible. Plan changes after activation are handled securely in the billing portal.
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        {paidPlans.map((plan: any) => {
          const isCurrent = subscription?.plan_id === plan.id && hasPaidSubscription
          const isGrowth = plan.code === 'GROWTH'
          return (
            <div
              key={plan.id}
              className={`card relative flex flex-col ${isGrowth ? 'border-[var(--accent)] ring-1 ring-[var(--accent)]' : ''}`}
            >
              {isGrowth && (
                <span className="absolute -top-3 left-5 rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-semibold text-white">
                  Most popular
                </span>
              )}
              <h3 className="text-lg font-bold">{plan.name}</h3>
              <div className="mt-3 text-3xl font-bold">
                ${plan.monthly_price}
                <span className="text-sm font-normal text-[var(--text-tertiary)]">/mo</span>
              </div>
              <div className="mt-5 flex-1 space-y-2 text-sm text-[var(--text-secondary)]">
                <div>{plan.included_credits} credits / month</div>
                <div>{plan.max_stores} store{plan.max_stores > 1 ? 's' : ''}</div>
                <div>{plan.max_products_per_month} products / month</div>
              </div>

              {isCurrent ? (
                <button className="btn-secondary mt-6 w-full" onClick={() => portal.mutate()}>
                  Current plan · Manage
                </button>
              ) : hasPaidSubscription ? (
                <button className="btn-secondary mt-6 w-full" onClick={() => portal.mutate()}>
                  Change in billing portal
                </button>
              ) : (
                <button
                  className="btn-primary mt-6 w-full"
                  onClick={() => checkout.mutate(plan.code)}
                  disabled={checkout.isPending}
                >
                  {checkout.isPending ? 'Opening checkout…' : 'Start plan'}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {(checkout.error || portal.error) && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          {(checkout.error || portal.error)?.message}
        </div>
      )}
    </div>
  )
}

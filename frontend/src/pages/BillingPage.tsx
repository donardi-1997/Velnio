import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function BillingPage() {
  const { data: plans = [] } = useQuery({ queryKey: ['plans'], queryFn: api.billing.plans })
  const { data: subscription } = useQuery({ queryKey: ['subscription'], queryFn: api.billing.subscription })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-8">Billing</h1>
      {subscription && (
        <div className="card mb-8">
          <h2 className="font-semibold mb-4">Current Plan</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-bold">{subscription.plan?.name || 'Unknown'}</div>
              <div className="text-sm text-[var(--text-secondary)]">{subscription.plan?.included_credits} credits/month</div>
            </div>
            <span className="text-sm font-medium px-3 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
              {subscription.status}
            </span>
          </div>
        </div>
      )}
      <h2 className="font-semibold mb-4">Available Plans</h2>
      <div className="grid grid-cols-4 gap-6">
        {plans.map((plan: any) => (
          <div key={plan.id} className={`card text-center ${subscription?.plan_id === plan.id ? 'border-[var(--accent)] ring-1 ring-[var(--accent)]' : ''}`}>
            <h3 className="font-semibold mb-2">{plan.name}</h3>
            <div className="text-2xl font-bold mb-2">${plan.monthly_price}<span className="text-sm font-normal text-[var(--text-tertiary)]">/mo</span></div>
            <div className="space-y-1 text-sm text-[var(--text-secondary)]">
              <div>{plan.included_credits} credits</div>
              <div>{plan.max_stores} store{plan.max_stores > 1 ? 's' : ''}</div>
              <div>{plan.max_products_per_month} products/mo</div>
            </div>
            {subscription?.plan_id === plan.id ? (
              <div className="mt-4 text-sm font-medium text-[var(--accent)]">Current Plan</div>
            ) : (
              <button className="btn-primary w-full mt-4" disabled>Upgrade</button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

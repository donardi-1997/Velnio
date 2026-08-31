import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function CreditsPage() {
  const { data: wallet } = useQuery({ queryKey: ['credits'], queryFn: api.credits.get })
  const { data: transactions = [] } = useQuery({ queryKey: ['credit-transactions'], queryFn: api.credits.transactions })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-8">Credits</h1>
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="card">
          <div className="text-sm text-[var(--text-secondary)] mb-1">Balance</div>
          <div className="text-3xl font-bold">{wallet?.balance ?? 0}</div>
        </div>
        <div className="card">
          <div className="text-sm text-[var(--text-secondary)] mb-1">Lifetime Credits</div>
          <div className="text-3xl font-bold">{wallet?.lifetime_credits ?? 0}</div>
        </div>
        <div className="card">
          <div className="text-sm text-[var(--text-secondary)] mb-1">Operations Cost</div>
          <div className="text-sm mt-2 space-y-1">
            <div className="flex justify-between"><span>Product Analysis</span><span>1 credit</span></div>
            <div className="flex justify-between"><span>Generate Angles</span><span>2 credits</span></div>
            <div className="flex justify-between"><span>Generate Landing</span><span>5 credits</span></div>
          </div>
        </div>
      </div>
      <div className="card">
        <h2 className="font-semibold mb-4">Transaction History</h2>
        {transactions.length === 0 ? (
          <p className="text-sm text-[var(--text-secondary)] py-4 text-center">No transactions yet</p>
        ) : (
          <div className="space-y-2">
            {transactions.map((t: any) => (
              <div key={t.id} className="flex items-center justify-between py-2 border-b border-[var(--border-color)] last:border-0">
                <div>
                  <div className="text-sm font-medium">{t.description}</div>
                  <div className="text-xs text-[var(--text-tertiary)]">{t.transaction_type} &middot; {new Date(t.created_at).toLocaleDateString()}</div>
                </div>
                <span className={`text-sm font-medium ${t.amount > 0 ? 'text-green-600' : 'text-red-500'}`}>
                  {t.amount > 0 ? '+' : ''}{t.amount}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

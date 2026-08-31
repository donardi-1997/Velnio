import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

const statusColors: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  ANALYZING: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  ANALYZED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  READY: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  PUBLISHED: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  FAILED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

export function ProductsPage() {
  const { data: products = [], isLoading } = useQuery({ queryKey: ['products'], queryFn: api.products.list })

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Products</h1>
        <Link to="/products/new" className="btn-primary">New Product</Link>
      </div>
      {isLoading ? (
        <div className="text-center py-12 text-[var(--text-secondary)]">Loading...</div>
      ) : products.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-[var(--text-secondary)] mb-4">No products yet</p>
          <Link to="/products/new" className="btn-primary">Create your first product</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map((p: any) => (
            <Link key={p.id} to={`/products/${p.id}`} className="card flex items-center justify-between hover:border-[var(--accent)] transition-colors">
              <div>
                <h3 className="font-medium">{p.name}</h3>
                <p className="text-sm text-[var(--text-secondary)]">{p.target_country} &middot; {p.source_type}</p>
              </div>
              <div className="flex items-center gap-4">
                {p.selling_price && <span className="text-sm font-medium">${p.selling_price}</span>}
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[p.status] || ''}`}>
                  {p.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

import { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-secondary)]">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="text-2xl font-bold">
            <span className="text-[var(--accent)]">V</span>elnio
          </Link>
          <p className="text-sm text-[var(--text-secondary)] mt-2">Turn products into winning campaigns</p>
        </div>
        {children}
      </div>
    </div>
  )
}

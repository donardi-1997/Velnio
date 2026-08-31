import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useLogin } from '../hooks/useAuth'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useLogin()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    login.mutate({ email, password })
  }

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-6">Sign in to Velnio</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {login.isError && (
          <div className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
            {login.error.message}
          </div>
        )}
        <div>
          <label className="block text-sm font-medium mb-1.5">Email</label>
          <input type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">Password</label>
          <input type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button type="submit" className="btn-primary w-full" disabled={login.isPending}>
          {login.isPending ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
      <p className="text-sm text-center text-[var(--text-secondary)] mt-6">
        Don't have an account? <Link to="/register" className="text-[var(--accent)] hover:underline">Start for free</Link>
      </p>
    </div>
  )
}

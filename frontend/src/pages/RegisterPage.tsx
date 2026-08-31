import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useRegister } from '../hooks/useAuth'

export function RegisterPage() {
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', confirmPassword: '' })
  const register = useRegister()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirmPassword) return
    register.mutate({ first_name: form.first_name, last_name: form.last_name, email: form.email, password: form.password })
  }

  const update = (field: string, value: string) => setForm((f) => ({ ...f, [field]: value }))

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-6">Create your account</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {register.isError && (
          <div className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
            {register.error.message}
          </div>
        )}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">First Name</label>
            <input className="input" value={form.first_name} onChange={(e) => update('first_name', e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Last Name</label>
            <input className="input" value={form.last_name} onChange={(e) => update('last_name', e.target.value)} required />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">Email</label>
          <input type="email" className="input" value={form.email} onChange={(e) => update('email', e.target.value)} required />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">Password</label>
          <input type="password" className="input" value={form.password} onChange={(e) => update('password', e.target.value)} required minLength={8} />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">Confirm Password</label>
          <input type="password" className="input" value={form.confirmPassword} onChange={(e) => update('confirmPassword', e.target.value)} required />
        </div>
        {form.password && form.confirmPassword && form.password !== form.confirmPassword && (
          <p className="text-sm text-red-500">Passwords do not match</p>
        )}
        <button type="submit" className="btn-primary w-full" disabled={register.isPending || form.password !== form.confirmPassword}>
          {register.isPending ? 'Creating account...' : 'Create account'}
        </button>
      </form>
      <p className="text-sm text-center text-[var(--text-secondary)] mt-6">
        Already have an account? <Link to="/login" className="text-[var(--accent)] hover:underline">Sign in</Link>
      </p>
    </div>
  )
}

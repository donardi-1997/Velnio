import { useMe } from '../hooks/useAuth'

export function SettingsPage() {
  const { data: user } = useMe()

  return (
    <div>
      <h1 className="text-2xl font-bold mb-8">Settings</h1>
      <div className="card max-w-lg">
        <h2 className="font-semibold mb-4">Account</h2>
        <div className="space-y-4">
          <div className="flex justify-between items-center py-2 border-b border-[var(--border-color)]">
            <span className="text-sm text-[var(--text-secondary)]">Name</span>
            <span className="text-sm font-medium">{user?.first_name} {user?.last_name}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[var(--border-color)]">
            <span className="text-sm text-[var(--text-secondary)]">Email</span>
            <span className="text-sm font-medium">{user?.email}</span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-sm text-[var(--text-secondary)]">Status</span>
            <span className="text-sm font-medium text-green-600">Active</span>
          </div>
        </div>
      </div>
    </div>
  )
}

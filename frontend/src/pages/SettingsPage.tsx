import { useMe } from '../hooks/useAuth'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useState } from 'react'
import { GoogleDriveBrowser } from '../components/GoogleDriveBrowser'

export function SettingsPage() {
  const { data: user } = useMe()
  const queryClient = useQueryClient()
  const [showDriveBrowser, setShowDriveBrowser] = useState(false)

  const { data: driveStatus } = useQuery({
    queryKey: ['drive-status'],
    queryFn: () => api.googleDrive.getStatus(),
  })

  const disconnectMutation = useMutation({
    mutationFn: () => api.googleDrive.disconnect(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drive-status'] }),
  })

  const connectMutation = useMutation({
    mutationFn: () => api.googleDrive.connectMock(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drive-status'] }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-8">Settings</h1>
      <div className="space-y-6 max-w-lg">
        <div className="card">
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

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Google Drive</h2>
            {driveStatus?.connected && (
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Connected</span>
            )}
          </div>
          <div className="space-y-4">
            {driveStatus?.connected ? (
              <>
                <div className="flex justify-between items-center py-2 border-b border-[var(--border-color)]">
                  <span className="text-sm text-[var(--text-secondary)]">Account</span>
                  <span className="text-sm font-medium">{driveStatus.google_email}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-[var(--border-color)]">
                  <span className="text-sm text-[var(--text-secondary)]">Name</span>
                  <span className="text-sm font-medium">{driveStatus.google_name}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-[var(--text-secondary)]">Status</span>
                  <span className="text-sm font-medium text-green-400">Active</span>
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => setShowDriveBrowser(!showDriveBrowser)}
                    className="btn-secondary text-sm"
                  >
                    {showDriveBrowser ? 'Hide Browser' : 'Browse Files'}
                  </button>
                  <button
                    onClick={() => disconnectMutation.mutate()}
                    className="text-sm text-red-400 hover:text-red-300 px-3 py-1.5"
                    disabled={disconnectMutation.isPending}
                  >
                    {disconnectMutation.isPending ? 'Disconnecting...' : 'Disconnect'}
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-zinc-400 mb-3">Connect your Google Drive to import images and documents.</p>
                <button
                  onClick={() => connectMutation.mutate()}
                  className="btn-primary"
                  disabled={connectMutation.isPending}
                >
                  {connectMutation.isPending ? 'Connecting...' : 'Connect Google Drive'}
                </button>
              </div>
            )}
          </div>
          {showDriveBrowser && driveStatus?.connected && (
            <div className="mt-4">
              <GoogleDriveBrowser onClose={() => setShowDriveBrowser(false)} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

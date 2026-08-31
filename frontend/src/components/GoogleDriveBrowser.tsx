import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { GoogleDriveFile } from '../types'

interface Props {
  onSelect?: (file: GoogleDriveFile) => void
  selectionMode?: 'image' | 'document' | 'asset'
  onClose?: () => void
}

export function GoogleDriveBrowser({ onSelect, selectionMode = 'image', onClose }: Props) {
  const [currentFolder, setCurrentFolder] = useState('root')
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const queryClient = useQueryClient()

  const { data: status } = useQuery({
    queryKey: ['drive-status'],
    queryFn: () => api.googleDrive.getStatus(),
  })

  const { data: folderData, isLoading: folderLoading } = useQuery({
    queryKey: ['drive-browse', currentFolder],
    queryFn: () => api.googleDrive.browse(currentFolder),
    enabled: !isSearching && !!status?.connected,
  })

  const { data: searchData, isLoading: searchLoading } = useQuery({
    queryKey: ['drive-search', searchQuery],
    queryFn: () => api.googleDrive.search(searchQuery),
    enabled: isSearching && searchQuery.length > 0 && !!status?.connected,
  })

  const connectMutation = useMutation({
    mutationFn: () => api.googleDrive.connectMock(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['drive-status'] }),
  })

  const files = isSearching ? (searchData?.files || []) : (folderData?.files || [])
  const folders = isSearching ? [] : (folderData?.folders || [])

  const filteredFiles = files.filter((f: GoogleDriveFile) => {
    if (selectionMode === 'image') return f.mime_type.startsWith('image/')
    if (selectionMode === 'document') return f.mime_type === 'text/plain' || f.mime_type === 'application/pdf' || f.mime_type.includes('google-apps.document')
    if (selectionMode === 'asset') return f.mime_type.startsWith('image/')
    return true
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) setIsSearching(true)
  }

  const handleClearSearch = () => {
    setSearchQuery('')
    setIsSearching(false)
  }

  const handleFileClick = (file: GoogleDriveFile) => {
    if (file.is_folder && !isSearching) {
      setCurrentFolder(file.id)
    } else if (onSelect) {
      onSelect(file)
    }
  }

  if (!status?.connected) {
    return (
      <div className="bg-zinc-800 rounded-xl p-6 text-center">
        <div className="mb-4">
          <svg className="w-12 h-12 mx-auto text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
          </svg>
        </div>
        <h3 className="font-semibold text-zinc-200 mb-2">Google Drive Not Connected</h3>
        <p className="text-sm text-zinc-400 mb-4">Connect your Google Drive to import images and documents.</p>
        <button onClick={() => connectMutation.mutate()} className="btn-primary" disabled={connectMutation.isPending}>
          {connectMutation.isPending ? 'Connecting...' : 'Connect Google Drive'}
        </button>
      </div>
    )
  }

  return (
    <div className="bg-zinc-800 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-zinc-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-zinc-100">Google Drive</h3>
            <span className="text-xs text-zinc-400 bg-zinc-700 px-2 py-0.5 rounded-full">{status.google_email}</span>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-zinc-400 hover:text-zinc-200">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search files..."
            className="flex-1 bg-zinc-700 border border-zinc-600 rounded-lg px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          {isSearching ? (
            <button type="button" onClick={handleClearSearch} className="btn-secondary text-xs px-3 py-1.5">
              Clear
            </button>
          ) : (
            <button type="submit" className="btn-secondary text-xs px-3 py-1.5">
              Search
            </button>
          )}
        </form>
      </div>

      {!isSearching && currentFolder !== 'root' && (
        <div className="px-4 py-2 border-b border-zinc-700">
          <button
            onClick={() => setCurrentFolder('root')}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            Back to Root
          </button>
        </div>
      )}

      <div className="max-h-80 overflow-y-auto">
        {folderLoading || searchLoading ? (
          <div className="p-8 text-center text-zinc-400 text-sm">Loading...</div>
        ) : (
          <div className="p-2">
            {folders.length > 0 && !isSearching && (
              <div className="mb-2">
                {folders.map((folder: GoogleDriveFile) => (
                  <button
                    key={folder.id}
                    onClick={() => handleFileClick(folder)}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-zinc-700 transition-colors text-left"
                  >
                    <svg className="w-5 h-5 text-amber-400 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
                    </svg>
                    <span className="text-sm text-zinc-200 truncate">{folder.name}</span>
                  </button>
                ))}
              </div>
            )}

            {filteredFiles.length === 0 && folders.length === 0 ? (
              <div className="p-8 text-center text-zinc-400 text-sm">
                {isSearching ? 'No matching files found' : 'No files in this folder'}
              </div>
            ) : (
              filteredFiles.map((file: GoogleDriveFile) => (
                <button
                  key={file.id}
                  onClick={() => handleFileClick(file)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-zinc-700 transition-colors text-left"
                >
                  {file.mime_type.startsWith('image/') ? (
                    <div className="w-8 h-8 bg-zinc-700 rounded flex-shrink-0 overflow-hidden">
                      <img src={file.thumbnail_url || ''} alt="" className="w-full h-full object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                    </div>
                  ) : (
                    <svg className="w-5 h-5 text-zinc-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-zinc-200 truncate">{file.name}</div>
                    <div className="text-xs text-zinc-500">
                      {file.size ? `${(file.size / 1024).toFixed(1)} KB` : file.mime_type}
                    </div>
                  </div>
                  {onSelect && !file.is_folder && (
                    <span className="text-xs text-indigo-400 flex-shrink-0">Select</span>
                  )}
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ThemeState {
  dark: boolean
  toggle: () => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      dark: typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches,
      toggle: () => set((s) => ({ dark: !s.dark })),
    }),
    { name: 'velnio-theme' }
  )
)

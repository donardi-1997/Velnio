import { useEffect } from 'react'
import { useThemeStore } from '../stores/theme'

export function useTheme() {
  const { dark, toggle } = useThemeStore()
  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [dark])
  return { dark, toggle }
}

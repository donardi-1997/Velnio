import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/auth'

export function useLogin() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  return useMutation({
    mutationFn: (data: { email: string; password: string }) => api.auth.login(data),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
      navigate('/dashboard')
    },
  })
}

export function useRegister() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  return useMutation({
    mutationFn: (data: { email: string; password: string; first_name: string; last_name: string }) =>
      api.auth.register(data),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
      navigate('/dashboard')
    },
  })
}

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: api.auth.me })
}

export function useLogout() {
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  return () => {
    logout()
    navigate('/login')
  }
}

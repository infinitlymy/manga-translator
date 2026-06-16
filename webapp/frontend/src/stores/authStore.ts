import { create } from 'zustand'

interface AuthState {
  token: string | null
  setupCompleted: boolean
  user: { id: string; email: string; role: string } | null
  setToken: (token: string | null) => void
  setSetupCompleted: (v: boolean) => void
  setUser: (user: { id: string; email: string; role: string } | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  setupCompleted: true, // will be checked on mount
  user: null,
  setToken: (token) => {
    if (token) localStorage.setItem('access_token', token)
    else localStorage.removeItem('access_token')
    set({ token })
  },
  setSetupCompleted: (v) => set({ setupCompleted: v }),
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem('access_token')
    set({ token: null, user: null })
  },
}))

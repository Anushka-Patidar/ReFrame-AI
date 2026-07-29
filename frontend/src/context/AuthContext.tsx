import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../lib/api'
import type { SessionUser } from '../types/api'

const STORAGE_KEY = 'reframe-auth-token'

type AuthContextValue = {
  token: string | null
  user: SessionUser | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (payload: { email: string; password: string }) => Promise<void>
  signup: (payload: {
    name: string
    email: string
    phone: string
    city: string
    password: string
  }) => Promise<void>
  logout: () => void
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY))
  const [user, setUser] = useState<SessionUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const persistSession = useCallback((nextToken: string, nextUser: SessionUser) => {
    localStorage.setItem(STORAGE_KEY, nextToken)
    setToken(nextToken)
    setUser(nextUser)
  }, [])

  const clearSession = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const refreshSession = useCallback(async () => {
    const savedToken = localStorage.getItem(STORAGE_KEY)
    if (!savedToken) {
      setIsLoading(false)
      return
    }

    try {
      const response = await api.me(savedToken)
      persistSession(response.access_token, response.user)
    } catch {
      clearSession()
    } finally {
      setIsLoading(false)
    }
  }, [clearSession, persistSession])

  useEffect(() => {
    void refreshSession()
  }, [refreshSession])

  const login = useCallback(
    async (payload: { email: string; password: string }) => {
      const response = await api.login(payload)
      persistSession(response.access_token, response.user)
    },
    [persistSession],
  )

  const signup = useCallback(
    async (payload: {
      name: string
      email: string
      phone: string
      city: string
      password: string
    }) => {
      const response = await api.signup(payload)
      persistSession(response.access_token, response.user)
    },
    [persistSession],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isLoading,
      isAuthenticated: Boolean(token && user),
      login,
      signup,
      logout: clearSession,
      refreshSession,
    }),
    [clearSession, isLoading, login, refreshSession, signup, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider.')
  }
  return context
}

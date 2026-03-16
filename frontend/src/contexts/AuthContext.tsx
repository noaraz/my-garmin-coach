import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { googleAuth } from '../api/client'

interface User {
  id: number
  email: string
  isAdmin: boolean
}

interface AuthContextValue {
  user: User | null
  accessToken: string | null
  isAdmin: boolean
  googleLogin: (idToken: string, inviteCode?: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

interface JwtPayload {
  userId?: number
  sub?: string
  email?: string
  exp?: number
  is_admin?: boolean
}

function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = parts[1]
    // base64url → base64
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=')
    return JSON.parse(atob(padded)) as JwtPayload
  } catch {
    return null
  }
}

function isTokenExpired(payload: JwtPayload): boolean {
  if (!payload.exp) return false
  return Date.now() / 1000 > payload.exp
}

function userFromPayload(payload: JwtPayload): User | null {
  const id = payload.userId ?? (payload.sub ? parseInt(payload.sub, 10) : undefined)
  const email = payload.email
  if (!id || !email) return null
  return { id, email, isAdmin: payload.is_admin ?? false }
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  accessToken: null,
  isAdmin: false,
  googleLogin: async () => {},
  logout: () => {},
  isLoading: true,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const isAdmin = user?.isAdmin ?? false

  useEffect(() => {
    const stored = localStorage.getItem('access_token')
    if (stored) {
      const payload = decodeJwtPayload(stored)
      if (payload && !isTokenExpired(payload)) {
        const parsedUser = userFromPayload(payload)
        if (parsedUser) {
          setUser(parsedUser)
          setAccessToken(stored)
        } else {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      } else {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
    }
    setIsLoading(false)
  }, [])

  const googleLogin = async (idToken: string, inviteCode?: string): Promise<void> => {
    const data = await googleAuth(idToken, inviteCode)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    setAccessToken(data.access_token)
    const payload = decodeJwtPayload(data.access_token)
    if (payload) {
      setUser(userFromPayload(payload))
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    setAccessToken(null)
  }

  return (
    <AuthContext.Provider value={{ user, accessToken, isAdmin, googleLogin, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

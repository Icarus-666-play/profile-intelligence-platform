import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { api, type AuthSession, type AuthStatus } from './api'

const TOKEN_KEY = 'pip.auth.token'
const ENTRY_KEY = 'pip.flow.passedLogin'

type AuthContextValue = {
  status: AuthStatus | null
  session: AuthSession | null
  ready: boolean
  passedLogin: boolean
  login: (username: string, password: string) => Promise<void>
  continueAsGuest: () => Promise<void>
  logout: () => Promise<void>
  markPassedLogin: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null)
  const [session, setSession] = useState<AuthSession | null>(null)
  const [ready, setReady] = useState(false)
  const [passedLogin, setPassedLogin] = useState(
    () => sessionStorage.getItem(ENTRY_KEY) === '1',
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const authStatus = await api.authStatus()
        if (cancelled) return
        setStatus(authStatus)
        const token = localStorage.getItem(TOKEN_KEY)
        if (token) {
          const resolved = await api.authSession(token)
          if (!cancelled && resolved.session) {
            setSession(resolved.session)
            setPassedLogin(true)
            sessionStorage.setItem(ENTRY_KEY, '1')
          } else {
            localStorage.removeItem(TOKEN_KEY)
          }
        }
      } catch {
        if (!cancelled) {
          setStatus({
            enabled: false,
            allow_guest: true,
            username_hint: null,
            flow: ['login', 'home', 'dashboard'],
          })
        }
      } finally {
        if (!cancelled) setReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  async function persist(next: AuthSession) {
    localStorage.setItem(TOKEN_KEY, next.token)
    sessionStorage.setItem(ENTRY_KEY, '1')
    setSession(next)
    setPassedLogin(true)
  }

  const value: AuthContextValue = {
    status,
    session,
    ready,
    passedLogin,
    markPassedLogin: () => {
      sessionStorage.setItem(ENTRY_KEY, '1')
      setPassedLogin(true)
    },
    login: async (username, password) => {
      const result = await api.login(username, password)
      await persist(result.session)
    },
    continueAsGuest: async () => {
      const result = await api.guest()
      await persist(result.session)
    },
    logout: async () => {
      const token = session?.token || localStorage.getItem(TOKEN_KEY)
      try {
        await api.logout(token)
      } finally {
        localStorage.removeItem(TOKEN_KEY)
        sessionStorage.removeItem(ENTRY_KEY)
        setSession(null)
        setPassedLogin(false)
      }
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth requires AuthProvider')
  return ctx
}

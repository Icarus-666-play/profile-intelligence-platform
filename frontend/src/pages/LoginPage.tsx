import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function LoginPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (auth.ready && auth.passedLogin) {
    return <Navigate to="/" replace />
  }

  async function continueGuest() {
    setBusy(true)
    setError(null)
    try {
      await auth.continueAsGuest()
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await auth.login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="entry-screen">
      <div className="entry-plane" aria-hidden="true" />
      <div className="entry-panel">
        <p className="entry-kicker">Optional entry</p>
        <h1 className="entry-brand">Profile Intelligence Platform</h1>
        <p className="entry-lead">
          Sign in locally, or continue as guest to Home, then open the Dashboard.
        </p>

        {error && <p className="status error">{error}</p>}

        <form className="entry-form" onSubmit={onSubmit}>
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder={auth.status?.username_hint || 'operator'}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder={auth.status?.enabled ? 'required' : 'optional'}
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        {auth.status?.allow_guest !== false && (
          <button
            type="button"
            className="secondary entry-skip"
            onClick={continueGuest}
            disabled={busy}
          >
            Continue without login
          </button>
        )}

        <p className="entry-flow muted">
          Login (optional) → Home → Dashboard
        </p>
        <p className="muted">
          <Link to="/">Skip to Home</Link>
        </p>
      </div>
    </div>
  )
}

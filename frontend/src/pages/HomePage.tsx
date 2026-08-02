import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function HomePage() {
  const auth = useAuth()

  if (auth.ready && !auth.passedLogin) {
    return <Navigate to="/login" replace />
  }

  const who =
    auth.session?.mode === 'guest'
      ? 'Guest'
      : auth.session?.username || 'Operator'

  return (
    <div className="home-screen">
      <div className="home-visual" aria-hidden="true" />
      <div className="home-copy">
        <p className="entry-kicker">Home</p>
        <h1 className="entry-brand">Profile Intelligence Platform</h1>
        <p className="entry-lead">
          Local-first profile intelligence. Continue to the Dashboard for
          confidence, sources, and operator tools.
        </p>
        <div className="home-actions">
          <Link className="button" to="/dashboard">
            Open Dashboard
          </Link>
          <Link className="button secondary" to="/login">
            Login
          </Link>
        </div>
        <p className="muted home-meta">
          Signed in as {who}
          {auth.session?.guest ? ' (optional login skipped)' : ''}
        </p>
        <p className="entry-flow muted">Login (optional) → Home → Dashboard</p>
      </div>
    </div>
  )
}

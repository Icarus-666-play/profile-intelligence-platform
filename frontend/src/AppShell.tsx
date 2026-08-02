import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from './auth'

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/search', label: 'Search' },
  { to: '/import', label: 'Import' },
  { to: '/compare', label: 'Compare' },
  { to: '/reports', label: 'Reports' },
  { to: '/settings', label: 'Settings' },
  { to: '/plugins', label: 'Plugins' },
  { to: '/logs', label: 'Logs' },
  { to: '/about', label: 'About' },
] as const

export default function AppShell() {
  const auth = useAuth()
  const navigate = useNavigate()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">Profile Intelligence Platform</div>
          <div className="brand-sub">Local-first profile analysis</div>
        </div>
        <nav aria-label="Primary">
          <ul className="nav-list">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={'end' in item ? item.end : false}
                  className={({ isActive }) =>
                    isActive ? 'nav-link active' : 'nav-link'
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="stack-chip">
          Login (optional) → Home → Dashboard
          <br />
          <span className="muted">
            {auth.session
              ? `${auth.session.guest ? 'Guest' : auth.session.username}`
              : 'No session'}
          </span>
          <br />
          <button
            type="button"
            className="secondary sidebar-auth"
            onClick={() => {
              void auth.logout().then(() => navigate('/login', { replace: true }))
            }}
          >
            {auth.session ? 'Sign out' : 'Login'}
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}

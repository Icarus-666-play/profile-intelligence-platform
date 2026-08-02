import { NavLink, Route, Routes } from 'react-router-dom'
import AboutPage from './pages/AboutPage'
import ComparePage from './pages/ComparePage'
import DashboardPage from './pages/DashboardPage'
import ImportPage from './pages/ImportPage'
import LogsPage from './pages/LogsPage'
import PluginsPage from './pages/PluginsPage'
import ReportsPage from './pages/ReportsPage'
import SearchPage from './pages/SearchPage'
import SettingsPage from './pages/SettingsPage'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/search', label: 'Search' },
  { to: '/import', label: 'Import' },
  { to: '/compare', label: 'Compare' },
  { to: '/reports', label: 'Reports' },
  { to: '/settings', label: 'Settings' },
  { to: '/plugins', label: 'Plugins' },
  { to: '/logs', label: 'Logs' },
  { to: '/about', label: 'About' },
] as const

export default function App() {
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
          Browser → React → REST → FastAPI
          <br />
          → Application → Repository
          <br />
          → SQLite → File Storage
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/plugins" element={<PluginsPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
    </div>
  )
}

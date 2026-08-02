import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AppShell from './AppShell'
import { useAuth } from './auth'
import AboutPage from './pages/AboutPage'
import ComparePage from './pages/ComparePage'
import DashboardPage from './pages/DashboardPage'
import HomePage from './pages/HomePage'
import ImportPage from './pages/ImportPage'
import LoginPage from './pages/LoginPage'
import LogsPage from './pages/LogsPage'
import PluginsPage from './pages/PluginsPage'
import ReportsPage from './pages/ReportsPage'
import SearchPage from './pages/SearchPage'
import SettingsPage from './pages/SettingsPage'

function RequireEntry({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const location = useLocation()
  if (!auth.ready) {
    return <p className="muted entry-loading">Loading…</p>
  }
  if (!auth.passedLogin) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireEntry>
            <HomePage />
          </RequireEntry>
        }
      />
      <Route
        element={
          <RequireEntry>
            <AppShell />
          </RequireEntry>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/import" element={<ImportPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/plugins" element={<PluginsPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/about" element={<AboutPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

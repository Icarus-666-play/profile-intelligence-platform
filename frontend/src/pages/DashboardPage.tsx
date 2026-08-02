import { useEffect, useState } from 'react'
import { api, type DashboardSnapshot } from '../api'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .dashboard()
      .then((snapshot) => {
        if (!cancelled) setData(snapshot)
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-lead">
        Local overview of profiles and confidence scores from SQLite.
      </p>
      {error && <p className="status error">{error}</p>}
      {!data && !error && <p className="muted">Loading dashboard…</p>}
      {data && (
        <>
          <div className="metric-row">
            <div className="metric">
              <span className="metric-label">Profiles</span>
              <span className="metric-value">{data.total_profiles}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Scored</span>
              <span className="metric-value">{data.scored_profiles}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Average score</span>
              <span className="metric-value">
                {data.average_score == null ? '—' : Math.round(data.average_score)}
              </span>
            </div>
          </div>
          <div className="panel">
            <h2>Top profiles</h2>
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Source</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {data.top_profiles.length === 0 && (
                  <tr>
                    <td colSpan={3} className="muted">
                      No profiles yet — import to get started.
                    </td>
                  </tr>
                )}
                {data.top_profiles.map((row) => (
                  <tr key={row.id}>
                    <td>{row.display_name}</td>
                    <td>{row.source || '—'}</td>
                    <td>{row.score ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}

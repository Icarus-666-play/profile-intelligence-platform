import { useEffect, useState } from 'react'
import { api, type Analytics } from '../api'

export default function ReportsPage() {
  const [data, setData] = useState<Analytics | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .analytics()
      .then((payload) => {
        if (!cancelled) setData(payload)
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
      <h1 className="page-title">Reports</h1>
      <p className="page-lead">
        Analytics snapshot from the application layer. Excel exports remain
        available via <code>pip-app export</code>.
      </p>
      {error && <p className="status error">{error}</p>}
      {!data && !error && <p className="muted">Loading analytics…</p>}
      {data && (
        <>
          <div className="metric-row">
            <div className="metric">
              <span className="metric-label">Profiles</span>
              <span className="metric-value">{data.profiles}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Duplicate pairs</span>
              <span className="metric-value">{data.duplicates.pairs}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Classified</span>
              <span className="metric-value">{data.classification.count}</span>
            </div>
          </div>
          <div className="panel">
            <h2>By source</h2>
            <table className="table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {data.by_source.map((row) => (
                  <tr key={row.source}>
                    <td>{row.source}</td>
                    <td>{row.count}</td>
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

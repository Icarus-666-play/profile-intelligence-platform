import { useEffect, useState } from 'react'
import { api, type DashboardSnapshot } from '../api'

type PanelKey = 'latest' | 'newest' | 'duplicates' | 'queue'

const PANELS: { key: PanelKey; label: string }[] = [
  { key: 'latest', label: 'Latest Imports' },
  { key: 'newest', label: 'Newest Profiles' },
  { key: 'duplicates', label: 'Duplicates' },
  { key: 'queue', label: 'Import Queue' },
]

function formatCount(value: number): string {
  return value.toLocaleString('en-US')
}

function formatPrice(
  value: number | null | undefined,
  currency: string | undefined,
): string {
  if (value == null) return '—'
  const symbol =
    currency === 'USD' ? '$' : currency === 'GBP' ? '£' : currency === 'EUR' ? '€' : `${currency || 'EUR'} `
  return `${symbol}${Math.round(value).toLocaleString('en-US')}`
}

function formatRating(value: number | null | undefined): string {
  if (value == null) return '—'
  return value.toFixed(2)
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [panel, setPanel] = useState<PanelKey>('latest')

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
        Profiles, imports, geography, pricing, and ratings from the local database.
      </p>
      {error && <p className="status error">{error}</p>}
      {!data && !error && <p className="muted">Loading dashboard…</p>}
      {data && (
        <>
          <div className="metric-row metric-row-5">
            <div className="metric">
              <span className="metric-label">Profiles</span>
              <span className="metric-value">
                {formatCount(data.total_profiles)}
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Imported Today</span>
              <span className="metric-value">
                {formatCount(data.imported_today ?? 0)}
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Countries</span>
              <span className="metric-value">
                {formatCount(data.countries ?? 0)}
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Average Price</span>
              <span className="metric-value">
                {formatPrice(
                  data.average_price,
                  data.average_price_currency,
                )}
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Average Rating</span>
              <span className="metric-value">
                {formatRating(data.average_rating)}
              </span>
            </div>
          </div>

          <div className="dash-panels">
            <div className="dash-tabs" role="tablist" aria-label="Dashboard lists">
              {PANELS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  role="tab"
                  aria-selected={panel === item.key}
                  className={
                    panel === item.key ? 'dash-tab active' : 'dash-tab'
                  }
                  onClick={() => setPanel(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="panel dash-panel-body" role="tabpanel">
              {panel === 'latest' && (
                <>
                  <h2>Latest Imports</h2>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>File</th>
                        <th>Imported</th>
                        <th>Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.latest_imports?.length ?? 0) === 0 && (
                        <tr>
                          <td colSpan={3} className="muted">
                            No ledger imports yet.
                          </td>
                        </tr>
                      )}
                      {data.latest_imports?.map((item) => (
                        <tr key={`${item.path}-${item.imported_at}`}>
                          <td>{item.name}</td>
                          <td>{item.imported_at || '—'}</td>
                          <td>{formatCount(item.file_size)} B</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {panel === 'newest' && (
                <>
                  <h2>Newest Profiles</h2>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Location</th>
                        <th>Source</th>
                        <th>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.newest_profiles?.length ?? 0) === 0 && (
                        <tr>
                          <td colSpan={4} className="muted">
                            No profiles yet — import to get started.
                          </td>
                        </tr>
                      )}
                      {data.newest_profiles?.map((row) => (
                        <tr key={row.id}>
                          <td>{row.display_name}</td>
                          <td>{row.location || '—'}</td>
                          <td>{row.source || '—'}</td>
                          <td>{row.score ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {panel === 'duplicates' && (
                <>
                  <h2>Duplicates</h2>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Left</th>
                        <th>Right</th>
                        <th>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.duplicates?.length ?? 0) === 0 && (
                        <tr>
                          <td colSpan={3} className="muted">
                            No near-duplicates detected.
                          </td>
                        </tr>
                      )}
                      {data.duplicates?.map((item) => (
                        <tr key={`${item.left_id}-${item.right_id}`}>
                          <td>
                            #{item.left_id} {item.left_name}
                          </td>
                          <td>
                            #{item.right_id} {item.right_name}
                          </td>
                          <td>{item.score.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {panel === 'queue' && (
                <>
                  <h2>Import Queue</h2>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>File</th>
                        <th>Path</th>
                        <th>Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data.import_queue?.length ?? 0) === 0 && (
                        <tr>
                          <td colSpan={3} className="muted">
                            Inbox is clear — no new files waiting.
                          </td>
                        </tr>
                      )}
                      {data.import_queue?.map((item) => (
                        <tr key={item.path}>
                          <td>{item.name}</td>
                          <td className="muted">{item.path}</td>
                          <td>{formatCount(item.file_size)} B</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  )
}

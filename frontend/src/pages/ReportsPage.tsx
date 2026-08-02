import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Analytics } from '../api'

type PanelKey =
  | 'countries'
  | 'average_prices'
  | 'languages'
  | 'services'
  | 'duplicates'
  | 'monthly_imports'
  | 'import_trend'

const PANELS: { key: PanelKey; label: string }[] = [
  { key: 'countries', label: 'Countries' },
  { key: 'average_prices', label: 'Average Prices' },
  { key: 'languages', label: 'Languages' },
  { key: 'services', label: 'Services' },
  { key: 'duplicates', label: 'Duplicates' },
  { key: 'monthly_imports', label: 'Monthly Imports' },
  { key: 'import_trend', label: 'Import Trend' },
]

function formatCount(value: number) {
  return value.toLocaleString('en-US')
}

function formatPrice(value: number, currency: string) {
  const code = (currency || 'EUR').toUpperCase()
  const symbol =
    code === 'EUR' ? '€' : code === 'USD' ? '$' : code === 'GBP' ? '£' : `${code} `
  return `${symbol}${Math.round(value).toLocaleString('en-US')}`
}

function maxCount(items: { count: number }[]) {
  return Math.max(1, ...items.map((item) => item.count))
}

function DistributionTable({
  rows,
  empty,
}: {
  rows: { name: string; count: number }[]
  empty: string
}) {
  if (!rows.length) return <p className="muted">{empty}</p>
  const peak = maxCount(rows)
  return (
    <table className="table report-dist-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Count</th>
          <th>Share</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.name}>
            <td>{row.name}</td>
            <td>{formatCount(row.count)}</td>
            <td>
              <div className="report-bar-track" aria-hidden="true">
                <div
                  className="report-bar-fill"
                  style={{ width: `${(row.count / peak) * 100}%` }}
                />
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function TrendBars({
  rows,
  empty,
}: {
  rows: { period: string; count: number }[]
  empty: string
}) {
  if (!rows.length) return <p className="muted">{empty}</p>
  const peak = maxCount(rows)
  return (
    <div className="report-trend">
      {rows.map((row) => (
        <div key={row.period} className="report-trend-col" title={`${row.period}: ${row.count}`}>
          <div className="report-trend-bar-wrap">
            <div
              className="report-trend-bar"
              style={{ height: `${(row.count / peak) * 100}%` }}
            />
          </div>
          <span className="report-trend-label">
            {row.period.length === 7 ? row.period.slice(2) : row.period.slice(5)}
          </span>
          <span className="report-trend-count">{row.count}</span>
        </div>
      ))}
    </div>
  )
}

export default function ReportsPage() {
  const [data, setData] = useState<Analytics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [panel, setPanel] = useState<PanelKey>('countries')

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
    <section className="reports-page">
      <h1 className="page-title">Reports</h1>
      <p className="page-lead">
        Distributions and import trends from the local database. Excel exports
        remain available via <code>pip-app export</code>.
      </p>
      {error && <p className="status error">{error}</p>}
      {!data && !error && <p className="muted">Loading analytics…</p>}
      {data && (
        <>
          <div className="metric-row">
            <div className="metric">
              <span className="metric-label">Profiles</span>
              <span className="metric-value">{formatCount(data.profiles)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Duplicate pairs</span>
              <span className="metric-value">
                {formatCount(data.duplicates.pairs)}
              </span>
            </div>
            <div className="metric">
              <span className="metric-label">Countries</span>
              <span className="metric-value">
                {formatCount(data.countries?.length ?? 0)}
              </span>
            </div>
          </div>

          <div className="dash-panels">
            <div className="dash-tabs" role="tablist" aria-label="Reports panels">
              {PANELS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  role="tab"
                  aria-selected={panel === item.key}
                  className={panel === item.key ? 'dash-tab active' : 'dash-tab'}
                  onClick={() => setPanel(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="panel dash-panel-body" role="tabpanel">
              {panel === 'countries' && (
                <>
                  <h2>Countries</h2>
                  <DistributionTable
                    rows={data.countries ?? []}
                    empty="No country data yet."
                  />
                </>
              )}

              {panel === 'average_prices' && (
                <>
                  <h2>Average Prices</h2>
                  {(data.average_prices ?? []).length === 0 ? (
                    <p className="muted">No rate data yet.</p>
                  ) : (
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Duration</th>
                          <th>Average</th>
                          <th>Currency</th>
                          <th>Rates</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.average_prices.map((row) => (
                          <tr key={`${row.label}-${row.currency}`}>
                            <td>{row.label}</td>
                            <td>{formatPrice(row.average, row.currency)}</td>
                            <td>{row.currency}</td>
                            <td>{formatCount(row.count)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </>
              )}

              {panel === 'languages' && (
                <>
                  <h2>Languages</h2>
                  <DistributionTable
                    rows={data.languages ?? []}
                    empty="No language data yet."
                  />
                </>
              )}

              {panel === 'services' && (
                <>
                  <h2>Services</h2>
                  <DistributionTable
                    rows={data.services ?? []}
                    empty="No service data yet."
                  />
                </>
              )}

              {panel === 'duplicates' && (
                <>
                  <h2>Duplicates</h2>
                  <p className="muted">
                    {formatCount(data.duplicates.pairs)} pairs ·{' '}
                    {formatCount(data.duplicates.groups)} groups
                  </p>
                  {(data.duplicate_pairs ?? []).length === 0 ? (
                    <p className="muted">No near-duplicate pairs found.</p>
                  ) : (
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Left</th>
                          <th>Right</th>
                          <th>Score</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.duplicate_pairs.map((row) => (
                          <tr key={`${row.left_id}-${row.right_id}`}>
                            <td>
                              {row.left_name}{' '}
                              <span className="muted">#{row.left_id}</span>
                            </td>
                            <td>
                              {row.right_name}{' '}
                              <span className="muted">#{row.right_id}</span>
                            </td>
                            <td>{row.score.toFixed(3)}</td>
                            <td>
                              <Link
                                to={`/compare?left=${row.left_id}&right=${row.right_id}`}
                              >
                                Compare
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </>
              )}

              {panel === 'monthly_imports' && (
                <>
                  <h2>Monthly Imports</h2>
                  <TrendBars
                    rows={data.monthly_imports ?? []}
                    empty="No monthly import history yet."
                  />
                </>
              )}

              {panel === 'import_trend' && (
                <>
                  <h2>Import Trend</h2>
                  <p className="muted">Daily imports over the last 30 days.</p>
                  <TrendBars
                    rows={data.import_trend ?? []}
                    empty="No import trend data yet."
                  />
                </>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  )
}

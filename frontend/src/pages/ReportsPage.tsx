import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, type Analytics } from '../api'

const SECTIONS = [
  { id: 'countries', label: 'Countries' },
  { id: 'average-prices', label: 'Average Prices' },
  { id: 'languages', label: 'Languages' },
  { id: 'services', label: 'Services' },
  { id: 'duplicates', label: 'Duplicates' },
  { id: 'monthly-imports', label: 'Monthly Imports' },
  { id: 'import-trend', label: 'Import Trend' },
] as const

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

function ReportSection({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: ReactNode
}) {
  return (
    <section id={id} className="panel report-section">
      <h2 className="report-section-title">{title}</h2>
      {children}
    </section>
  )
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
        <div
          key={row.period}
          className="report-trend-col"
          title={`${row.period}: ${row.count}`}
        >
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
        Countries, prices, languages, services, duplicates, and import trends
        from the local database.
      </p>
      {error && <p className="status error">{error}</p>}
      {!data && !error && <p className="muted">Loading analytics…</p>}
      {data && (
        <>
          <nav className="report-jump" aria-label="Report sections">
            {SECTIONS.map((section) => (
              <a key={section.id} href={`#${section.id}`}>
                {section.label}
              </a>
            ))}
          </nav>

          <div className="report-sections">
            <ReportSection id="countries" title="Countries">
              <DistributionTable
                rows={data.countries ?? []}
                empty="No country data yet."
              />
            </ReportSection>

            <ReportSection id="average-prices" title="Average Prices">
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
            </ReportSection>

            <ReportSection id="languages" title="Languages">
              <DistributionTable
                rows={data.languages ?? []}
                empty="No language data yet."
              />
            </ReportSection>

            <ReportSection id="services" title="Services">
              <DistributionTable
                rows={data.services ?? []}
                empty="No service data yet."
              />
            </ReportSection>

            <ReportSection id="duplicates" title="Duplicates">
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
            </ReportSection>

            <ReportSection id="monthly-imports" title="Monthly Imports">
              <TrendBars
                rows={data.monthly_imports ?? []}
                empty="No monthly import history yet."
              />
            </ReportSection>

            <ReportSection id="import-trend" title="Import Trend">
              <p className="muted">Daily imports over the last 30 days.</p>
              <TrendBars
                rows={data.import_trend ?? []}
                empty="No import trend data yet."
              />
            </ReportSection>
          </div>
        </>
      )}
    </section>
  )
}

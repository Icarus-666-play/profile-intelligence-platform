import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Profile } from '../api'

const MAX_COMPARE = 2

function formatImported(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatPrice(profile: Profile) {
  if (profile.average_price == null) return '—'
  const code = (profile.average_price_currency || 'EUR').toUpperCase()
  const symbol =
    code === 'EUR' ? '€' : code === 'USD' ? '$' : code === 'GBP' ? '£' : `${code} `
  return `${symbol}${Math.round(profile.average_price)}`
}

function formatRating(value: number | null | undefined) {
  if (value == null) return '—'
  return value.toFixed(2)
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<Profile[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<number[]>([])

  async function runSearch(nextQuery: string) {
    setLoading(true)
    setError(null)
    try {
      const result = await api.profiles({
        q: nextQuery.trim() || undefined,
        limit: 50,
      })
      setItems(result.items)
      setTotal(result.total)
      setSelected((current) =>
        current.filter((id) => result.items.some((row) => row.id === id)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void runSearch('')
  }, [])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    await runSearch(query)
  }

  function toggleCompare(id: number) {
    setSelected((current) => {
      if (current.includes(id)) {
        return current.filter((item) => item !== id)
      }
      if (current.length >= MAX_COMPARE) {
        return [...current.slice(1), id]
      }
      return [...current, id]
    })
  }

  const compareReady = selected.length === MAX_COMPARE
  const compareHref = compareReady
    ? `/compare?left=${selected[0]}&right=${selected[1]}`
    : '/compare'

  return (
    <section className="search-page">
      <h1 className="page-title">Search</h1>
      <p className="page-lead">Find profiles in the local database.</p>
      <form className="form-row" onSubmit={onSubmit}>
        <label>
          Query
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Name, email, source…"
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>
      {error && <p className="status error">{error}</p>}

      <div className="compare-selection-bar">
        <p>
          Compare{' '}
          <span className="muted">
            ({selected.length}/{MAX_COMPARE} selected)
          </span>
        </p>
        {compareReady ? (
          <Link className="button-link" to={compareHref}>
            Compare selected
          </Link>
        ) : (
          <button type="button" disabled>
            Select two profiles
          </button>
        )}
      </div>

      <div className="panel">
        <h2>
          Results <span className="muted">({total})</span>
        </h2>
        {items.length === 0 ? (
          <p className="muted">
            {loading
              ? 'Loading profiles…'
              : 'No profiles matched. Try another query or import first.'}
          </p>
        ) : (
          <ul className="profile-list">
            {items.map((row) => {
              const checked = selected.includes(row.id)
              const disabled = !checked && selected.length >= MAX_COMPARE
              return (
                <li key={row.id} className="profile-list-row">
                  <div className="profile-list-photo">
                    {row.photo ? (
                      <img src={row.photo} alt="" />
                    ) : (
                      <div className="profile-list-photo-fallback" aria-hidden="true">
                        {(row.display_name || '?').slice(0, 1).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <div className="profile-list-body">
                    <div className="profile-list-headline">
                      <h3>{row.display_name}</h3>
                      <span className="muted">#{row.id}</span>
                    </div>
                    <dl className="profile-list-fields">
                      <div>
                        <dt>Age</dt>
                        <dd>{row.age || '—'}</dd>
                      </div>
                      <div>
                        <dt>Country</dt>
                        <dd>{row.country || '—'}</dd>
                      </div>
                      <div>
                        <dt>Languages</dt>
                        <dd>
                          {row.languages?.length ? (
                            <ul className="profile-chip-list">
                              {row.languages.map((language) => (
                                <li key={language}>{language}</li>
                              ))}
                            </ul>
                          ) : (
                            '—'
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Rating</dt>
                        <dd>{formatRating(row.rating)}</dd>
                      </div>
                      <div>
                        <dt>Average Price</dt>
                        <dd>{formatPrice(row)}</dd>
                      </div>
                      <div>
                        <dt>Imported</dt>
                        <dd>{formatImported(row.imported ?? row.created_at)}</dd>
                      </div>
                    </dl>
                  </div>
                  <label className="profile-compare-toggle">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggleCompare(row.id)}
                    />
                    <span>Compare</span>
                  </label>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </section>
  )
}

import { useState } from 'react'
import type { FormEvent } from 'react'
import { api, type Profile } from '../api'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState<Profile[]>([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const result = await api.profiles({
        q: query.trim() || undefined,
        limit: 50,
      })
      setItems(result.items)
      setTotal(result.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
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
      <div className="panel">
        <h2>
          Results <span className="muted">({total})</span>
        </h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>Source</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  Run a search or leave the query blank to list recent profiles.
                </td>
              </tr>
            )}
            {items.map((row) => (
              <tr key={row.id}>
                <td>{row.id}</td>
                <td>{row.display_name}</td>
                <td>{row.email || '—'}</td>
                <td>{row.source || '—'}</td>
                <td>{row.score ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

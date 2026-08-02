import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type Comparison } from '../api'

export default function ComparePage() {
  const [params] = useSearchParams()
  const [leftId, setLeftId] = useState(params.get('left') || '')
  const [rightId, setRightId] = useState(params.get('right') || '')
  const [result, setResult] = useState<Comparison | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function runCompare(left: string, right: string) {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const comparison = await api.compare(Number(left), Number(right))
      setResult(comparison)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    const left = params.get('left') || ''
    const right = params.get('right') || ''
    setLeftId(left)
    setRightId(right)
    if (left && right) {
      void runCompare(left, right)
    }
  }, [params])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    await runCompare(leftId, rightId)
  }

  return (
    <section>
      <h1 className="page-title">Compare</h1>
      <p className="page-lead">Diff two profiles side by side.</p>
      <form className="form-row" onSubmit={onSubmit}>
        <label>
          Left ID
          <input
            value={leftId}
            onChange={(e) => setLeftId(e.target.value)}
            inputMode="numeric"
            required
          />
        </label>
        <label>
          Right ID
          <input
            value={rightId}
            onChange={(e) => setRightId(e.target.value)}
            inputMode="numeric"
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Comparing…' : 'Compare'}
        </button>
      </form>
      {error && <p className="status error">{error}</p>}
      {result && (
        <div className="panel">
          <h2>
            {result.left_name} vs {result.right_name}
          </h2>
          <p className="muted">
            {result.matches} matches · {result.differences} differences
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Left</th>
                <th>Right</th>
              </tr>
            </thead>
            <tbody>
              {result.fields.map((field) => (
                <tr
                  key={field.field}
                  className={field.equal ? undefined : 'diff-row unequal'}
                >
                  <td>{field.field}</td>
                  <td>{String(field.left ?? '—')}</td>
                  <td>{String(field.right ?? '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

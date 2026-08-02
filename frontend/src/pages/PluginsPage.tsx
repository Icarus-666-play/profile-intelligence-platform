import { useEffect, useState } from 'react'
import { api, type PluginInfo } from '../api'

export default function PluginsPage() {
  const [items, setItems] = useState<PluginInfo[]>([])
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    setError(null)
    const result = await api.plugins()
    setItems(result.items)
  }

  useEffect(() => {
    let cancelled = false
    load().catch((err: Error) => {
      if (!cancelled) setError(err.message)
    })
    return () => {
      cancelled = true
    }
  }, [])

  async function reload() {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.reloadPlugins()
      setItems(result.items)
      setMessage(`Reloaded ${result.reloaded} plugin(s)`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h1 className="page-title">Plugins</h1>
      <p className="page-lead">Discovered importer plugins from the registry.</p>
      <div className="form-row">
        <button type="button" className="secondary" onClick={reload} disabled={busy}>
          {busy ? 'Reloading…' : 'Reload plugins'}
        </button>
      </div>
      {error && <p className="status error">{error}</p>}
      {message && <p className="status">{message}</p>}
      <div className="panel">
        <h2>Installed</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Extensions</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {items.map((plugin) => (
              <tr key={plugin.name}>
                <td>{plugin.name}</td>
                <td>{plugin.supported_extensions.join(', ') || '—'}</td>
                <td>{plugin.description || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

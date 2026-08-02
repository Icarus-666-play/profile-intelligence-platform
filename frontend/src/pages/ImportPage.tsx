import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  api,
  type ImportActivity,
  type ImportPreview,
  type ImportSummary,
} from '../api'
import ProfilePreviewCard from '../components/ProfilePreviewCard'

type PanelKey = 'recent' | 'queue' | 'progress' | 'errors' | 'completed'

const PANELS: { key: PanelKey; label: string }[] = [
  { key: 'recent', label: 'Recent URLs' },
  { key: 'queue', label: 'Import Queue' },
  { key: 'progress', label: 'Progress' },
  { key: 'errors', label: 'Errors' },
  { key: 'completed', label: 'Completed' },
]

export default function ImportPage() {
  const [url, setUrl] = useState('https://')
  const [plugin, setPlugin] = useState('')
  const [source, setSource] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [lastImport, setLastImport] = useState<ImportSummary | null>(null)
  const [activity, setActivity] = useState<ImportActivity | null>(null)
  const [panel, setPanel] = useState<PanelKey>('recent')

  const refreshActivity = useCallback(async () => {
    try {
      setActivity(await api.importActivity())
    } catch {
      // panel refresh is best-effort
    }
  }, [])

  useEffect(() => {
    void refreshActivity()
    const timer = window.setInterval(() => {
      void refreshActivity()
    }, 4000)
    return () => window.clearInterval(timer)
  }, [refreshActivity])

  async function runPreview(event?: FormEvent) {
    event?.preventDefault()
    setBusy(true)
    setError(null)
    setLastImport(null)
    try {
      const result = await api.previewUrl({
        url: url.trim(),
        plugin: plugin.trim() || undefined,
        source: source.trim() || undefined,
      })
      setPreview(result)
      setPanel('progress')
      await refreshActivity()
      setPanel('recent')
    } catch (err) {
      setPreview(null)
      setError(err instanceof Error ? err.message : String(err))
      setPanel('errors')
      await refreshActivity()
    } finally {
      setBusy(false)
    }
  }

  async function runImport(event?: FormEvent) {
    event?.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const result = await api.importUrl({
        url: url.trim(),
        plugin: plugin.trim() || undefined,
        source: source.trim() || undefined,
      })
      setLastImport(result)
      setPreview(null)
      setPanel('completed')
      await refreshActivity()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setPanel('errors')
      await refreshActivity()
    } finally {
      setBusy(false)
    }
  }

  function cancelPreview() {
    setPreview(null)
    setError(null)
  }

  const focusProfile = useMemo(() => {
    if (!preview?.rows?.length) return null
    return (
      preview.rows.find((row) => row.status === 'ok' || row.status === 'update') ||
      preview.rows[0]
    )
  }, [preview])

  return (
    <section>
      <h1 className="page-title">Import</h1>
      <p className="page-lead">
        Paste a URL, preview the extract, then import into SQLite.
      </p>

      <div className="panel import-url-panel">
        <h2>URL</h2>
        <form
          className="import-url-form"
          onSubmit={(event) => {
            void runImport(event)
          }}
        >
          <label className="import-url-label">
            URL
            <input
              className="import-url-input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://"
              inputMode="url"
              required
            />
          </label>
          <div className="form-row import-url-options">
            <label>
              Plugin
              <input
                value={plugin}
                onChange={(e) => setPlugin(e.target.value)}
                placeholder="auto"
              />
            </label>
            <label>
              Source
              <input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="optional"
              />
            </label>
          </div>
          <div className="import-url-actions">
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => {
                void runPreview()
              }}
            >
              {busy ? 'Working…' : 'Preview'}
            </button>
            <button type="submit" disabled={busy}>
              {busy ? 'Working…' : 'Import'}
            </button>
          </div>
        </form>
      </div>

      {error && <p className="status error">{error}</p>}

      {preview && focusProfile && (
        <div className="panel profile-preview-panel">
          <p className="muted">
            {preview.plugin} · {preview.records_read} read ·{' '}
            {preview.accepted_count} accepted · {preview.rejected_count} rejected
          </p>
          <ProfilePreviewCard
            profile={focusProfile}
            busy={busy}
            onImport={() => {
              void runImport()
            }}
            onCancel={cancelPreview}
          />
          {preview.rows.length > 1 && (
            <details className="preview-more">
              <summary>{preview.rows.length - 1} more row(s)</summary>
              <table className="table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.slice(1, 20).map((row) => (
                    <tr key={row.index}>
                      <td>{row.index}</td>
                      <td>{row.display_name || '—'}</td>
                      <td>{row.status}</td>
                      <td>{row.score ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}
        </div>
      )}

      {preview && !focusProfile && (
        <div className="panel">
          <h2>Preview</h2>
          <p className="muted">No profile rows to show.</p>
          <div className="import-url-actions">
            <button type="button" className="secondary" onClick={cancelPreview}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {lastImport && (
        <div className="panel">
          <h2>Last import</h2>
          <p>
            {lastImport.success ? 'Success' : 'Finished with issues'} · created{' '}
            {lastImport.created} · updated {lastImport.updated} · skipped{' '}
            {lastImport.skipped}
          </p>
        </div>
      )}

      <hr className="import-divider" />

      <div className="dash-panels">
        <div className="dash-tabs" role="tablist" aria-label="Import activity">
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
          {panel === 'recent' && (
            <>
              <h2>Recent URLs</h2>
              <table className="table">
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>When</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {(activity?.recent_urls.length ?? 0) === 0 && (
                    <tr>
                      <td colSpan={3} className="muted">
                        No recent URLs yet.
                      </td>
                    </tr>
                  )}
                  {activity?.recent_urls.map((item) => (
                    <tr key={`${item.url}-${item.at}`}>
                      <td className="url-cell">{item.url}</td>
                      <td>{item.at}</td>
                      <td>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setUrl(item.url)}
                        >
                          Use
                        </button>
                      </td>
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
                  {(activity?.import_queue.length ?? 0) === 0 && (
                    <tr>
                      <td colSpan={3} className="muted">
                        Inbox is clear — no new files waiting.
                      </td>
                    </tr>
                  )}
                  {activity?.import_queue.map((item) => (
                    <tr key={item.path}>
                      <td>{item.name}</td>
                      <td className="muted">{item.path}</td>
                      <td>{item.file_size.toLocaleString('en-US')} B</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {panel === 'progress' && (
            <>
              <h2>Progress</h2>
              {!activity?.progress && (
                <p className="muted">No import in progress.</p>
              )}
              {activity?.progress && (
                <div className="progress-block">
                  <p>
                    <strong>{activity.progress.stage}</strong> —{' '}
                    {activity.progress.message}
                  </p>
                  <p className="url-cell muted">{activity.progress.url}</p>
                  <div className="progress-bar" aria-hidden="true">
                    <span style={{ width: `${activity.progress.percent}%` }} />
                  </div>
                  <p className="muted">{activity.progress.percent}%</p>
                </div>
              )}
            </>
          )}

          {panel === 'errors' && (
            <>
              <h2>Errors</h2>
              <table className="table">
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>Message</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  {(activity?.errors.length ?? 0) === 0 && (
                    <tr>
                      <td colSpan={3} className="muted">
                        No import errors recorded.
                      </td>
                    </tr>
                  )}
                  {activity?.errors.map((item) => (
                    <tr key={`${item.url}-${item.at}`}>
                      <td className="url-cell">{item.url}</td>
                      <td>{item.message}</td>
                      <td>{item.at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {panel === 'completed' && (
            <>
              <h2>Completed</h2>
              <table className="table">
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>Result</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  {(activity?.completed.length ?? 0) === 0 && (
                    <tr>
                      <td colSpan={3} className="muted">
                        No completed URL imports yet.
                      </td>
                    </tr>
                  )}
                  {activity?.completed.map((item) => (
                    <tr key={`${item.url}-${item.at}`}>
                      <td className="url-cell">{item.url}</td>
                      <td>
                        {item.success ? 'ok' : 'failed'}
                        {item.plugin ? ` · ${item.plugin}` : ''}
                        {` · +${item.created}/~${item.updated}`}
                      </td>
                      <td>{item.at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </section>
  )
}

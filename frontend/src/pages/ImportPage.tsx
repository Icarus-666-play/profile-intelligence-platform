import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  api,
  type ImportActivity,
  type ImportPreview,
  type ImportSummary,
} from '../api'
import ProfilePreviewCard from '../components/ProfilePreviewCard'
import UrlImportPipeline, {
  DEFAULT_LABELS,
  DEFAULT_PIPELINE,
} from '../components/UrlImportPipeline'
import { URL_LIST_PLACEHOLDER, parseUrlList } from '../urlList'

type PanelKey = 'recent' | 'queue' | 'progress' | 'errors' | 'completed'

const PANELS: { key: PanelKey; label: string }[] = [
  { key: 'recent', label: 'Recent URLs' },
  { key: 'queue', label: 'Import Queue' },
  { key: 'progress', label: 'Progress' },
  { key: 'errors', label: 'Errors' },
  { key: 'completed', label: 'Completed' },
]

export default function ImportPage() {
  const [urlsText, setUrlsText] = useState(URL_LIST_PLACEHOLDER)
  const [plugin, setPlugin] = useState('')
  const [source, setSource] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [previewBatch, setPreviewBatch] = useState<ImportPreview[]>([])
  const [lastImport, setLastImport] = useState<ImportSummary | null>(null)
  const [importBatch, setImportBatch] = useState<ImportSummary[]>([])
  const [batchErrors, setBatchErrors] = useState<string[]>([])
  const [activity, setActivity] = useState<ImportActivity | null>(null)
  const [panel, setPanel] = useState<PanelKey>('recent')
  const [activeStage, setActiveStage] = useState<string | null>(null)
  const [stagesRun, setStagesRun] = useState<string[]>([])

  const selectedUrls = useMemo(() => parseUrlList(urlsText), [urlsText])

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
    }, 1500)
    return () => window.clearInterval(timer)
  }, [refreshActivity])

  useEffect(() => {
    if (activity?.progress) {
      setActiveStage(activity.progress.stage)
      setStagesRun(activity.progress.stages_run ?? [])
    }
  }, [activity?.progress])

  async function runPreview(event?: FormEvent) {
    event?.preventDefault()
    const urls = parseUrlList(urlsText)
    if (!urls.length) {
      setError('Enter at least one URL (one per line).')
      return
    }
    setBusy(true)
    setError(null)
    setLastImport(null)
    setImportBatch([])
    setBatchErrors([])
    setActiveStage('url')
    setStagesRun(['url'])
    setPanel('progress')
    try {
      const result = await api.previewUrl({
        urls,
        plugin: plugin.trim() || undefined,
        source: source.trim() || undefined,
      })
      const batch = result.previews?.length ? result.previews : [result]
      setPreviewBatch(batch)
      setPreview(batch[0] ?? result)
      setBatchErrors(result.errors ?? [])
      setActiveStage(result.stage || 'preview')
      setStagesRun(
        result.stages_run?.length
          ? result.stages_run
          : [...DEFAULT_PIPELINE].slice(0, 8),
      )
      await refreshActivity()
    } catch (err) {
      setPreview(null)
      setPreviewBatch([])
      setError(err instanceof Error ? err.message : String(err))
      setPanel('errors')
      await refreshActivity()
    } finally {
      setBusy(false)
    }
  }

  async function runImport(event?: FormEvent) {
    event?.preventDefault()
    const urls = parseUrlList(urlsText)
    if (!urls.length) {
      setError('Enter at least one URL (one per line).')
      return
    }
    setBusy(true)
    setError(null)
    setActiveStage('url')
    setStagesRun(['url'])
    setPanel('progress')
    try {
      const result = await api.importUrl({
        urls,
        plugin: plugin.trim() || undefined,
        source: source.trim() || undefined,
      })
      const batch = result.imports?.length ? result.imports : [result]
      setImportBatch(batch)
      setLastImport(batch[batch.length - 1] ?? result)
      setBatchErrors(result.errors ?? [])
      setPreview(null)
      setPreviewBatch([])
      setActiveStage(result.stage || 'import')
      setStagesRun(
        result.stages_run?.length ? result.stages_run : [...DEFAULT_PIPELINE],
      )
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
    setPreviewBatch([])
    setError(null)
  }

  function useRecentUrl(next: string) {
    const existing = parseUrlList(urlsText)
    if (existing.includes(next)) {
      setUrlsText(existing.join('\n'))
      return
    }
    const lines = urlsText
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line && line !== 'https://...' && line !== 'http://...')
    const merged = [...existing, next]
    setUrlsText(merged.length ? merged.join('\n') : [...lines, next].join('\n'))
  }

  const focusProfile = useMemo(() => {
    if (!preview?.rows?.length) return null
    return (
      preview.rows.find((row) => row.status === 'ok' || row.status === 'update') ||
      preview.rows[0]
    )
  }, [preview])

  const pipeline = activity?.pipeline?.length
    ? activity.pipeline
    : [...DEFAULT_PIPELINE]
  const stageLabels = activity?.stage_labels ?? DEFAULT_LABELS
  const progressStage = activity?.progress?.stage || activeStage
  const progressStagesRun = activity?.progress?.stages_run?.length
    ? activity.progress.stages_run
    : stagesRun

  return (
    <section>
      <h1 className="page-title">Import</h1>
      <p className="page-lead">
        URL → Downloader → Snapshot → Parser → Extractor → Normalizer →
        Validator → Preview → Import
      </p>

      <div className="panel import-pipeline-panel">
        <h2>Pipeline</h2>
        <UrlImportPipeline
          pipeline={pipeline}
          labels={stageLabels}
          currentStage={progressStage}
          stagesRun={progressStagesRun}
        />
      </div>

      <div className="panel import-url-panel">
        <h2>URLs</h2>
        <p className="muted">One URL per line.</p>
        <form
          className="import-url-form"
          onSubmit={(event) => {
            void runImport(event)
          }}
        >
          <label className="import-url-label">
            URLs
            <textarea
              className="import-url-input import-url-list"
              value={urlsText}
              onChange={(e) => setUrlsText(e.target.value)}
              placeholder={URL_LIST_PLACEHOLDER}
              rows={5}
              spellCheck={false}
              required
            />
          </label>
          <p className="muted">
            {selectedUrls.length
              ? `${selectedUrls.length} URL${selectedUrls.length === 1 ? '' : 's'} ready`
              : 'Add real https:// links to continue'}
          </p>
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
              disabled={busy || selectedUrls.length === 0}
              onClick={() => {
                void runPreview()
              }}
            >
              {busy ? 'Working…' : 'Preview'}
            </button>
            <button type="submit" disabled={busy || selectedUrls.length === 0}>
              {busy
                ? 'Working…'
                : selectedUrls.length > 1
                  ? `Import ${selectedUrls.length} URLs`
                  : 'Import'}
            </button>
          </div>
        </form>
      </div>

      {error && <p className="status error">{error}</p>}
      {batchErrors.length > 0 && (
        <div className="status error">
          {batchErrors.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </div>
      )}

      {preview && focusProfile && (
        <div className="panel profile-preview-panel">
          <p className="muted">
            {preview.url ? `${preview.url} · ` : ''}
            {preview.plugin} · {preview.records_read} read ·{' '}
            {preview.accepted_count} accepted · {preview.rejected_count} rejected
            {previewBatch.length > 1
              ? ` · ${previewBatch.length} URL previews`
              : ''}
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
          {importBatch.length > 1 ? (
            <>
              <p className="muted">{importBatch.length} URLs processed</p>
              <table className="table">
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>Result</th>
                    <th>Created</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {importBatch.map((item) => (
                    <tr key={item.url || item.path}>
                      <td className="url-cell">{item.url || item.path}</td>
                      <td>{item.success ? 'ok' : 'issues'}</td>
                      <td>{item.created}</td>
                      <td>{item.updated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p>
              {lastImport.success ? 'Success' : 'Finished with issues'} · created{' '}
              {lastImport.created} · updated {lastImport.updated} · skipped{' '}
              {lastImport.skipped}
            </p>
          )}
        </div>
      )}

      {previewBatch.length > 1 && (
        <div className="panel">
          <h2>URL previews</h2>
          <table className="table">
            <thead>
              <tr>
                <th>URL</th>
                <th>Plugin</th>
                <th>Accepted</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {previewBatch.map((item) => (
                <tr key={item.url || item.path}>
                  <td className="url-cell">{item.url || item.path}</td>
                  <td>{item.plugin}</td>
                  <td>{item.accepted_count}</td>
                  <td>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => setPreview(item)}
                    >
                      Show
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
                          onClick={() => useRecentUrl(item.url)}
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
              <UrlImportPipeline
                pipeline={pipeline}
                labels={stageLabels}
                currentStage={progressStage}
                stagesRun={progressStagesRun}
              />
              {!activity?.progress && !busy && (
                <p className="muted">No import in progress.</p>
              )}
              {activity?.progress && (
                <div className="progress-block">
                  <p>
                    <strong>
                      {stageLabels[activity.progress.stage] ||
                        activity.progress.stage}
                    </strong>{' '}
                    — {activity.progress.message}
                  </p>
                  <p className="url-cell muted">{activity.progress.url}</p>
                  {activity.progress.snapshot && (
                    <p className="muted">
                      Snapshot:{' '}
                      <code>{activity.progress.snapshot.path}</code>
                      {activity.progress.snapshot.from_cache
                        ? ' (cached)'
                        : ''}
                    </p>
                  )}
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

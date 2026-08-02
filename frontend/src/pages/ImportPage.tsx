import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result || '')
      const comma = result.indexOf(',')
      resolve(comma >= 0 ? result.slice(comma + 1) : result)
    }
    reader.onerror = () => reject(reader.error || new Error('read failed'))
    reader.readAsDataURL(file)
  })
}

export default function ImportPage() {
  const [path, setPath] = useState('')
  const [url, setUrl] = useState('')
  const [plugin, setPlugin] = useState('')
  const [source, setSource] = useState('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function importPath(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.importFiles({
        paths: [path.trim()],
        plugin: plugin.trim() || undefined,
        source: source.trim() || undefined,
      })
      setMessage(
        `Imported ${result.count} batch(es)` +
          (result.errors.length ? `; errors: ${result.errors.join('; ')}` : ''),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function importUpload(event: FormEvent) {
    event.preventDefault()
    if (!files?.length) {
      setError('Choose at least one file')
      return
    }
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const encoded = await Promise.all(
        Array.from(files).map(async (file) => ({
          name: file.name,
          content_base64: await toBase64(file),
        })),
      )
      const result = await api.importFiles({
        files: encoded,
        plugin: plugin.trim() || undefined,
        source: source.trim() || undefined,
      })
      setMessage(
        `Uploaded ${result.count} batch(es)` +
          (result.errors.length ? `; errors: ${result.errors.join('; ')}` : ''),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function importRemote(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.importUrl({
        url: url.trim(),
        plugin: plugin.trim() || undefined,
        source: source.trim() || undefined,
      })
      setMessage(`URL import complete (${String(result.status || 'ok')})`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h1 className="page-title">Import</h1>
      <p className="page-lead">
        Send files through FastAPI into the application import pipeline.
      </p>
      {error && <p className="status error">{error}</p>}
      {message && <p className="status">{message}</p>}

      <div className="panel">
        <h2>Shared options</h2>
        <div className="form-row">
          <label>
            Plugin
            <input
              value={plugin}
              onChange={(e) => setPlugin(e.target.value)}
              placeholder="csv / excel / eurogirls…"
            />
          </label>
          <label>
            Source tag
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="optional"
            />
          </label>
        </div>
      </div>

      <div className="panel">
        <h2>Local path</h2>
        <form className="form-row" onSubmit={importPath}>
          <label>
            Path
            <input
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/data/inbox/profiles.csv"
              required
            />
          </label>
          <button type="submit" disabled={busy}>
            Import path
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Upload</h2>
        <form className="form-row" onSubmit={importUpload}>
          <label>
            Files
            <input
              type="file"
              multiple
              onChange={(e) => setFiles(e.target.files)}
            />
          </label>
          <button type="submit" disabled={busy}>
            Upload & import
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>URL</h2>
        <form className="form-row" onSubmit={importRemote}>
          <label>
            URL
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
              required
            />
          </label>
          <button type="submit" disabled={busy}>
            Download & import
          </button>
        </form>
      </div>
    </section>
  )
}

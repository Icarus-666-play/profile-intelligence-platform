import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, type PluginInfo, type SettingsSnapshot } from '../api'
import { THEMES, applyTheme, readTheme, type ThemeId } from '../theme'

const SECTIONS = [
  { id: 'theme', label: 'Theme' },
  { id: 'database', label: 'Database' },
  { id: 'plugins', label: 'Plugins' },
  { id: 'scoring', label: 'Scoring' },
  { id: 'import-folder', label: 'Import Folder' },
  { id: 'playwright', label: 'Playwright' },
  { id: 'backups', label: 'Backups' },
] as const

function SettingsSection({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: ReactNode
}) {
  return (
    <section id={id} className="panel settings-section">
      <h2 className="settings-section-title">{title}</h2>
      {children}
    </section>
  )
}

function Kv({ rows }: { rows: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="settings-kv">
      {rows.map((row) => (
        <div key={row.label}>
          <dt>{row.label}</dt>
          <dd>{row.value}</dd>
        </div>
      ))}
    </dl>
  )
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

export default function SettingsPage() {
  const [data, setData] = useState<SettingsSnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [theme, setTheme] = useState<ThemeId>(() => readTheme())
  const [backupBusy, setBackupBusy] = useState(false)
  const [backupMessage, setBackupMessage] = useState<string | null>(null)
  const [reloadBusy, setReloadBusy] = useState(false)

  async function loadSettings() {
    const payload = await api.settings()
    setData(payload)
  }

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    let cancelled = false
    loadSettings()
      .catch((err: Error) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function onCreateBackup() {
    setBackupBusy(true)
    setBackupMessage(null)
    try {
      const result = await api.createBackup()
      setBackupMessage(`Created ${result.backup.name}`)
      await loadSettings()
    } catch (err) {
      setBackupMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBackupBusy(false)
    }
  }

  async function onReloadPlugins() {
    setReloadBusy(true)
    try {
      await api.reloadPlugins()
      await loadSettings()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setReloadBusy(false)
    }
  }

  const plugins = (data?.plugins.items ?? []) as PluginInfo[]

  return (
    <section className="settings-page">
      <h1 className="page-title">Settings</h1>
      <p className="page-lead">
        Local configuration snapshot. Edit YAML under <code>config/</code> for
        durable changes, then restart <code>pip-app ui</code>.
      </p>
      {error && <p className="status error">{error}</p>}
      {!data && !error && <p className="muted">Loading settings…</p>}
      {data && (
        <>
          <nav className="report-jump" aria-label="Settings sections">
            {SECTIONS.map((section) => (
              <a key={section.id} href={`#${section.id}`}>
                {section.label}
              </a>
            ))}
          </nav>

          <div className="report-sections">
            <SettingsSection id="theme" title="Theme">
              <p className="muted">{data.theme.note}</p>
              <div className="theme-options">
                {THEMES.map((item) => (
                  <label
                    key={item.id}
                    className={
                      theme === item.id
                        ? 'theme-option active'
                        : 'theme-option'
                    }
                  >
                    <input
                      type="radio"
                      name="theme"
                      value={item.id}
                      checked={theme === item.id}
                      onChange={() => setTheme(item.id)}
                    />
                    <span>
                      <strong>{item.label}</strong>
                      <span className="muted">{item.note}</span>
                    </span>
                  </label>
                ))}
              </div>
            </SettingsSection>

            <SettingsSection id="database" title="Database">
              <Kv
                rows={[
                  { label: 'Driver', value: data.database.driver },
                  {
                    label: 'Path',
                    value: <code>{data.database.path}</code>,
                  },
                  {
                    label: 'URL',
                    value: data.database.url ? (
                      <code>{data.database.url}</code>
                    ) : (
                      '—'
                    ),
                  },
                  {
                    label: 'File present',
                    value: data.database.exists ? 'Yes' : 'No',
                  },
                  {
                    label: 'Echo SQL',
                    value: data.database.echo_sql ? 'On' : 'Off',
                  },
                  {
                    label: 'Timeout',
                    value: `${data.database.timeout_seconds}s`,
                  },
                  {
                    label: 'Foreign keys',
                    value: data.database.foreign_keys ? 'On' : 'Off',
                  },
                ]}
              />
            </SettingsSection>

            <SettingsSection id="plugins" title="Plugins">
              <Kv
                rows={[
                  {
                    label: 'Directory',
                    value: <code>{data.plugins.directory}</code>,
                  },
                  {
                    label: 'Auto discover',
                    value: data.plugins.auto_discover ? 'On' : 'Off',
                  },
                  {
                    label: 'Enabled allowlist',
                    value: data.plugins.enabled.length
                      ? data.plugins.enabled.join(', ')
                      : 'All discovered',
                  },
                  {
                    label: 'Loaded',
                    value: String(data.plugins.count ?? plugins.length),
                  },
                ]}
              />
              <div className="settings-actions">
                <button
                  type="button"
                  onClick={() => void onReloadPlugins()}
                  disabled={reloadBusy}
                >
                  {reloadBusy ? 'Reloading…' : 'Reload plugins'}
                </button>
                <Link to="/plugins">Open Plugins page</Link>
              </div>
              {plugins.length > 0 && (
                <ul className="settings-plugin-list">
                  {plugins.map((plugin) => (
                    <li key={plugin.name}>
                      <strong>{plugin.name}</strong>
                      <span className="muted">
                        {plugin.description || 'No description'}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </SettingsSection>

            <SettingsSection id="scoring" title="Scoring">
              <Kv
                rows={[
                  { label: 'Method', value: data.scoring.method },
                  { label: 'Max score', value: String(data.scoring.max_score) },
                  {
                    label: 'Daily rescore',
                    value: data.scoring.daily_rescore ? 'On' : 'Off',
                  },
                  {
                    label: 'Config',
                    value: <code>{data.scoring.config_file}</code>,
                  },
                ]}
              />
              <table className="table">
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.scoring.weights).map(([field, weight]) => (
                    <tr key={field}>
                      <td>{field}</td>
                      <td>{weight}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </SettingsSection>

            <SettingsSection id="import-folder" title="Import Folder">
              <Kv
                rows={[
                  {
                    label: 'Path',
                    value: <code>{data.import_folder.path}</code>,
                  },
                  {
                    label: 'Configured',
                    value: <code>{data.import_folder.configured}</code>,
                  },
                  {
                    label: 'Exists',
                    value: data.import_folder.exists ? 'Yes' : 'No',
                  },
                  {
                    label: 'Recursive',
                    value: data.import_folder.recursive ? 'On' : 'Off',
                  },
                  {
                    label: 'Excel path',
                    value: <code>{data.import_folder.excel_path}</code>,
                  },
                  {
                    label: 'Dashboard path',
                    value: <code>{data.import_folder.dashboard_path}</code>,
                  },
                ]}
              />
            </SettingsSection>

            <SettingsSection id="playwright" title="Playwright">
              <Kv
                rows={[
                  {
                    label: 'Package',
                    value: data.playwright.available
                      ? 'Installed'
                      : 'Not installed',
                  },
                  {
                    label: 'Pipeline',
                    value: data.playwright.enabled ? 'Enabled' : 'Not wired',
                  },
                  { label: 'Status', value: data.playwright.status },
                ]}
              />
              <p className="muted">{data.playwright.note}</p>
            </SettingsSection>

            <SettingsSection id="backups" title="Backups">
              <Kv
                rows={[
                  {
                    label: 'Directory',
                    value: <code>{data.backups.directory}</code>,
                  },
                  {
                    label: 'Log rotation copies',
                    value: String(data.backups.log_backup_count),
                  },
                ]}
              />
              <p className="muted">{data.backups.note}</p>
              <div className="settings-actions">
                <button
                  type="button"
                  onClick={() => void onCreateBackup()}
                  disabled={backupBusy}
                >
                  {backupBusy ? 'Creating…' : 'Create database backup'}
                </button>
              </div>
              {backupMessage && <p className="status">{backupMessage}</p>}
              {(data.backups.items ?? []).length === 0 ? (
                <p className="muted">No database backups yet.</p>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Size</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.backups.items.map((item) => (
                      <tr key={item.path}>
                        <td>
                          <code>{item.name}</code>
                        </td>
                        <td>{formatBytes(item.size_bytes)}</td>
                        <td>
                          {item.created_at
                            ? new Date(item.created_at).toLocaleString()
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </SettingsSection>
          </div>
        </>
      )}
    </section>
  )
}

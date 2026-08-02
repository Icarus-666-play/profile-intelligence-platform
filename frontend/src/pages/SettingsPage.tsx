export default function SettingsPage() {
  return (
    <section>
      <h1 className="page-title">Settings</h1>
      <p className="page-lead">
        Configuration is loaded from YAML under <code>config/</code> and
        environment overrides. Edit on disk and restart <code>pip-app ui</code>.
      </p>
      <div className="panel">
        <h2>Stack</h2>
        <p className="muted">
          Browser → React → REST API → FastAPI → Application Layer → Repository
          Layer → SQLite → File Storage
        </p>
        <ul>
          <li>
            Database: <code>data/pip.sqlite3</code>
          </li>
          <li>
            Media / files: <code>data/media</code>, <code>data/inbox</code>,{' '}
            <code>exports/</code>
          </li>
          <li>
            API docs: <a href="/api/docs">/api/docs</a>
          </li>
        </ul>
      </div>
    </section>
  )
}

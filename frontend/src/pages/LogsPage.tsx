export default function LogsPage() {
  return (
    <section>
      <h1 className="page-title">Logs</h1>
      <p className="page-lead">
        Application logs are written under <code>logs/</code> by the Python
        process. Tail them from a terminal while the UI runs.
      </p>
      <div className="panel">
        <h2>Where to look</h2>
        <ul>
          <li>
            <code>logs/pip.log</code> — rotating application log
          </li>
          <li>
            FastAPI / uvicorn console output from <code>pip-app ui</code>
          </li>
        </ul>
      </div>
    </section>
  )
}

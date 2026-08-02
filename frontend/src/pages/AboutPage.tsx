import { useEffect, useState } from 'react'
import { api } from '../api'

export default function AboutPage() {
  const [stack, setStack] = useState<string>('…')

  useEffect(() => {
    api
      .health()
      .then((health) => setStack(health.stack))
      .catch(() => setStack('unavailable'))
  }, [])

  return (
    <section>
      <h1 className="page-title">About</h1>
      <p className="page-lead">
        Profile Intelligence Platform — local-first desktop profile analysis.
      </p>
      <div className="panel">
        <h2>Presentation stack</h2>
        <p>
          Browser → React → REST API → FastAPI → Application Layer → Repository
          Layer → SQLite → File Storage
        </p>
        <p className="muted">
          API health stack: <strong>{stack}</strong>
        </p>
      </div>
    </section>
  )
}

import type { ReactNode } from 'react'
import type { ImportPreviewRow } from '../api'

type Props = {
  profile: ImportPreviewRow
  busy?: boolean
  onImport: () => void
  onCancel: () => void
}

function Field({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="profile-field">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function listOrDash(items: string[] | null | undefined) {
  if (!items?.length) return <span className="muted">—</span>
  return (
    <ul className="profile-chip-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

export default function ProfilePreviewCard({
  profile,
  busy = false,
  onImport,
  onCancel,
}: Props) {
  const gallery = profile.pictures?.length
    ? profile.pictures
    : profile.picture
      ? [profile.picture]
      : []

  return (
    <article className="profile-preview-card">
      <div className="profile-preview-hero">
        <div className="profile-picture">
          {profile.picture ? (
            <img src={profile.picture} alt={profile.display_name} />
          ) : (
            <div className="profile-picture-fallback" aria-hidden="true">
              {profile.display_name.slice(0, 1).toUpperCase() || '?'}
            </div>
          )}
        </div>
        <div className="profile-preview-identity">
          <p className="entry-kicker">Profile preview</p>
          <h2 className="profile-preview-name">{profile.display_name}</h2>
          <p className="muted">
            {[profile.location, profile.source, profile.status]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
      </div>

      <dl className="profile-fields">
        <Field label="Name">{profile.display_name || '—'}</Field>
        <Field label="Age">{profile.age || '—'}</Field>
        <Field label="Nationality">{profile.nationality || '—'}</Field>
        <Field label="Languages">{listOrDash(profile.languages)}</Field>
        <Field label="Services">{listOrDash(profile.services)}</Field>
        <Field label="Rates">{listOrDash(profile.rates)}</Field>
        <Field label="Reviews">{listOrDash(profile.reviews)}</Field>
        <Field label="Pictures">
          {gallery.length === 0 ? (
            <span className="muted">—</span>
          ) : (
            <div className="profile-gallery">
              {gallery.slice(0, 8).map((src) => (
                <a
                  key={src}
                  href={src}
                  target="_blank"
                  rel="noreferrer"
                  className="profile-gallery-item"
                >
                  <img src={src} alt="" />
                </a>
              ))}
            </div>
          )}
        </Field>
      </dl>

      <hr className="import-divider" />

      <div className="import-url-actions">
        <button type="button" disabled={busy} onClick={onImport}>
          {busy ? 'Importing…' : 'Import'}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </article>
  )
}

# Security

PIP is a **local-first desktop** application. Security posture assumes a trusted workstation operator, not a multi-tenant public server.

## Trust model

| Asset | Trust assumption |
|-------|------------------|
| Local SQLite / media / exports | Protected by OS user file permissions |
| Importer plugins | Trusted code loaded onto `sys.path` |
| Dashboard UI | Intended for loopback use by the same user |
| AI / remote media | Optional egress; off or constrained by config |

## Local UI / API binding

- Default bind: `127.0.0.1:8765`
- **No authentication** on UI or `/api` JSON routes
- Do **not** expose `--host 0.0.0.0` on untrusted networks
- `POST /api/import/url` respects `media.allow_remote_download`

If you bind beyond loopback, treat the UI/API as an open local admin console.

## Secrets & configuration

- Keep API keys and credentials in gitignored overlays:
  - `config/settings.local.yaml`
  - environment / `.env` (ignored)
- Never commit `api_key`, PEM/key files, or `credentials.json`
- AI settings (`ai.api_key`, `ai.base_url`) are only used when `ai.enabled: true`

Relevant ignore patterns: `.env`, `*.local.yaml`, `*.pem`, `*.key`, `secrets.yaml`, `credentials.json`, `data/`, `logs/`.

## Data at rest

- Default database: `data/pip.sqlite3`
- Media under `data/media/` (content-addressed)
- Logs under `logs/` may contain pathnames and import diagnostics — treat as sensitive

Back up and restrict ACLs on `data/` and `exports/` as appropriate for the host.

## Network egress

| Feature | Config | Risk |
|---------|--------|------|
| Remote image download | `media.allow_remote_download` | Fetches attacker-controlled URLs if present in imports |
| Remote/OpenAI AI | `ai.provider` + key | Sends prompts/profile text to third parties when enabled |
| Redis cache (future) | `cache.redis_url` | Network dependency |

Defaults keep AI **disabled**. Prefer leaving remote download enabled only when you trust source URLs.

## Plugin execution

Plugins are arbitrary Python. A malicious plugin has the same privileges as the PIP process.

Mitigations:

- Install only plugins you trust
- Use `importers.enabled` to allowlist names
- Review new packages under `plugins/` before running imports

## Database drivers

- SQLite: local file; protect filesystem
- PostgreSQL (optional): credentials live in `database.url` — store only in local overlays

## Logging hygiene

Avoid putting secrets into profile fields that will be logged or exported. Error logs capture exception text; do not log raw API keys.

## Recommendations checklist

1. Run UI on `127.0.0.1` only
2. Keep `ai.enabled: false` unless required
3. Use local YAML overlays for secrets
4. Allowlist importer plugins in production-like installs
5. Restrict OS permissions on `data/`, `logs/`, `exports/`
6. Disable `media.allow_remote_download` if imports should stay fully offline

## Related

- [DEPLOYMENT.md](DEPLOYMENT.md)
- [configuration.md](configuration.md)
- ADR: [0005-ai-off-by-default.md](ADR/0005-ai-off-by-default.md)

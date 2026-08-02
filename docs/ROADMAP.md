# Roadmap

Status summary for Profile Intelligence Platform. Detailed acceptance criteria also live in [milestones.md](milestones.md).

## Milestone status

| Milestone | Status | Summary |
|-----------|--------|---------|
| **M0 Foundation** | Complete | Config, logging, SQLite, DI, plugin framework, docs, tests |
| **M1 Core Pipeline** | Complete | Import → extract → search → score → Excel + CLI |
| **M2 Dashboard UI** | Complete | Local multi-page UI (`pip-app ui`) |
| **M3 AI Assist** | Planned | Live Local / Remote providers behind `IAIProvider` |

## Delivered capabilities (M0–M2)

- Plugin importers (CSV, Excel, webarchive, EuroGirls, NewWebsite scaffold, …)
- Confidence Score 0–100
- Search, compare, analysis toolkit
- Image pipeline (download → hash → duplicate → thumbnail → storage)
- Cache backends (Memory / File / SQLite; Redis stub)
- Daily automation with new-file ledger
- Dashboard UI navigation:

```
Profile Intelligence Platform
Dashboard
Search
Import
Compare
Reports
Settings
Plugins
Logs
About
```

## Milestone 3 — AI Assist (next)

```
AI
  Null (default when disabled)
  Local (future)
  Remote (future)
```

**Intent**
- Keep `ai.enabled: false` as the safe default
- Implement Local (e.g. Ollama-compatible) and Remote adapters for real completions
- Wire summarization (and optional classify/recommend assists) through `IAIProvider`

**Acceptance (planned)**
1. Enabling Local/Remote via YAML works without code changes in call sites
2. Null provider remains default
3. Failures surface as `AIError` without corrupting imports
4. Tests cover provider selection and disabled path

## Stretch themes (unscheduled)

| Theme | Notes |
|-------|-------|
| Email report send | Daily stage exists as stub |
| Redis cache | Interface stubbed |
| Stronger search | Fuzzy / FTS beyond current SQLite adapter |
| Auth-gated UI | Only if binding beyond loopback becomes a product need |
| Richer desktop shell | Optional native wrapper around the local UI |

## Documentation track

Product documentation set (this tree):

```
docs/
├── PRODUCT_VISION.md
├── PRODUCT_REQUIREMENTS.md
├── USER_STORIES.md
├── UI_WIREFRAMES.md
├── API_SPEC.md
├── DATABASE_ERD.md
├── PLUGIN_SDK.md
├── IMPORT_PIPELINE.md
├── SECURITY.md
├── DEPLOYMENT.md
├── ROADMAP.md
└── ADR/
```

## Related

- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md)
- [milestones.md](milestones.md)

# UI Wireframes

Local Dashboard UI launched with `pip-app ui` (default `http://127.0.0.1:8765/`).

Primary implementation: React SPA (`frontend/`) served by FastAPI. Legacy WSGI pages remain under `src/profile_intelligence/ui/` (`--legacy-wsgi`).

## Entry flow

```
Login (optional)
 ↓
Home
 ↓
Dashboard
```

| Step | Route | Notes |
|------|-------|-------|
| Login | `/login` | Optional; **Continue without login** → guest session |
| Home | `/` | Brand landing + CTA to Dashboard |
| Dashboard | `/dashboard` | Metrics overview (app shell) |

Auth API: `/api/auth/status|login|guest|logout|session`. Config: `auth:` in `settings.yaml`.

## Shell

```
┌──────────────┬────────────────────────────────────────────┐
│ Brand        │  Page title / hero                         │
│ PIP          │  Supporting sentence                       │
│              │                                            │
│ Dashboard    │  Page body                                 │
│ Search       │                                            │
│ Import       │                                            │
│ Compare      │                                            │
│ Reports      │                                            │
│ Settings     │                                            │
│ Plugins      │                                            │
│ Logs         │                                            │
│ About        │                                            │
│              │                                            │
│ vX.Y.Z       │                                            │
│ Local-first  │                                            │
└──────────────┴────────────────────────────────────────────┘
```

Navigation source of truth: `ui/navigation.py`.

## Pages

### Dashboard `/dashboard`

```
Dashboard — local overview…

Profiles   Imported Today   Countries   Average Price   Average Rating
  N              N              N            €NNN            N.NN

[ Latest Imports | Newest Profiles | Duplicates | Import Queue ]
  …table for active panel…
```

Data: `DashboardService.snapshot()` (+ rates/reviews/ledger/inbox).

### Search `/search`

```
Search
Find profiles in the local SQLite database.

[ query ________________________ ]  [ Search ]

Compare (0/2 selected)              [ Select two profiles ]

Results
  [Photo]  Name
           Age · Country · Languages · Rating · Average Price · Imported
           Compare ☑
```

Select up to two rows, then open Compare with `?left=&right=`.

### Import `/import`

```
Import

URL → Downloader → Snapshot → Parser → Extractor
  → Normalizer → Validator → Preview → Import
  …pipeline stepper…

URLs (one per line)
https://...
https://...
https://...
https://...

[ Preview ]   [ Import N URLs ]

Profile preview (after Preview)
  Picture
  Name
  Age
  Nationality
  Languages
  Services
  Rates
  Reviews
  Pictures
  ----------------------
  [ Import ]  [ Cancel ]

----------------------------

Recent URLs | Import Queue | Progress | Errors | Completed
  …table for active panel…
```

React primary surface. APIs: `POST /api/import/url[/preview]`, `GET /api/import/activity`.
Legacy WSGI page still exposes staged Input → Preview → Validate → Import for local paths.

### Compare `/compare`

```
Compare
Diff two stored profiles field by field.

Left id   [ 1 ]
Right id  [ 2 ]
[ Compare ]

Name A vs Name B
N difference(s), M match(es)

Field | Left | Right | Status
...
```

Accepts `?left=&right=` from Search compare selection and auto-runs.
POST → `CompareService.compare_ids`.

### Reports `/reports`

```
Reports
Countries, prices, languages, services, duplicates, and import trends…

Countries
  …distribution…

Average Prices
  …by duration…

Languages
  …distribution…

Services
  …distribution…

Duplicates
  …near-duplicate pairs…

Monthly Imports
  …12-month bars…

Import Trend
  …30-day bars…
```

React primary surface. Data: `GET /api/analytics` (`ReportsAnalyticsService`).
Excel exports remain via `pip-app export` (legacy WSGI Reports still exposes folder export).

### Settings `/settings`

```
Settings
Local configuration snapshot…

Theme
Database
Plugins
Scoring
Import Folder
Playwright
Backups
```

React primary surface. Data: `GET /api/settings`; backups via `GET/POST /api/backups`.
Theme is browser-local. YAML under `config/` remains the durable source.

### Plugins `/plugins`

```
Plugins
Importer plugins available…

plug  csv         description · .csv
plug  excel       …
plug  eurogirls   …
```

### Logs `/logs`

```
Logs
Recent lines from rotating log files.

application.log
┌─────────────────────────┐
│ tail of file            │
└─────────────────────────┘

import.log / errors.log …
```

### About `/about`

```
Profile Intelligence Platform

Product / Short name / Version / Runtime / CLI
```

## Interaction notes

- GET for all pages; POST for Import, Compare, Reports
- Static assets: `/static/styles.css`, `/static/app.js`
- No authentication (loopback-only by default) — see [SECURITY.md](SECURITY.md)
- Mobile: sidebar stacks above content under ~900px

## Related

- [USER_STORIES.md](USER_STORIES.md)
- [API_SPEC.md](API_SPEC.md) (routes + CLI)

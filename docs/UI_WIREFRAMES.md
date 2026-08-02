# UI Wireframes

Local Dashboard UI launched with `pip-app ui` (default `http://127.0.0.1:8765/`).

Implementation: `src/profile_intelligence/ui/` (WSGI app + HTML pages). This document describes the shipped information architecture, not a separate design-tool mock.

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

### Dashboard `/`

```
Profile Intelligence Platform          ← brand-level title
Dashboard — local overview…

PROFILES     SCORED     AVG CONFIDENCE
   N           N            NN.N

By source
  source-a · n   source-b · n

Top confidence
  #id  Name   source · confidence=NN

Needs attention
  #id  Name   source · confidence=NN
```

Data: `DashboardService.snapshot()`.

### Search `/search`

```
Search
Find profiles in the local SQLite database.

[ query ________________________ ]  [ Search ]

Results
  #id  Name   source · confidence=NN
```

### Import `/import`

```
Import
Staged operator flow for local files.

Input → Preview → Validate → Import     ← step indicator

Path        [ /path/to/file ________ ]
Source      [ optional _____________ ]
Plugin      [ Auto-detect ▼ ]
[ ] Recurse folders (Import stage)
[ Input ] [ Preview ] [ Validate ] [ Import ]

Preview table / Validate issues (when run)
```

POST `action=` → `ImportFlow` (`input` / `preview` / `validate` / `import`).

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

POST → `CompareService.compare_ids`.

### Reports `/reports`

```
Reports
Generate Excel workbooks…

[ Export Excel ]

Exports folder
  path/to/exports/
  file.xlsx · bytes
```

POST → `ProfileService.export_excel`.

### Settings `/settings`

```
Settings
Active local configuration (read-only).

App            …
Database       …
AI enabled     …
Cache backend  …
Daily paths    …
```

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

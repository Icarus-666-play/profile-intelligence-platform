# User Stories

Primary actor: **Operator** — a local user running PIP on their workstation.

## Epic: Import profiles

### US-I1 — Import a single file
**As an** operator  
**I want to** import a profile file from disk  
**So that** records are normalized and stored in SQLite.

**Acceptance**
- `pip-app import <path>` or UI Import with a local path succeeds
- Profiles appear in `pip-app list` / Dashboard
- Confidence scores are assigned when fields allow

### US-I1b — Staged import flow
**As an** operator  
**I want to** run Input → Preview → Validate → Import  
**So that** I can inspect rows before writing to the database.

**Acceptance**
- `--input` / `--preview` / `--validate` CLI stages work
- Preview does not persist profiles
- UI Import exposes the four stage actions

### US-I2 — Import an inbox folder
**As an** operator  
**I want to** process a folder of new files  
**So that** daily drops are ingested without re-importing old files.

**Acceptance**
- `pip-app daily` detects new files via `import_file_ledger`
- Only new/changed files are imported unless `--force-all-files`

### US-I3 — Choose an importer plugin
**As an** operator  
**I want to** force a plugin when auto-detect is ambiguous  
**So that** site-specific parsers run correctly.

**Acceptance**
- `--plugin eurogirls` / UI plugin select works
- `pip-app importers` lists discovered plugins

## Epic: Find and compare

### US-S1 — Search profiles
**As an** operator  
**I want to** search by name/email/org text  
**So that** I can locate records quickly.

**Acceptance**
- `pip-app search <query>` and UI `/search` return matches

### US-C1 — Compare two profiles
**As an** operator  
**I want to** diff two profile ids field-by-field  
**So that** I can spot duplicates or updates.

**Acceptance**
- `pip-app compare <id_a> <id_b>` and UI `/compare` show matches/diffs

### US-A1 — Analyze similarity / duplicates
**As an** operator  
**I want to** score similarity and find near-duplicates  
**So that** I can clean the database.

**Acceptance**
- `pip-app analyze similarity|duplicates|recommend|summarize|classify` produce results

## Epic: Report & operate

### US-R1 — Export Excel
**As an** operator  
**I want to** export profiles to `.xlsx`  
**So that** I can share offline reports.

**Acceptance**
- `pip-app export` / UI Reports writes under `exports/`

### US-D1 — View dashboard
**As an** operator  
**I want to** see totals, sources, and low-confidence profiles  
**So that** I know database health at a glance.

**Acceptance**
- `pip-app dashboard` prints a summary
- `pip-app ui` Dashboard page shows the same metrics live

### US-U1 — Use the Dashboard UI
**As an** operator  
**I want to** navigate Dashboard, Search, Import, Compare, Reports, Settings, Plugins, Logs, About  
**So that** I can operate without memorizing CLI flags.

**Acceptance**
- All nine nav destinations render
- Forms perform real local operations

### US-L1 — Inspect logs
**As an** operator  
**I want to** read recent application/import/error logs  
**So that** I can diagnose failed imports.

**Acceptance**
- UI Logs shows tails of `logs/*.log`

## Epic: Configure & extend

### US-X1 — Review settings
**As an** operator  
**I want to** see the active config snapshot  
**So that** I know which paths and AI/cache options are in effect.

**Acceptance**
- UI Settings shows read-only values from `AppConfig`

### US-X2 — Add a custom importer
**As a** developer  
**I want to** drop a plugin package under `plugins/`  
**So that** a new source format is supported without core changes.

**Acceptance**
- Plugin discovered on start when `importers.auto_discover: true`
- Documented in [PLUGIN_SDK.md](PLUGIN_SDK.md)

## Epic: AI assist (planned)

### US-AI1 — Optional AI summarization
**As an** operator  
**I want to** enable a Local or Remote AI provider later  
**So that** summaries can use models when I opt in.

**Acceptance (M3)**
- `ai.enabled: false` keeps Null provider
- Enabling Local/Remote does not require code changes outside config

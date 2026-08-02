# Import Pipeline

End-to-end path from a local file to SQLite (and optional media / daily automation).

## URL import flow (React Import page)

```
URL
 ↓
Downloader
 ↓
Snapshot
 ↓
Parser
 ↓
Extractor
 ↓
Normalizer
 ↓
Validator
 ↓
Preview
 ↓
Import
```

Constants: `domain/value_objects/url_import.py` (`URL_IMPORT_STAGES`).  
Progress is reported on `GET /api/import/activity` while Preview/Import run.

## Operator flow

Staged control surface for CLI / Dashboard UI (`ImportFlow`):

```
Input
 ↓
Preview
 ↓
Validate
 ↓
Import
```

| Stage | Meaning | CLI |
|-------|---------|-----|
| Input | Resolve path + plugin | `pip-app import PATH --input` |
| Preview | Dry-run rows (no DB write) | `pip-app import PATH --preview` |
| Validate | Gate on accepted/rejected rows | `pip-app import PATH --validate` |
| Import | Persist full pipeline | `pip-app import PATH` |

Implementation: `application/use_cases/import_flow.py`  
Value objects: `domain/value_objects/import_flow.py`

## Plugin ingest stages

Site plugins (EuroGirls, NewWebsite, …) implement:

```
Downloader
 ↓
Parser
 ↓
Extractor
 ↓
Normalizer
 ↓
Validator
 ↓
Importer
```

`DocumentDownloader` materializes URLs/files; `PluginPipeline` runs Parser→…→Validator and returns RawRecords for the Importer (`ProfileImporter.parse_profiles`).

## Platform transform stages

After the plugin Importer emits RawRecords:

```
File / RawDocument
 ↓
parser                 (resolve plugin + load records)
 ↓
normalizer             (RawRecord → ProfileDraft)
 ↓
validator
 ↓
duplicate_detector
 ↓
scorer                 (Confidence Score 0–100)
 ↓
repository             (upsert Profile + children)
 ↓
SQLite
```

Configured in `config/settings.yaml`:

```yaml
pipeline:
  - parser
  - normalizer
  - validator
  - duplicate_detector
  - scorer
  - repository
```

Defaults: `DEFAULT_PIPELINE_STAGES` in `core/config.py`.

## Code map

| Piece | Path |
|-------|------|
| Operator flow | `ImportFlow` (`application/use_cases/import_flow.py`) |
| Operator entry | `ImportService` (`application/use_cases/import_service.py`) |
| Pipeline facade | `ImportPipeline` (`application/use_cases/import_pipeline.py`) |
| Stage chain | `ProcessingChain` (`application/pipeline/chain.py`) |
| Stages | `application/pipeline/{parser,normalizer,validator,duplicate_detector,scorer,repository_stage}.py` |
| Plugin load | `ImporterRegistry` + `ProfileImporter` |
| Extract | `ProfileExtractor` → `ProfileDraft` |
| Persist | `IProfileRepository.upsert_draft` |

CLI: `pip-app import <path> [--plugin] [--source] [--recursive]`  
UI: Import page POST.

## Stage responsibilities

| Stage | Responsibility |
|-------|----------------|
| parser | Choose plugin, load `RawDocument` / raw records |
| normalizer | Header aliases → drafts / normalized rows |
| validator | Drop/flag invalid rows |
| duplicate_detector | Match existing profiles; decide create vs update |
| scorer | Confidence Score 0–100 |
| repository | Upsert aggregate to SQLite |

## Image pipeline (related)

When photos/URLs are present, media processing follows:

```
Image → Download → Hash → Duplicate Detection → Thumbnail → Storage
```

Implemented via `ImagePipeline` / `MediaPipeline` and `media_assets` / `profile_photos`.

## Daily automation pipeline

```
Daily
 ↓
Import Folder
 ↓
Detect new files      (import_file_ledger)
 ↓
Import
 ↓
Update                (optional rescore)
 ↓
Generate Excel
 ↓
Create Dashboard
 ↓
Email Report (future)
```

Entry: `pip-app daily` / `scripts/run_daily.py` → `DailyPipeline`.

Domain events published along the way:

```
ProfileImported → ScoreCalculated → ImagesExtracted → ExcelExported → DashboardUpdated
```

## Dedup & updates

- Duplicate detection compares incoming drafts to stored profiles (identity heuristics)
- Updates refresh fields rather than always inserting
- Daily ledger keys files by content hash so unchanged inbox files are skipped

## Import stats

Import summaries report created / updated / skipped counts (and richer child/image stats where available). CLI prints a human report; UI Import shows a status notice.

## Failure modes

- Missing plugin for extension → error / skip with message
- Invalid path → validation error
- Per-row issues accumulate in summary `errors` without always aborting the whole batch

## Related

- [PLUGIN_SDK.md](PLUGIN_SDK.md)
- [DATABASE_ERD.md](DATABASE_ERD.md)
- [architecture.md](architecture.md)

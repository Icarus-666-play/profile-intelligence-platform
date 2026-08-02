# Database

PIP persists data in a local **SQLite** database via **SQLAlchemy 2.x**.

## Connection layer

`profile_intelligence.infrastructure.database.connection.Database`:

- Creates the parent directory for the DB file
- Builds a SQLAlchemy engine (`sqlite:///<path>`)
- Enables foreign keys through a connect event
- Exposes transactional `session()` context manager

```python
from profile_intelligence.infrastructure.database import create_database
from profile_intelligence.core.config import load_config

config = load_config()
db = create_database(config)
with db.session() as session:
    ...
db.disconnect()
```

## Models

ORM models live under `infrastructure/database/`:

- `SchemaMigration` — applied migration ledger
- `Profile` — aggregate root
- `ProfileRate` / `ProfileService` / `ProfileReview` / `ProfilePhoto` / `ProfileAvailability` — child tables
- `MediaAsset` — content-addressed image metadata

Aggregate shape:

```
Profile
 ↓
Rate
 ↓
Service
 ↓
Review
 ↓
Photo
 ↓
Availability
```

## Repository pattern

`Repository[T]` defines `get_by_id`, `list_all`, `add`, and `delete`.

Domain ports (interfaces):

```
IProfileRepository
IRateRepository
IServiceRepository
IReviewRepository
IPhotoRepository
```

SQLite adapters:

| Port | Adapter |
|------|---------|
| `IProfileRepository` | `SQLiteRepository` |
| `IRateRepository` | `SQLiteRateRepository` |
| `IServiceRepository` | `SQLiteServiceRepository` |
| `IReviewRepository` | `SQLiteReviewRepository` |
| `IPhotoRepository` | `SQLitePhotoRepository` |

`SQLiteRepository.upsert_draft` upserts the parent and replaces child collections in one session (delegating to the child session helpers). `ProfileRepository` remains a compatibility alias for `SQLiteRepository`.

```
Domain ProfileDraft
 ↓
IProfileRepository  (SQLiteRepository)
 ↓
SQLite
```

## Package layout

```
src/profile_intelligence/infrastructure/database/
  connection.py              # engine + session management
  models.py                  # Base, Profile, MediaAsset
  models_profile_children.py # Rate / Service / Review / Photo / Availability
  repository.py              # SQLiteRepository (IProfileRepository)
  child_repositories.py      # Rate / Service / Review / Photo adapters
  migrate.py                 # migration framework + versions
  seed.py                    # demo data seeder
```

## Migrations

Defined in `database/migrate.py` (lightweight, no Alembic required):

1. Subclass `Migration` with `version`, `name`, and `up()`
2. Add the class to `ALL_MIGRATIONS`
3. Run via launcher or `run_migrations(database)`

Migrations are applied in version order inside a transaction and recorded in `schema_migrations`.

### Initial migration (`001_initial_schema`)

Creates:

- `schema_migrations`
- `profiles` (+ indexes on `display_name`, `source`)

### Enrichment migration (`002_enrich_profiles`)

Adds Milestone 1 columns:

- `email`, `phone`, `title`, `organization`, `location`, `tags`, `raw_json`
- indexes on `email` and `external_id`

### Media assets migration (`003_media_assets`)

Creates `media_assets` for content-addressed image storage.

### Profile children migration (`004_profile_children`)

Creates child tables owned by `profiles.id` (CASCADE delete):

- `profile_rates`
- `profile_services`
- `profile_reviews`
- `profile_photos`
- `profile_availability`

## Seeding

`database/seed.py` upserts built-in demo profiles (source=`seed`):

```python
from profile_intelligence.infrastructure.database import seed_database, SQLiteRepository

seed_database(SQLiteRepository(db), only_if_empty=True)
```

## CLI

```bash
python -m profile_intelligence migrate
python -m profile_intelligence seed
python -m profile_intelligence seed --only-if-empty
python scripts/migrate.py
```

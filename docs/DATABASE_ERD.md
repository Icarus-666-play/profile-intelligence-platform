# Database ERD

Default store: SQLite file `data/pip.sqlite3`.  
ORM: SQLAlchemy models under `src/profile_intelligence/infrastructure/database/`.  
Migrations: lightweight runners in `migrate.py` (versions `001`–`005`).

## Entity relationship (logical)

```
schema_migrations

profiles 1──* profile_rates
         1──* profile_services
         1──* profile_reviews
         1──* profile_photos
         1──* profile_availability

profiles  ?──* media_assets      (profile_id nullable, content-addressed)

import_file_ledger               (Daily detect-new-files; not FK-bound)
```

Aggregate narrative used in domain docs:

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

## Tables

### `schema_migrations`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| version | VARCHAR(64) UNIQUE | e.g. `001` |
| name | VARCHAR(255) | |
| applied_at | DATETIME | |

### `profiles`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| external_id | VARCHAR(255) | |
| display_name | VARCHAR(512) NOT NULL | |
| email | VARCHAR(320) | |
| phone | VARCHAR(64) | |
| title | VARCHAR(255) | |
| organization | VARCHAR(255) | |
| location | VARCHAR(255) | |
| tags | TEXT | |
| source | VARCHAR(128) | importer / site label |
| notes | TEXT | |
| raw_json | TEXT | |
| score | INTEGER | Confidence 0–100 |
| created_at / updated_at | DATETIME | |

### `profile_rates`

`profile_id` FK → `profiles.id` CASCADE  
Fields: `duration`, `price`, `currency`, `incall`, `outcall`  
Unique: `(profile_id, duration, incall, outcall)`

### `profile_services`

FK CASCADE · `name`, `available`  
Unique: `(profile_id, name)`

### `profile_reviews`

FK CASCADE · `text`, `author`, `rating`, `reviewed_at`, `source_url`

### `profile_photos`

FK CASCADE · `original_url`, `sha256`, `role`, `content_type`  
Unique: `(profile_id, original_url)`

### `profile_availability`

FK CASCADE · `day_of_week`, `start_time`, `end_time`, …  
Unique window constraint per profile

### `media_assets`

| Column | Notes |
|--------|-------|
| content_hash | UNIQUE content address |
| profile_id | optional link |
| storage_path / thumbnail_path | on-disk paths under media root |
| byte_size, width, height, content_type, extension | metadata |

### `import_file_ledger` (migration `005`)

| Column | Notes |
|--------|-------|
| path | inbox file path |
| content_hash | UNIQUE |
| file_size | |
| imported_at | |

Used by Daily **Detect new files**.

## Migrations

| Version | Name |
|---------|------|
| 001 | initial_schema |
| 002 | enrich_profiles |
| 003 | media_assets |
| 004 | profile_children |
| 005 | import_file_ledger |

Apply: `pip-app migrate` (also on application start).

## Repository ports

| Port | Adapter |
|------|---------|
| `IProfileRepository` | SQLite (+ optional PostgreSQL) |
| `IRateRepository` / `IServiceRepository` / `IReviewRepository` / `IPhotoRepository` | SQLite child repos |
| Image metadata | `ImageRepository` / `media_assets` |

## Related

- [database.md](database.md) (operational guide)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- ADR: [0002-lightweight-sql-migrations.md](ADR/0002-lightweight-sql-migrations.md)

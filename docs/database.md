# Database

PIP persists data in a local **SQLite** database via **SQLAlchemy 2.x**.

## Connection layer

`profile_intelligence.database.connection.Database`:

- Creates the parent directory for the DB file
- Builds a SQLAlchemy engine (`sqlite:///<path>`)
- Enables foreign keys through a connect event
- Exposes transactional `session()` context manager

```python
from profile_intelligence.database import create_database
from profile_intelligence.core.config import load_config

config = load_config()
db = create_database(config)
with db.session() as session:
    ...
db.disconnect()
```

## Models

ORM models live in `database/models.py`:

- `SchemaMigration` — applied migration ledger
- `Profile` — initial profile entity scaffold

## Repository pattern

`Repository[T]` defines `get_by_id`, `list_all`, `add`, and `delete`.

`ProfileRepository` is the first concrete implementation. Additional repositories should follow the same pattern and wrap persistence errors as `RepositoryError`.

## Package layout

```
src/profile_intelligence/database/
  connection.py   # engine + session management
  models.py       # SQLAlchemy ORM models
  repository.py   # repository pattern
  migrate.py      # migration framework + versions
  seed.py         # demo data seeder
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

## Seeding

`database/seed.py` upserts built-in demo profiles (source=`seed`):

```python
from profile_intelligence.database import seed_database, ProfileRepository

seed_database(ProfileRepository(db), only_if_empty=True)
```

## CLI

```bash
python -m profile_intelligence migrate
python -m profile_intelligence seed
python -m profile_intelligence seed --only-if-empty
python scripts/migrate.py
```

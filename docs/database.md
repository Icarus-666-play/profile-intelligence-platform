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

## Migrations

Custom lightweight framework (no Alembic required for the initial scaffold):

1. Subclass `Migration` with `version`, `name`, and `up()`
2. Add the class to `ALL_MIGRATIONS` in `database/migrations/versions/__init__.py`
3. Run via launcher (`--migrate-only`) or `MigrationRunner.migrate()`

Migrations are applied in version order inside a transaction and recorded in `schema_migrations`.

### Initial migration (`001_initial_schema`)

Creates:

- `schema_migrations`
- `profiles` (+ indexes on `display_name`, `source`)

## CLI

```bash
python -m profile_intelligence --migrate-only
python scripts/migrate.py
```

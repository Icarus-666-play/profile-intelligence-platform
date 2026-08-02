# Importer Plugin Framework

Importers convert external files into PIP records. The framework is plugin-based so new sources can be added without changing core orchestration.

## Interface

Subclass `ImporterPlugin`:

```python
from typing import Any, ClassVar
from profile_intelligence.importers import ImporterPlugin, ImportResult

class MyImporter(ImporterPlugin):
    name: ClassVar[str] = "my_source"
    description: ClassVar[str] = "Imports from my format"
    supported_extensions: ClassVar[tuple[str, ...]] = (".csv",)

    def can_handle(self, path) -> bool:
        return self.matches_extension(path)

    def import_file(self, path, **options: Any) -> ImportResult:
        self.validate_path(path)
        return ImportResult(success=True, records_read=0, records_imported=0)
```

## Discovery

`ImporterRegistry.discover()`:

1. Loads built-in modules under `profile_intelligence.importers.plugins`
2. Optionally loads `*.py` modules from the configured `plugins/` directory
3. Filters by `importers.enabled` when that list is non-empty

Built-in package is empty by design in this scaffold — add modules alongside `plugins/__init__.py`.

## Registration rules

- Concrete (non-abstract) subclasses of `ImporterPlugin` are instantiated
- Plugin `name` must be unique
- External modules should not start with `_`

## Runtime selection

```python
plugin = registry.find_handler("export.csv")
if plugin:
    result = plugin.import_file("export.csv")
```

## CLI

```bash
python -m profile_intelligence --list-importers
```

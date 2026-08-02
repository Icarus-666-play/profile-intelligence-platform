# External Importer Plugins

Drop site-specific or private importer packages here. PIP discovers them at
startup from `paths.plugins_dir` (default: this directory).

## Layout

```
plugins/
  eurogirls/     # Sprint 1 — Safari .webarchive importer (production)
  newwebsite/    # HTML/JSON importer (parser → extract → validate → normalize)
  eros/          # Eros directory export importer (scaffold)
  custom/        # Template for your own importers
```

### EuroGirls (Sprint 1)

```
eurogirls/
  plugin.py       # EuroGirlsImporter
  parser.py       # .webarchive → HTML
  extractor.py    # BeautifulSoup structured extract
  normalizer.py   # → platform RawRecord
  tests.py
```

### NewWebsite

```
newwebsite/
  plugin.py
  parser.py
  extractor.py
  normalizer.py
  validator.py
```

Each subdirectory is a Python package. Put an `ImporterPlugin` subclass in
`plugin.py` / `importer.py` (imported from `__init__.py`), or add top-level
`*.py` modules directly under `plugins/`.

## Discovery rules

1. Built-in plugins (`csv`, `excel`) load first
2. Top-level `plugins/*.py` modules load next
3. Each `plugins/<name>/` package is imported and scanned for plugin classes
4. `importers.enabled` in `settings.yaml` can restrict which names stay active

## Create a plugin

```python
from pathlib import Path
from typing import ClassVar
from profile_intelligence.infrastructure.importers import ProfileImporter

class MyImporter(ProfileImporter):
    name: ClassVar[str] = "my_source"
    description: ClassVar[str] = "My export format"
    supported_extensions: ClassVar[tuple[str, ...]] = (".json",)
    source_markers: ClassVar[tuple[str, ...]] = ("my_source",)
    require_source_marker: ClassVar[bool] = True

    def parse_profiles(self, path: Path, **options: object):
        return [{"name": "Ada"}], 0
```

See `custom/` for a ready-to-edit template.

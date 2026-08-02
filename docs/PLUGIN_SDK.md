# Plugin SDK

Guide for building importer plugins for Profile Intelligence Platform.

Also see the shorter operator guide: [importers.md](importers.md) and `plugins/README.md`.

## Concepts

An **importer plugin** turns a local file into raw profile row records (`RawRecord` dicts). The core pipeline then normalizes, validates, deduplicates, scores, and persists.

Prefer subclassing `ProfileImporter` from:

```python
from profile_intelligence.infrastructure.importers import ProfileImporter
# or domain port:
# from profile_intelligence.domain.interfaces.importers import ProfileImporter
```

## Minimal plugin

```python
from pathlib import Path
from typing import ClassVar

from profile_intelligence.infrastructure.importers import ProfileImporter


class MyImporter(ProfileImporter):
    name: ClassVar[str] = "mysite"
    description: ClassVar[str] = "My site profile files"
    supported_extensions: ClassVar[tuple[str, ...]] = (".html", ".json")
    source_markers: ClassVar[tuple[str, ...]] = ("mysite",)  # optional
    require_source_marker: ClassVar[bool] = False

    def parse_profiles(self, path: Path, **options: object):
        # Return (records, skipped_count) or ImportResult.failure(...)
        text = path.read_text(encoding="utf-8")
        record = {
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "source": self.name,
        }
        return [record], 0
```

`ProfileImporter` supplies `can_handle()`, `import_file()`, extension checks, and optional filename source markers.

## Package layout

External packages live under repository `plugins/<name>/`:

```
plugins/mysite/
  __init__.py
  plugin.py          # Importer class (required discovery entry)
  parser.py          # optional
  extractor.py       # optional
  normalizer.py      # optional
  validator.py       # optional
  tests.py           # pytest module (pythonpath includes plugins/)
```

Reference packages:

| Package | Role |
|---------|------|
| `plugins/eurogirls/` | Safari `.webarchive` site importer |
| `plugins/newwebsite/` | HTML/JSON scaffold (parser/extractor/normalizer/validator) |
| `plugins/eros/` | Scaffold |
| `plugins/custom/` | Template |

Built-ins (`csv`, `excel`, `webarchive`) ship inside `infrastructure/importers/plugins/`.

## Discovery order

`ImporterRegistry.discover()`:

1. Built-in plugins
2. `plugins/*.py` modules
3. `plugins/<package>/` packages
4. Optional filter via `importers.enabled` in settings

Config:

```yaml
importers:
  auto_discover: true
  enabled: []   # empty = all discovered
```

## Record shape & header aliases

Records are loosely keyed dicts. `ProfileExtractor` maps aliases → `ProfileDraft` fields (`display_name`, `email`, `phone`, `title`, `organization`, `location`, `tags`, `notes`, `external_id`, …).

Children may be attached when the plugin/normalizer provides structured rate/service/review/photo/availability data (see EuroGirls).

## CLI / UI usage

```bash
pip-app importers
pip-app import path/to/file --plugin mysite --source mysite
```

UI: Import page plugin dropdown.

## Testing

```bash
pytest plugins/mysite/tests.py
# or full suite — pythonpath includes plugins/
pytest
```

Tips:

- Prefer temp roots / fixtures from `tests/conftest.py` patterns
- Assert `can_handle` for extensions and negative cases
- Run one file through `ImportService` or `ImportPipeline` when integration matters

## Compatibility shim

Legacy imports under `profile_intelligence.importers` still resolve for older plugins; new code should use `infrastructure.importers` or domain ports.

## Related

- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- ADR: [0003-plugin-importer-registry.md](ADR/0003-plugin-importer-registry.md)

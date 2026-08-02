# ADR 0001 — Clean architecture layers

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

PIP needs a modular codebase that can grow importers, UI, AI, and storage adapters without entangling domain rules with frameworks.

## Decision

Organize the package as:

```
domain/          # entities, value objects, ports, events
application/     # use cases, pipeline stages, event bus
infrastructure/  # SQLAlchemy, importers, excel, media, UI-adjacent adapters
ui/              # presentation (Dashboard UI)
core/            # config, logging, DI, exceptions
bootstrap.py     # composition root
```

Dependencies point inward. `bootstrap.py` wires concrete adapters into the DI container.

## Consequences

- New features prefer ports + adapters over direct infrastructure calls from domain
- Compatibility shims may remain at legacy import paths for older plugins
- Slightly more boilerplate; clearer test seams

# ADR 0003 — Plugin importer registry

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

Profile sources vary by site and file format. Forking core for each source is unsustainable.

## Decision

Define `ImporterPlugin` / `ProfileImporter` ports and discover implementations via `ImporterRegistry`:

1. Built-in plugins in `infrastructure/importers/plugins/`
2. External modules/packages under repository `plugins/`
3. Optional allowlist `importers.enabled`

Plugins return raw records; the shared pipeline handles normalize → validate → dedupe → score → persist.

## Consequences

- New sources are additive packages (see [PLUGIN_SDK.md](../PLUGIN_SDK.md))
- Plugins are trusted local code (security implications documented)
- Discovery failures are isolatable per plugin

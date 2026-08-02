# ADR 0005 — AI off by default (Null provider)

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

PIP is AI-ready but local-first. Shipping with remote model calls enabled would surprise operators and risk leaking profile text.

## Decision

Introduce `IAIProvider` with:

```
AI
  Null (default when disabled)
  Local (future)
  Remote (future)
```

Factory `create_ai_provider` returns `NullAIProvider` when `ai.enabled: false`. Local/Remote remain stubs until Milestone 3.

## Consequences

- Imports and core flows never require network AI
- Call sites depend on the port, not a vendor SDK
- Enabling AI is an explicit config change (see [SECURITY.md](../SECURITY.md))

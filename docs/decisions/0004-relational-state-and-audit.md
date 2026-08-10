# ADR 0004: Relational current state and append-only audit

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

Persist normalized current state and an immutable, attributable audit history in one relational transaction. Do not use event sourcing. State mutations and audit append either commit together or roll back together.

Use entity versions, command correlation/causation IDs, unique idempotency keys, and explicit named transitions. Audit read access is permission-filtered, and application APIs expose no audit update/delete.

## Consequences

Current queries remain direct while history is durable. Full temporal reconstruction is limited to recorded event detail. Operational logs are separate and redacted.

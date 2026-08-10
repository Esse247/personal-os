# Handoff

## Current state

Foundation v0.1 remains complete and independently accepted for a localhost, mock-only, synthetic-data demonstration. Post-acceptance operating hardening is recorded by quality run `qg-20260810-operating-rules-run-001`; all authoritative records and checklists are reconciled. No capability is live.

## Exact next task

Establish PostgreSQL-first CI that applies every migration from zero, loads deterministic fixtures, and runs the persistence/concurrency integration suite against PostgreSQL.

## Read first

`AGENTS.md`, `PROJECT_MANIFEST.yaml`, `docs/BUILD_STATUS.md`, `docs/ARCHITECTURE.md`, accepted ADRs including ADR 0011, `quality/README.md`, `docs/SECURITY_PRIVACY_THREAT_MODEL.md`, `docs/EVIDENCE.md`, and `checklists/FOUNDATION_V0_1.md`.

## Guardrails

Keep provider mode mock-only and data synthetic. Do not add production identity, a live provider, real credentials/data, or external actions while closing the PostgreSQL evidence gap. Preserve immutable migrations and the SQLite local-development path. Define a success contract and invoke the quality gauntlet before claiming that next meaningful milestone complete.

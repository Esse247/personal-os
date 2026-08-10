# Architecture

## Decision summary

Foundation v0.1 is a modular monolith in a monorepo:

- `frontend/`: React, strict TypeScript, Vite, responsive dashboard.
- `backend/`: FastAPI, Pydantic contracts, SQLAlchemy persistence, Alembic migrations.
- local SQLite by default for a zero-service demonstration; PostgreSQL is the target-compatible Compose database.
- API and worker are separate composition boundaries over the same application and domain modules.
- relational current state plus append-only audit events; not event sourcing.

See accepted ADRs in `docs/decisions/` for rationale and consequences.

## Dependency rule

Dependencies point inward:

1. Domain — entities, value objects, transitions, invariants; no framework imports.
2. Application — typed commands/queries and orchestration; depends on domain and ports.
3. Ports — repository, clock, ID, provider, policy, audit, and job contracts.
4. Adapters — SQL persistence, mock providers, system clock, deterministic classifiers.
5. API/interface — HTTP schemas, identity fixture, response projection.
6. Worker — bounded jobs using the same application services and policy checks.
7. Persistence — module-owned mappings and migrations.
8. Observability — redacted structured operational logs and correlation IDs.

FastAPI, SQLAlchemy, provider SDKs, and environment configuration must not be imported by domain code. Provider-specific types must not cross a port.

## Bounded modules

Implemented vertical-slice modules are identity/access, capture, planning/commitments, scheduling, approvals, finance/house projects, audit, integrations/capabilities, and dashboard projection. Knowledge, notifications, agency, wellbeing, and remaining broad entities are contract/state definitions only in this phase.

Cross-module coordination uses typed IDs, commands, queries, and events. There are no generic repository or generic status-patch endpoints.

## Command pipeline

`untrusted input -> typed draft -> schema validation -> authorization -> domain command -> invariant checks -> persistence + audit`

Model/provider output is untrusted input. A mutation and its audit event share one database transaction. Commands use correlation IDs and durable request-digest receipts: an exact retry replays stored result references, while changed-content key reuse conflicts. Approval decisions use database compare-and-swap entity versions; material changes supersede earlier proposals.

## Runtime topology

- Browser communicates with `/v1` HTTP endpoints.
- API is localhost-bound by default and composes only mock providers in v0.1.
- The worker boundary exists as a separate entry point; the demo may execute deterministic jobs inline while preserving the port.
- PostgreSQL can be selected through an explicit database URL in Compose. Unknown or live provider modes fail startup.
- No Redis, broker, microservice, production model, or provider network dependency is introduced.

## Reliability and data rules

- UTC storage; user IANA timezone at presentation/scheduling boundaries.
- Half-open time intervals `[start, end)`.
- Integer minor units plus ISO currency for money; never binary float.
- Optimistic entity versions and unique idempotency keys.
- Confirmed blocks are planning inputs; approval rechecks overlap, and persistent commitment/exact-interval uniqueness guards concurrent duplicate confirmation.
- Append-only authoritative audit records; logs are not audit history.
- Mock adapters are deterministic and return provenance-bearing canonical responses.
- Frontend output-encodes captured/provider text and does not cache sensitive API responses.

## Enforcement

Architecture tests scan imports and contracts. Provider contract tests exercise substitution. Permission, approval, audit, provenance, and state-machine tests gate release. Capability registry, API, and UI must agree that v0.1 is mock/synthetic only.

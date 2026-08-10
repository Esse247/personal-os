# Architecture

## Decision summary

Foundation v0.1 is a modular monolith in a monorepo:

- `frontend/`: React, strict TypeScript, Vite, responsive dashboard.
- `backend/`: FastAPI, Pydantic contracts, SQLAlchemy persistence, Alembic migrations.
- local SQLite by default for a zero-service demonstration; PostgreSQL 17 is the v0.2
  production-semantic reference and the Compose/CI database.
- API and worker are separate composition boundaries over the same application and domain modules.
- relational current state plus append-only audit and outbox-transition history; not event sourcing.

See accepted ADRs in `docs/decisions/` for rationale and consequences.

## Long-term organisational architecture

The modular monolith is the initial substrate for a private AI organisation, not a
single-chat assistant or cognitive simulation. One permission-controlled world model feeds
typed specialist contracts. Specialists produce bounded observations, candidate insights,
proposals, and verification evidence. A Chief of Staff application layer performs
cross-domain executive synthesis and attention prioritisation. Deterministic policy and
approval services—not a model or executive agent—remain the authority boundary.

Coordination is event-driven: meaningful authorised signals and state transitions may
create candidate work. There is no fixed-frequency thought generator, recursive
self-enqueue loop, or requirement for continuous model calls. Future execution follows:

`event -> candidate insight -> specialist assessment -> executive synthesis -> gated action -> verification -> learning evidence`

The v0.2 transactional outbox carries only a finite redacted internal event catalog. Its
envelope includes the ownership, data-subject, actor, sensitivity, provenance linkage, and
correlation needed for future candidate-insight and executive contracts, without
implementing those specialists or granting new capability now.

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

Implemented vertical-slice modules are identity/access, capture, planning/commitments,
scheduling, approvals, finance/house projects, audit, integrations/capabilities, dashboard
projection, and the bounded persistence/execution substrate. Knowledge, candidate insight,
executive synthesis, notifications, agency, wellbeing, outcome learning, and remaining
broad entities are contract/state definitions only in this phase.

Cross-module coordination uses typed IDs, commands, queries, and events. There are no generic repository or generic status-patch endpoints.

## Command pipeline

`untrusted input/event -> typed draft/candidate -> schema validation -> authorization -> domain command -> invariant checks -> persistence + audit + canonical outbox event`

Model/provider output is untrusted input. A mutation and its audit event share one database transaction. Commands use correlation IDs and durable request-digest receipts: an exact retry replays stored result references, while changed-content key reuse conflicts. Approval decisions use database compare-and-swap entity versions; material changes supersede earlier proposals.

In v0.2, a consequential command's authoritative mutation, audit, receipt/approval, and
finite redacted outbox event share that transaction. The application explicitly enqueues
through a provider-neutral port; persistence never invents an event by inspecting ORM
changes. Internal delivery commits its unique consumer receipt, one internal effect,
delivery audit, delivered state, and immutable transition history atomically.
Operator status/failed-work queries cross the central owner-scoped read policy. Recovery
crosses the separate recovery policy as a typed, correlated, idempotency-digested command;
its redacted response snapshot is durable and exact-replayable only after a current policy
decision immediately before receipt read/result disclosure.

## Runtime topology

- Browser communicates with `/v1` HTTP endpoints.
- API is localhost-bound by default and composes only mock providers in v0.1.
- The worker boundary exists as a separate entry point. v0.2 permits only an allowlisted,
  policy-rechecked, local internal projection with bounded retry and fenced leases; it is
  not a general autonomous-agent runner.
- PostgreSQL can be selected through an explicit local synthetic database URL. Alembic is
  its only bootstrap, and startup fails closed if its revision is not the runtime head.
  Unknown or live provider modes fail startup.
- No Redis, broker, microservice, production model, or provider network dependency is introduced.

## Reliability and data rules

- UTC storage; user IANA timezone at presentation/scheduling boundaries.
- Half-open time intervals `[start, end)`.
- Integer minor units plus ISO currency for money; never binary float.
- Optimistic entity versions and unique idempotency keys.
- PostgreSQL outbox claims use database time, `FOR UPDATE SKIP LOCKED`, short leases, and
  unguessable fencing tokens. Retry/failure/recovery is bounded, typed, visible, and
  append-only; SQLite exercises lightweight behavior but is not PostgreSQL evidence.
- Confirmed blocks are planning inputs; approval rechecks overlap, and persistent commitment/exact-interval uniqueness guards concurrent duplicate confirmation.
- Append-only authoritative audit records; logs are not audit history.
- Mock adapters are deterministic and return provenance-bearing canonical responses.
- Frontend output-encodes captured/provider text and does not cache sensitive API responses.

## Enforcement

Architecture tests scan imports and contracts. Provider contract tests exercise substitution. Permission, approval, audit, provenance, and state-machine tests gate release. Capability registry, API, and UI must agree that v0.1 is mock/synthetic only.

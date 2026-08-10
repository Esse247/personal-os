# ADR 0012: PostgreSQL production semantics and transactional outbox execution

- **Status:** Accepted for Persistence & Execution Foundation v0.2
- **Date:** 2026-08-10
- **Supersedes for production semantics:** ADR 0005

## Context

Foundation v0.1 deliberately used SQLite for a zero-service local demonstration while
reserving PostgreSQL as the durable target. SQLite did not prove PostgreSQL migrations,
locking, isolation, constraint errors, concurrency, or timestamp behavior. The worker
boundary also had no durable queue, retry, recovery, or duplicate-delivery mechanism.

The accepted v0.1 command, authorization, provenance, approval, idempotency, and audit
invariants remain binding. This decision changes the persistence and execution substrate,
not product authority or provider capability.

## Decision

1. PostgreSQL 17 is the production-semantic reference database. Every persistence,
   transaction, concurrency, and execution claim must run against a real PostgreSQL
   instance. SQLite remains an explicit lightweight local and unit/integration-test option
   but cannot supply PostgreSQL acceptance evidence.
2. Alembic is the only PostgreSQL schema bootstrap path. Verification creates a clean
   disposable database, upgrades every immutable revision from zero, reruns upgrade as a
   no-op, and loads deterministic fixtures twice. `Base.metadata.create_all` is restricted
   to the intentional SQLite convenience path.
3. Consequential application events use a relational transactional outbox. The
   authoritative mutation, append-only audit event, command receipt or approval, and
   canonical redacted outbox event commit or roll back in one unit of work.
4. Delivery is at-least-once. Idempotent consumer receipts make handler effects
   duplicate-tolerant; the system does not claim broker-level or universal exactly-once
   delivery.
5. PostgreSQL workers claim eligible rows with short leases and
   `SELECT ... FOR UPDATE SKIP LOCKED`. Claims, state transitions, and consumer receipts
   are protected by database constraints and conditional versions. Expired leases are
   reclaimable after a crash.
6. Retryable failures use deterministic bounded exponential backoff. Non-retryable or
   exhausted events enter visible `failed` state. Every claim, retry, delivery, terminal
   failure, and explicit operator recovery appends immutable attempt history. Recovery
   requires an actor and reason and starts a new bounded attempt cycle.
7. The v0.2 handler registry is allowlisted and internal-only. A central policy check runs
   before handling; outbox payloads contain canonical identifiers and redacted metadata,
   never credentials or unrestricted personal content. No Level 4/5 or live-provider
   action is registered.
8. CI provisions a real PostgreSQL service and invokes the same clean verification command
   used locally. Workflow presence or SQLite substitution is not proof of PostgreSQL
   success.

## Consequences

- New outbox, delivery-attempt, and consumer-receipt tables are introduced by an immutable
  migration.
- PostgreSQL-specific locking stays in the persistence adapter; domain and application
  ports remain dialect- and provider-neutral.
- Existing API and mock demonstration behavior remains unchanged.
- A database-backed outbox avoids a broker dependency in v0.2. A future broker may relay
  committed events but cannot weaken transactional or idempotency guarantees.
- Live integrations, external side effects, production identity, and real data remain out
  of scope and prohibited.

# ADR 0013: Canonical internal events and fenced execution authority

- **Status:** Accepted for Persistence & Execution Foundation v0.2
- **Date:** 2026-08-10
- **Refines:** ADR 0012

## Context

ADR 0012 selected a transactional relational outbox, but a queue table alone does not
define a safe application event contract or prevent a stale worker from completing work
after its lease has been reassigned. The accepted v0.1 authorization, provenance, audit,
idempotency, and mock-only boundaries must remain true on both sides of durable delivery.

## Decision

1. Application services enqueue only finite, versioned `InternalEventType` values through
   the unit-of-work `OutboxRepository` port. Persistence adapters do not infer events by
   inspecting ORM state or by copying arbitrary audit payloads.
2. Every canonical envelope contains event and schema version, aggregate type/id/version,
   owner/controller/data-subject scope, actor/on-behalf-of identity, sensitivity,
   correlation and causation identifiers, an aware UTC occurrence time, capability mode,
   and a deterministic unique producer key. Payload keys and scalar values are allowlisted,
   canonical JSON is size-bounded, and raw user text, credentials, tokens, unrestricted
   audit details, or provider payloads are prohibited.
3. The authoritative mutation, audit event, command receipt or approval, and outbox row
   share one application unit of work. A constraint failure rolls all of them back.
4. A claim uses database time and, on PostgreSQL, `FOR UPDATE SKIP LOCKED`. It assigns an
   unguessable fencing token, owner, expiry, cycle, and bounded attempt number. Delivery,
   retry, and terminal-failure updates condition on the current token, current owner,
   processing state, and an unexpired lease. An expired holder cannot record an effect.
5. For the v0.2 internal projection consumer, the unique consumer receipt, one durable
   internal effect, delivery audit, outbox delivered transition, and immutable transition
   history commit atomically. Delivery is at-least-once; uniqueness makes re-delivery
   harmless without claiming universal exactly-once processing.
6. Retry uses typed redacted failure codes and deterministic bounded backoff. Exhausted or
   non-retryable work becomes visibly `failed`. Recovery is a typed command with a named
   actor, bounded reason, correlation ID, unique idempotency key and request digest. Its
   event/cycle result is stored in the same transaction for exact replay; changed-content
   key reuse conflicts. Recovery starts a new attempt cycle and never edits prior history.
7. The server constructs worker identity, delegation, resource, sensitivity, purpose, and
   environment. It authorizes `outbox.event.handle.internal.own` after claim and again
   immediately before the durable effect. Owner-scoped execution reads use
   `outbox.event.read.internal.own`; human recovery uses
   `outbox.event.recover.internal.own`. Unknown handlers, permissions, environments, and
   external-action registrations fail closed and are audited where authority permits.
8. PostgreSQL acceptance tests must cover a populated accepted-v0.1-head upgrade, competing
   claims, partial schedule overlap, duplicate delivery, crash/lease recovery, stale fencing,
   retry exhaustion, authorization revocation, wrong-actor recovery, and atomic rollback.

## Consequences

- Outbox events, immutable transition history, consumer receipts, and internal effects are
  durable relational records with state and uniqueness constraints.
- The only v0.2 handler is a local, deterministic, redacted projection. It cannot call a
  provider, network endpoint, agent, email, bank, calendar, or other external side effect.
- SQLite can exercise deterministic application behavior, but it cannot provide the
  PostgreSQL locking, lease, migration, or concurrency acceptance evidence.
- The accepted Foundation v0.1 product behavior and capability statuses remain unchanged.

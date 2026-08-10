# Data and memory model

## Authoritative memory

The database stores current relational state plus append-only history. The LLM context is a disposable, permission-filtered view, never memory or authority. Operational logs are diagnostic and are not the audit ledger.

The long-term shared world model is one logical permission-controlled knowledge surface,
not a globally readable agent memory. Domain ownership, controller/data-subject scope,
sensitivity, consent, purpose, validity, and provenance are enforced before a specialist,
Chief of Staff synthesis, model, or tool receives a view.

Candidate insights, executive syntheses, expected-action evidence, outcome verifications,
and learning records are separate typed records. They reference source evidence rather than
copying unrestricted payloads, expire or supersede explicitly, and never become facts,
permissions, approvals, or completed actions merely because a model produced them.

## Provenance envelope

Every observation, intent, inference, prediction, fact, provider result, and classification preserves:

- `source_type`: `USER_STATED`, `TOOL_OBSERVED`, `SYSTEM_INFERRED`, or `SYSTEM_PREDICTED`;
- `source_identifier`: stable origin reference;
- `observed_at` and `recorded_at` in UTC;
- `valid_from` and optional `valid_until` where relevant;
- `confidence` in `[0, 1]`;
- `confirmation_status`: `unconfirmed`, `confirmed`, `disputed`, or `superseded`;
- `sensitivity`: `public`, `household_shared`, `personal`, `financial`, `health`, `identity`, `legal`, or `credential`;
- actor, data subject/controller, correlation ID, and optional supersession/input references.

The system rejects invalid confidence and validity ranges. Derived data inherits the highest input sensitivity. Confidence never grants authority.

## Truth and contradiction

Claims coexist with provenance. A later statement does not destructively replace an earlier one: it confirms, disputes, or supersedes it. The active projection selects usable claims by explicit rules while retaining history. Predictions are rendered as predictions and never as observed facts.

## Audit events

Audit records are append-only through application ports. Events cover successful, denied, rejected, changed, expired, failed, and retried actions. Minimum fields include event/time, actor/on-behalf-of, action, entity and version, correlation/causation IDs, policy result, approval/tool/agent references, capability mode, redacted payload/evidence, and outcome.

Application APIs provide no update or delete operation for audit events. Hash chaining may provide local tamper evidence but is not described as tamper-proof without an external anchor.

## Privacy and retention defaults

- Personal by default; explicit field/resource/purpose/time-scoped grants for sharing.
- Context assembly uses least data and rechecks permission at use time.
- No credentials or personal data in fixtures, examples, logs, or committed databases.
- Financial and approval responses use `Cache-Control: no-store`.
- Browser service workers must not cache sensitive API content.
- Concrete retention, deletion, export, and cryptographic-key policies are open for a later authenticated phase.

## Current persistence

SQLite is the zero-service local default. PostgreSQL 17 is the v0.2 production-semantic
reference and Alembic is its only bootstrap path. Consequential application mutations,
audit, command/approval evidence, and finite canonical redacted outbox events share a
transaction. Module-owned tables use opaque IDs and typed contracts rather than
cross-module ORM graph traversal. The outbox is event-driven plumbing for future selective
reasoning; it is not a continuous model-call scheduler.

Execution recovery receipts bind the owner, command type, canonical request digest,
outbox event ID, and a size-bounded redacted result snapshot. The event transition, audit,
and receipt commit together, so exact retries can replay without repeating recovery and
mutated key reuse cannot silently create another attempt cycle. The snapshot is disclosed
only after current recovery authorization; revocation produces a denial audit and a
non-enumerating response instead of a replay.

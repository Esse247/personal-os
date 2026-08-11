# Persistence & Execution Foundation v0.2 checklist

Status legend: `[x]` verified complete; `[ ]` incomplete; `[~]` blocked or deliberately
deferred with an explicit evidence-based rationale.

## Fixed gate and baseline

- [x] Accepted Foundation v0.1 tag and complete regression baseline recovered.
- [x] Pre-implementation Quality Gauntlet contract is fixed and SHA-256 bound.
- [x] Completed successor run 005 preserves run-004 lineage and resolves every carried or discovered stable failure key.
- [x] ADRs 0012 and 0013 fix PostgreSQL, event, authority, and delivery boundaries.

## PostgreSQL reference path

- [x] PostgreSQL is selected explicitly and never auto-bootstrapped with `create_all`.
- [x] A loopback PostgreSQL 17.10 disposable-database command has an execution result.
- [x] Fresh zero-to-0008, second no-op, and populated accepted-0005-to-0008 paths pass.
- [x] Two synthetic fixture loads remain deterministic and idempotent on PostgreSQL.
- [x] PostgreSQL atomic rollback scenarios pass.
- [x] PostgreSQL CAS, overlap, claim, fencing, expiry, and one-winner races pass.
- [x] PostgreSQL isolation, provenance, immutable audit, approval, and idempotency pass.
- [x] Dialect-boundary tests isolate SQLite from PostgreSQL acceptance semantics.

## Durable execution

- [x] Consequential mutations enqueue finite canonical redacted events transactionally.
- [x] PostgreSQL claims use `SKIP LOCKED`, database time, short leases, and fencing tokens.
- [x] Consumer receipts suppress duplicate handler effects in the tested canonical handler.
- [x] Bounded backoff, exhaustion, visible failure, restart, and stale fencing pass.
- [x] Transition history is observable and append-only on PostgreSQL.
- [x] Recovery is typed, correlated, digest-bound, durable, and mutation-conflicting.
- [x] Exact recovery replay reauthorizes after serialization and before result disclosure;
  allow-then-revoke local, PostgreSQL, and independent probes pass with denial audit.
- [x] Worker effects are reauthorized before the tested default effect and live handlers fail closed.
- [x] Claim/reclaim history is labeled preauthorization; later delivered history remains allowed.
- [x] Adversarial direct, mutable-input, and stateful-consumer handler outputs fail closed
  before effect or receipt persistence, with typed failed history and audit.
- [x] Recovery advisory-key and event-row locks each have a non-leaking 500 ms scoped
  timeout; real PostgreSQL proves prior-setting restoration, typed/audited contention,
  zero partial write, authorized retry, and wrong-actor non-disclosure.

## CI and regressions

- [x] A PostgreSQL 17 workflow invokes the same strict verifier and full regression command.
- [x] GitHub Actions run 31441487067 provisions PostgreSQL 17 and passes the strict
  PostgreSQL verifier plus full regression on candidate commit `3ae6d6d`.
- [x] GitHub Actions run 31444166567 passes on exact candidate `5f789ea`; its later
  architecture rejection is retained and is not hidden by the hosted success.
- [x] The complete Foundation v0.1 regression and both mock/synthetic demos remain green.
- [x] SQLite remains a clearly labeled lightweight local/test path.
- [x] Dependency, credential, build, regression, quality-structure, and continuity gates pass.

## Acceptance and continuity

- [x] Run-002 persistence architecture reviewer accepted with no P0/P1.
- [x] Run-002 concurrency/reliability reviewer accepted with no P0/P1.
- [x] Run-003 independent security recheck accepts PE-F-010 with no P0/P1 security finding.
- [x] Run-003 persistence-architecture and concurrency/reliability reviewers accept with
  no P0/P1 finding in their scopes.
- [x] Run-004 architecture, concurrency/reliability, and security reviewers accept with no
  P0/P1 finding and independently accept the handler-envelope repair.
- [x] Run-004 milestone rejection/escalation remains immutable evidence of the mandatory
  CAP-007 lock-timeout P2 rather than being rewritten by successor success.
- [x] Run-005 P1 `recovery-lock-timeout-scope-untranslated-55p03` is resolved by retained
  iteration 2 and accepted on exact SHA by architecture, concurrency, security, and milestone reviewers.
- [x] GitHub destination and explicit commit/remote/push/Actions authority are recorded;
  hosted run 31445219880 is authentic exact-SHA repaired-tree evidence.
- [x] Manifest, ADRs, architecture/security docs, risks, status, evidence, and handoff agree.
- [x] Fresh hosted execution and all four independent run-005 acceptance roles pass with
  no P0/P1/P2 finding.
- [x] Final continuity and named Quality Gauntlet `--require-pass` execution exit 0.

## Product North Star boundary

- [x] Charter and product truth describe proactive, event-driven, permission-controlled assistance.
- [x] Candidate-insight, executive-synthesis, verification, and learning contracts remain planned.
- [x] No live model, bank, calendar, email, wearable, specialist runtime, or continuous LLM loop was added.

## Explicit exclusions

- [x] No live banking, email, calendar, model, wearable, or other provider integration.
- [x] No real personal/household/financial data or credentials.
- [x] No production financial action, Level 4/5 execution, or unrestricted autonomous agent.

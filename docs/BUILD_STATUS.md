# Build status

- **Current phase:** Persistence & Execution Foundation v0.2
- **Status:** Successor Quality Gauntlet run 005 active; v0.2 is not accepted
- **Accepted capability baseline:** Foundation v0.1 at `foundation-v0.1-accepted`
- **Capability mode:** Local, mock-only, synthetic-data-only; no live capability
- **Last updated:** 2026-08-11

## Accepted baseline

Foundation v0.1 remains independently accepted at commit
`e15b256cd3d632f4b9292b6c63819d75c8f19db1` and annotated tag
`foundation-v0.1-accepted`. Accepted migrations 0001 through 0005 are unchanged, the
complete Foundation regression remains green, and no v0.2 work changes product behavior,
provider mode, capability status, or authority level.

## v0.2 implementation checkpoint

- ADR 0012 selects PostgreSQL 17 as the production-semantic reference while retaining
  SQLite as an explicitly lightweight local/test path.
- ADR 0013 defines finite redacted canonical events, atomic outbox enqueue, database-time
  claims, fencing tokens, bounded retry, visible failure, explicit recovery, consumer
  receipts, atomic internal effects, and append-only transition history.
- Alembic revisions 0006 through 0008 add PostgreSQL audit immutability, durable execution,
  and recovery receipts. Revision identifiers fit the accepted Alembic version table and
  the immutable accepted-v0.1 revisions remain untouched.
- The strict verifier now seeds representative revision-0005 state without invoking the
  current-head application, then proves its preservation through revision 0008.
- Execution status and failed-work reads cross central owner policy. Recovery is a typed,
  correlated, idempotency-digested command with a durable exact-result receipt,
  changed-content denial audit, and current reauthorization before every initial or
  exact-replay result disclosure.
- Product North Star documents now specify a proactive, event-driven, shared-world-model
  organisation with candidate-insight and executive-synthesis contracts. These are future
  contracts only; no specialist runtime, live provider, external action, or continuous
  model loop was added.

## Latest verified evidence

- A checksum-pinned extract-only PostgreSQL 17.10 runtime ran on `127.0.0.1:55432`, UTC,
  under the synthetic `personal_os` user. All runtime/data/password/log files are under
  ignored `work/` and are not source-control candidates.
- `npm.cmd run verify:postgresql` exits 0: clean zero-to-0008 migration, populated accepted
  0005-to-0008 preservation, second no-op upgrade, two idempotent fixture loads, and 14
  PostgreSQL tests pass.
- Run-004 reviewers reran the PostgreSQL path on isolated database names; clean and
  populated migrations, fixtures, and all 14 PostgreSQL tests passed.
- `npm.cmd run verify` exits 0: repository safety, Ruff/ESLint, strict Python/TypeScript,
  76 backend unit tests, one frontend test, 38 SQLite integration tests, production build,
  CI-contract/quality/continuity validators, and both mock/synthetic demo flows pass.
- `npm.cmd run test:execution` exits 0 with 19 passed; `npm.cmd run
  test:dialect-boundaries` exits 0 with 8 passed.
- Independent architecture, concurrency, and security reviewers accept the handler repair:
  nine direct/stateful attacks fail as `handler-envelope-invalid`, with zero effect/receipt,
  unchanged stored payload, and atomic failed transition/audit.
- `npm.cmd run audit:dependencies` exits 0 with no known third-party vulnerability; the
  editable local `personal-os` package is explicitly skipped because it is not on PyPI.
- The demo reports `live_capabilities: []`. The user-authorized empty GitHub destination
  now contains the unchanged accepted main/tag and candidate branch. GitHub Actions run
  `31441487067` completed successfully on candidate commit `3ae6d6d325ddeab5b049c737ef4574388c4a4440`.

## Quality disposition

Runs 002, 003, and 004 are frozen `COMPLETE / ESCALATE`, never PASS. Run 004 used its
fixed three repairs to resolve actual hosted CI, truthful preauthorization history, and
handler-envelope binding. Its vector improved from `[0, 1, 3, 0]` to `[0, 0, 1, 0]`.

Run-004 independent decisions are:

- persistence architecture: ACCEPT, no P0/P1;
- concurrency and reliability: ACCEPT, no P0/P1;
- security and authorization: ACCEPT, no P0/P1;
- final milestone acceptance: REJECT and ESCALATE.

The sole blocker is P2 `recovery-advisory-lock-unbounded-wait`, tied to mandatory CAP-007.
PostgreSQL reports `lock_timeout=0`, and an independent waiter remained blocked until its
holder released the advisory lock. This is an availability/recovery-latency risk, not a
demonstrated authority bypass, duplicate effect, corruption, data loss, or lock cycle.

Active successor run `qg-20260810-persistence-execution-v02-run-005` preserves exact
run-004 lineage and starts at `[0, 0, 1, 0]` with only that stable failure key. Retained
iteration 1 adds a 500 ms transaction-local timeout with typed authorized deferral,
non-enumerating denial, correlated audit, and safe same-key retry after release. Sixteen
PostgreSQL tests and the complete regression pass, improving the vector to `[0, 0, 0, 0]`.
The exact committed tree still requires fresh hosted PostgreSQL/full-regression evidence
and all four independent roles before the v0.2 pass gate. Persistence & Execution
Foundation v0.2 remains unaccepted. No pilot, production, live-provider, real-data,
autonomous-specialist, or external-action claim is authorized.

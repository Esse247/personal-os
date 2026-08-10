# Build status

- **Current phase:** Persistence & Execution Foundation v0.2
- **Status:** Successor Quality Gauntlet run 004 active; v0.2 is not accepted
- **Accepted capability baseline:** Foundation v0.1 at `foundation-v0.1-accepted`
- **Capability mode:** Local, mock-only, synthetic-data-only; no live capability
- **Last updated:** 2026-08-10

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
- Three author-independent reviewers reran the PostgreSQL path on isolated database names;
  each passed the populated upgrade, clean bootstrap, fixtures, and 13-test suite.
- `npm.cmd run verify` exits 0: repository safety, Ruff/ESLint, strict Python/TypeScript,
  76 backend unit tests, one frontend test, 29 SQLite integration tests, production build,
  CI-contract/quality/continuity validators, and both mock/synthetic demo flows pass.
- `npm.cmd run test:execution` exits 0 with 10 passed; `npm.cmd run
  test:dialect-boundaries` exits 0 with 8 passed.
- Independent security recheck `security-authorization-r3-recheck-20260810-2340` accepts
  PE-F-010: allow-then-revoke replay makes two policy decisions, discloses no result after
  revocation, retains one receipt/transition, and appends the correlated denial audit.
- `npm.cmd run audit:dependencies` exits 0 with no known third-party vulnerability; the
  editable local `personal-os` package is explicitly skipped because it is not on PyPI.
- The demo reports `live_capabilities: []`. The user-authorized empty GitHub destination
  is reachable; origin configuration, branch push, and the first hosted CI result remain
  pending in run 004.

## Quality disposition

Run `qg-20260810-persistence-execution-v02-run-002` is frozen as
`COMPLETE / ESCALATE`, not PASS. Persistent-goal continuation authorized bounded successor
run `qg-20260810-persistence-execution-v02-run-003`; its iteration-zero vector is
`[0, 2, 2, 0]`. Retained iteration 1 resolves exact recovery replay reauthorization and
improves the vector to `[0, 1, 2, 0]`. Iteration 2 honestly records no change on hosted CI
and the newly reviewed P2, leaving the final vector `[0, 1, 3, 0]`.

Run-002 independent decisions remain historical input, not run-003 acceptance:

- persistence architecture: ACCEPT, no P0/P1;
- concurrency and reliability: ACCEPT, no P0/P1;
- security and authorization: REJECT;
- final milestone acceptance: REJECT and ESCALATE.

No P0 exists. One P1 blocker remains: CAP-010 requires an actual successful hosted
PostgreSQL CI run, while only the workflow contract and local equivalent have executed.
The repository has no remote, and no remote has been configured or pushed.

Three P2 hardening findings remain: claim history uses an allowed label before the first
policy decision; handler-produced effects are not independently bound to the claimed
event/owner/consumer envelope before persistence; and PostgreSQL recovery advisory-lock
acquisition has no scoped timeout for a wedged open transaction.

Run 003 is frozen `COMPLETE / ESCALATE`. Current persistence-architecture,
concurrency/reliability, and security reviewers accept with no P0/P1 finding in their
scopes; milestone reviewer `anscombe-milestone-r003-20260810-2253` rejects and escalates
because mandatory CAP-010 lacks an actual hosted run. Persistence & Execution Foundation
v0.2 is not complete or accepted. No pilot,
production, live-provider, real-data, autonomous-specialist, or external-action claim is
authorized.

Run `qg-20260810-persistence-execution-v02-run-004` is active at iteration zero with exact
run-003 lineage and baseline vector `[0, 1, 3, 0]`. The user has supplied the empty GitHub
destination and explicit authority to commit, configure origin, push the accepted baseline
and v0.2 branch, and run Actions. CAP-010 remains P1 until an actual hosted PostgreSQL
result succeeds.

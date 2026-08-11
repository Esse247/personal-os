# Build status

- **Current phase:** Persistence & Execution Foundation v0.2
- **Status:** Independently accepted; Quality Gauntlet run 005 is `COMPLETE / PASS`
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
  0005-to-0008 preservation, second no-op upgrade, two idempotent fixture loads, and 18
  PostgreSQL tests pass.
- Run-005 reviewers reran isolated clean/populated PostgreSQL paths and all 18 tests;
  concurrency additionally passed five freshly recreated 13-case stress rounds (65/65).
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
  now contains the unchanged accepted main/tag and candidate branch. GitHub Actions runs
  `31441487067` on `3ae6d6d` and `31444166567` on `5f789ea` completed successfully. The
  latter exact candidate was still rejected by architecture review after a different-key
  row-contention probe exposed a transaction-local timeout leak; hosted success is not
  substituted for acceptance.
- GitHub Actions run `31445219880`, job `93637847953`, completed successfully on accepted
  code candidate `e5fecd68ce9a6a54e7c7367e27aaf52d389d73ed`: PostgreSQL 17,
  CI-contract validation, the strict verifier, full regression, cleanup, and service stop
  all passed.

## Quality disposition

Runs 002, 003, and 004 remain frozen `COMPLETE / ESCALATE`, never relabeled. Successor run
`qg-20260810-persistence-execution-v02-run-005` preserves their lineage and is now
`COMPLETE / PASS`. Iteration 1 resolved the carried unbounded-wait P2. Exact candidate
`5f789ea` then passed hosted CI but was truthfully rejected when architecture review found
P1 `recovery-lock-timeout-scope-untranslated-55p03`. Retained iteration 2 restored the
prior timeout, bounded both recovery lock points, reauthorized after waits, preserved audit
and retry semantics, and returned the derived vector from `[0, 1, 0, 0]` to `[0, 0, 0, 0]`.

Final run-005 decisions are all ACCEPT with no P0/P1/P2 finding:

- persistence architecture: `faraday-persistence-architecture-r005-20260811-0218-b4d2`;
- concurrency and reliability: `concurrency-reliability-r005-20260811-e5fecd6-a7c19b`;
- security and authorization: `security-authorization-r5-final-20260811-0118`;
- milestone acceptance: `milestone-acceptance-r005-20260811-0125-e5fecd6`.

Every CAP-001 through CAP-010 and REG-001 through REG-005 criterion passes. The named
Quality Gauntlet pass gate and reconciled continuity gate are the authoritative completion
checks. Persistence & Execution Foundation v0.2 is accepted only for its documented
localhost, mock-only, synthetic-data scope. No pilot, production, live-provider, real-data,
autonomous-specialist, or external-action claim is authorized.

# Handoff

## Current state

Foundation v0.1 remains independently accepted at tag `foundation-v0.1-accepted`.
Persistence & Execution Foundation v0.2 remains active and unaccepted. Runs 002 through
004 are frozen `COMPLETE / ESCALATE`. Run-005 iteration 1 resolved the carried P2, but
exact candidate `5f789ea` was rejected when architecture review found P1
`recovery-lock-timeout-scope-untranslated-55p03`. Retained iteration 2 now restores the
prior PostgreSQL timeout and bounds both advisory-key and event-row locks. Its local and
real-PostgreSQL vector is `[0, 0, 0, 0]`; replacement hosted and independent acceptance
evidence is still pending. No capability is live.

Real PostgreSQL 17.10 evidence now proves clean and populated migrations, deterministic
fixtures, transactions, locking/races, audit immutability, bounded delivery, restart,
fencing, duplicate tolerance, and recovery persistence. Run-003 iteration 1 now
reauthorizes exact recovery replay before receipt read/result disclosure; independent
security review accepts replay and handler-envelope repairs with no P0/P1 finding. Hosted
CI proves pushed candidates `3ae6d6d` and `5f789ea`, but the latter review finding required
the current iteration-2 repair. The replacement exact commit still needs a fresh hosted run
and all four fresh reviews before milestone acceptance.

## Exact next task

Do not edit completed runs 002 through 004 and do not begin broader v0.2/product work.
Review the complete Git candidate set, run the credential/dependency/continuity gates,
commit and push the exact run-005 repaired tree, and obtain fresh hosted
PostgreSQL/full-regression evidence. Then rerun all four independent roles, reconcile the
final run/checklist/status/evidence/handoff records, and execute the named Quality Gauntlet
pass gate before any v0.2 completion claim.

## Read first

`AGENTS.md`, `PROJECT_MANIFEST.yaml`, `docs/BUILD_STATUS.md`, `docs/EVIDENCE.md`,
`docs/RISK_REGISTER.md`, ADRs 0012 and 0013, active successor run 005, and
`checklists/PERSISTENCE_EXECUTION_V0_2.md`.

## Guardrails

Preserve the accepted Foundation v0.1 baseline and migrations, fixed v0.2 Success Contract,
provider/model neutrality, mock-only/synthetic-only mode, one permission-controlled world
model, event-driven selective reasoning, deterministic authority, and the explicit SQLite
local/test path. Do not add live providers, real credentials/data, Level 4/5 external
actions, unrestricted agents, recursive repair loops, continuous model calls, or future
specialists while completing the remaining evidence and acceptance gates.

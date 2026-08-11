# Handoff

## Current state

Foundation v0.1 remains independently accepted at tag `foundation-v0.1-accepted`.
Persistence & Execution Foundation v0.2 is independently accepted. Runs 002 through 004
remain frozen `COMPLETE / ESCALATE`; run 005 is `COMPLETE / PASS` with vector
`[0, 0, 0, 0]`. Its retained history includes candidate `5f789ea`'s rejection and the
iteration-2 repair. Accepted code candidate `e5fecd68ce9a6a54e7c7367e27aaf52d389d73ed`
passed exact-SHA hosted PostgreSQL/full verification and all four independent roles with no
P0/P1/P2 finding. No capability is live.

Real PostgreSQL 17.10 evidence now proves clean and populated migrations, deterministic
fixtures, transactions, locking/races, audit immutability, bounded delivery, restart,
fencing, duplicate tolerance, and recovery persistence. Run-003 iteration 1 now
reauthorizes exact recovery replay before receipt read/result disclosure; independent
security review accepts replay and handler-envelope repairs. Hosted run `31445219880`
proves the replacement exact SHA; isolated architecture, concurrency, security, and
milestone reviewers accept the bounded lock repair and every Success Contract criterion.
The accepted Foundation v0.1 tag/main, migrations 0001 through 0005, and ADRs 0001 through
0011 remain unchanged.

## Exact next task

Do not reopen accepted Foundation v0.1 or v0.2 without concrete regression evidence and do
not infer pilot/live capability. Await the user's next `/goal`. Recommended next goal:
define a bounded pre-pilot Identity, Consent & Data Lifecycle Success Contract covering
production identity/authorization design, explicit consent-grant lifecycle, retention and
deletion semantics, and their evidence gates, without enabling a live provider.

## Read first

`AGENTS.md`, `PROJECT_MANIFEST.yaml`, `docs/BUILD_STATUS.md`, `docs/EVIDENCE.md`,
`docs/RISK_REGISTER.md`, ADRs 0012 and 0013, completed successor run 005, and
`checklists/PERSISTENCE_EXECUTION_V0_2.md`.

## Guardrails

Preserve the accepted Foundation v0.1 baseline and migrations, fixed v0.2 Success Contract,
provider/model neutrality, mock-only/synthetic-only mode, one permission-controlled world
model, event-driven selective reasoning, deterministic authority, and the explicit SQLite
local/test path. Do not add live providers, real credentials/data, Level 4/5 external
actions, unrestricted agents, recursive repair loops, continuous model calls, or future
specialists without a new bounded Success Contract and explicit goal.

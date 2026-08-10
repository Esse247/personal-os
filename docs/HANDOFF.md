# Handoff

## Current state

Foundation v0.1 remains independently accepted at tag `foundation-v0.1-accepted`.
Persistence & Execution Foundation v0.2 remains the active but unaccepted phase. Runs 002
and 003 are frozen `COMPLETE / ESCALATE`. User-supplied GitHub authority resolved the
external-decision stop and opened successor run 004 at iteration zero, carrying the hosted
CI P1 and three P2 hardening findings. No capability is live.

Real PostgreSQL 17.10 evidence now proves clean and populated migrations, deterministic
fixtures, transactions, locking/races, audit immutability, bounded delivery, restart,
fencing, duplicate tolerance, and recovery persistence. Run-003 iteration 1 now
reauthorizes exact recovery replay before receipt read/result disclosure; independent
security recheck accepts the repair with no P0/P1 security finding. No actual hosted CI
result exists, so v0.2 remains unaccepted.

## Exact next task

Do not edit completed runs 002 or 003 and do not begin broader v0.2/product work. In active
run 004, take this exact order:

1. Create the authorized v0.2 branch, commit the fully scanned candidate, configure origin,
   push the accepted v0.1 baseline/tag and v0.2 branch, then capture the actual GitHub
   Actions PostgreSQL result. Local or structural evidence is not a substitute.
2. Only after P1 clearance, correct the three P2 hardening items: label claim history as
   preauthorization, and validate the handler effect ID/consumer/event/owner/type/payload
   against the claimed envelope before persistence with an adversarial-handler test. Also
   add a scoped PostgreSQL advisory-lock timeout with deterministic operator failure/retry
   evidence for a wedged recovery transaction.
3. Rerun all four independent roles and the named Quality Gauntlet pass gate before any
   v0.2 completion claim.

## Read first

`AGENTS.md`, `PROJECT_MANIFEST.yaml`, `docs/BUILD_STATUS.md`, `docs/EVIDENCE.md`,
`docs/RISK_REGISTER.md`, ADRs 0012 and 0013, active successor run 004, and
`checklists/PERSISTENCE_EXECUTION_V0_2.md`.

## Guardrails

Preserve the accepted Foundation v0.1 baseline and migrations, fixed v0.2 Success Contract,
provider/model neutrality, mock-only/synthetic-only mode, one permission-controlled world
model, event-driven selective reasoning, deterministic authority, and the explicit SQLite
local/test path. Do not add live providers, real credentials/data, Level 4/5 external
actions, unrestricted agents, recursive repair loops, continuous model calls, or future
specialists as a workaround for the remaining hosted-CI P1 or three P2 hardening findings.

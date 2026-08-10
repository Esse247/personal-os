# Foundation v0.1 checklist

Status legend: `[x]` verified complete; `[ ]` incomplete; `[~]` deliberately deferred with rationale.

## Source of truth and continuity

- [x] `AGENTS.md` is concise and points to the manifest and indexed sources.
- [x] Manifest maps phase, sources, decisions, checklist, evidence, handoff, skills, and commands.
- [x] Required product/architecture/domain/security/integration/scheduling/UX sources exist.
- [x] Numbered ADRs record architecture, stack, persistence, boundaries, approvals, providers, identity, and the bounded quality protocol.
- [x] Open questions, risks, build status, evidence, and handoff have an initial truthful entry.
- [x] Five repo-scoped skills validate and remain focused.
- [x] Continuity validator passes and detects broken fixtures in its tests.

## Post-acceptance stewardship hardening

- [x] `AGENTS.md` reconstructs mission, architecture, phase, verified state, active goal, unresolved decisions, risks, and exact next action without chat history.
- [x] Quality run `qg-20260810-operating-rules-run-001` is contract-hashed, bounded to three repairs, independently reviewed, and reconciled with continuity records.
- [x] Structural quality validation is distinct from derived milestone PASS, and adversarial validator tests cover fail-open acceptance paths.
- [x] The complete Foundation regression remains green and no capability changed state.
- [x] Independent final evidence review accepted the reconciled run with no P0/P1 unsupported claim.

## Architecture and domain

- [x] Modular-monolith and inward-dependency rules are documented.
- [x] Broad core domain catalog and important state transitions are documented.
- [x] Provenance and capability-state vocabularies are documented.
- [x] Framework-free state transitions and architecture guard tests pass.
- [x] Required provider ports and mock/null adapters exist and pass substitution tests.
- [x] Migration applies from zero and fixtures load idempotently.

## Security, privacy, autonomy

- [x] Action levels, approval binding, consent default, and ship blockers are documented.
- [x] Central policy denies unknown/cross-person/out-of-scope access.
- [x] Approval/version/idempotency behavior passes tests.
- [x] Audit history is append-only and permission-filtered.
- [x] Mock/live mode fails closed and UI/API/spec agree.
- [x] Independent security/permission implementation review has no open blocker.

## Required working flows

- [x] Haircut capture creates user-stated intent and auditable commitment from confirmed fixture facts.
- [x] Mock calendar availability yields a deterministic feasible proposal.
- [x] Dashboard shows proposal and approve/change/reject behavior.
- [x] Each transition appears in audit history.
- [x] Synthetic house transaction is deterministically categorised and displayed with source/confidence/history.
- [x] Ambiguous input requires clarification and creates no commitment/schedule.
- [x] No live provider, real credential, personal data, or outbound side effect is used.

## Interface and quality

- [x] Responsive dashboard contains all minimum panels and persistent mock/synthetic status.
- [x] Captured/provider strings render inertly and controls have accessible labels/focus.
- [x] Setup, development, migration, fixture, demo, and verification commands are documented and usable.
- [x] Build, lint, type checks, unit tests, integration tests, and demo verifier pass.
- [x] Actual results and exit codes are recorded in `docs/EVIDENCE.md`.

## Final acceptance

- [x] Capabilities distinguish planned, mocked, implemented, live, and prohibited accurately.
- [x] Integration, security, and release checklists are reconciled.
- [x] Independent reviewers executed architecture, security, and evidence checks and did not approve their own work.
- [x] No known high-impact Foundation v0.1 defect remains.
- [x] Build status and handoff reflect the exact verified state and next goal.

## Deliberate phase deferrals

- [~] Production authentication — local synthetic identity only; production identity design is v0.2.
- [~] Live provider integrations — prohibited until per-provider readiness and consent review.
- [~] Level 4/5 execution — mock-only or prohibited; explicit future approval/reverification required.
- [~] PostgreSQL local execution evidence — optional if Docker unavailable; required before any pilot/production claim.
- [~] Full CRUD for the broad future domain — contracts and states only outside the required vertical slice.
- [~] Uncontrolled/recursive agent runtime — explicitly excluded; only bounded contracts/activity are demonstrated.

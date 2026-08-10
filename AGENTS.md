# PERSONAL OS repository protocol

## Source hierarchy

1. Current user instruction and applicable safety policy.
2. `PROJECT_MANIFEST.yaml`, the compact project map—not a product specification.
3. Accepted ADRs in `docs/decisions/`.
4. Authoritative product, architecture, domain, security, integration, and UX sources indexed by `docs/INDEX.md`.
5. Executable specifications, migrations, code, and tests.
6. `docs/BUILD_STATUS.md`, `docs/EVIDENCE.md`, and `docs/HANDOFF.md` for execution state.

Resolve contradictions upward through this source hierarchy. Never silently weaken a stronger constraint.

## Recovery and goal selection

Before editing, use manifest-selected sources and working-tree state to reconstruct without chat history:

- mission from `docs/PROJECT_CHARTER.md` and product sources;
- architecture from `docs/ARCHITECTURE.md` and relevant ADRs;
- phase, status, data/provider modes, active checklist, and capability truth from the manifest and `spec/capabilities.yaml`;
- verified state from `docs/BUILD_STATUS.md` and the latest `docs/EVIDENCE.md`;
- active goal from the current user request, otherwise the `docs/HANDOFF.md` exact next task;
- unresolved decisions from `docs/OPEN_QUESTIONS.md`, risks from `docs/RISK_REGISTER.md`, and the exact next action from handoff.

Do not reopen or reimplement a completed, independently accepted phase without concrete contradictory evidence. If current instructions conflict with recorded status, surface the conflict before changing scope.

## Work and authority boundaries

- Plan the smallest coherent bounded vertical slice; preserve modular-monolith boundaries and keep domain/application code provider-neutral.
- Models may interpret and propose. Only validated commands may write authoritative state.
- Deterministic code owns calculations, money, permission decisions, state-transition validation, scheduling constraints, and side-effect gates.
- Preserve user overrides, provenance, consent, buffers, idempotency, and append-only audit history.
- Prefer incremental, reversible work; create an ADR before introducing or changing a durable architectural rule.

## Quality, subagents, and review

Use `.agents/skills/quality-gauntlet/SKILL.md` for meaningful milestones, high-risk changes, release/completion claims, or an explicit quality pass; skip it for trivial typo/format-only work unless requested. Define success before implementation, repair one highest-impact confirmed failure per iteration, and obey its finite stop/escalation rules.

Give subagents bounded, non-overlapping file ownership; forbid simultaneous edits to the same files; keep integration with the root agent. A builder may self-check but may not approve their own meaningful work. Final acceptance requires an independent reviewer; route architecture changes to architecture review and permissions, finance, sensitive data, autonomy, providers, or external actions to security review.

## Security and capability truth

The current localhost, mock-only, synthetic-only restrictions remain binding until authoritative sources are deliberately advanced with reviewed evidence. Default deny unknown permissions, providers, environments, and side effects. Household membership is not consent. Never expose credentials or protected payloads in code, logs, audit views, fixtures, screenshots, or notifications.

Keep capability states planned, mocked, implemented, live, and prohibited distinct across spec, runtime, UI, status, and evidence. Never promote a claim from code presence or model output alone.

## Evidence and handoff

Run proportionate lint, type, unit, integration, build, security, browser, and continuity checks. Do not claim completion from inspection or planned commands. At each meaningful checkpoint, update only changed truth: exact commands, exit codes, and results in evidence; current state/checklist; decisions/risks; and one concrete exact next task in handoff. Validate continuity before reporting verified outcomes, residual risks, and deferrals.

# Quality gauntlet protocol

This directory stores bounded, reviewable evidence for meaningful PERSONAL OS milestones. It is subordinate to `PROJECT_MANIFEST.yaml` and the repository source hierarchy: contracts interpret authoritative goals; runs record evaluations and repairs; neither silently changes product truth, capability state, permissions, or release status.

The protocol follows four durable rules:

- define measurable success before implementation;
- prefer deterministic evaluators and preserve exact results;
- repair one highest-impact confirmed failure per iteration;
- stop with `PASS`, `FAIL`, or `ESCALATE` under a finite budget.

Recorded command strings are inert. `scripts/validate_quality.py` parses and validates artifacts but never executes commands, edits files, invokes agents, or applies repairs. A typed disposition is not authoritative: the validator derives PASS eligibility from criteria, regressions, unresolved severity, independent reviewer decisions, and continuity references.

## Layout

- `contracts/`: immutable-after-baseline success contracts, named by stable contract ID.
- `runs/`: active or final run records bound to a contract ID, path, and SHA-256.
- `rubrics/`: optional machine-readable thresholds for genuinely subjective review.
- `schemas/`: JSON Schemas documenting accepted artifact shapes.
- `agents-policy.yaml`: measurable policy for the concise root `AGENTS.md`.

The repository may have no Git commit yet. In that case a run records `repository_revision: null` and `workspace_state: uncommitted`; the contract hash remains mandatory.

## Lifecycle

1. Create the contract and active run before implementation; baseline is iteration zero.
2. Validate artifacts with `npm run validate:quality`.
3. Evaluate in authority order, record stable failure keys, and make at most one focused repair in an iteration.
4. Compare the recomputed severity vector with the best previous result and rerun relevant regressions.
5. Obtain author-independent decisions for every required role.
6. Reconcile `docs/EVIDENCE.md`, `docs/BUILD_STATUS.md`, the active checklist, risks/ADRs where needed, and `docs/HANDOFF.md`.
7. Gate a milestone with `npm run validate:quality -- --require-pass <run-id>`.

Structural validation intentionally accepts truthful final FAIL or ESCALATE history. The named pass gate does not.

## Severity and boundedness

P0 freezes affected side-effecting behavior and always blocks PASS. P1 blocks PASS. P2 blocks when tied to a mandatory criterion or unmet threshold; otherwise it needs an explicit deferral. P3 is polish and never displaces a higher-severity failure.

The default repair budget is three. Four or five requires a pre-baseline justification and approver; more than five is invalid. Escalation is mandatory when one failure survives three repairs, two consecutive repairs do not improve the best result, the budget is exhausted with a blocker, requirements conflict or cannot be measured, an external dependency or user decision blocks progress, or a safe repair would violate authoritative constraints.

## Evidence hygiene

Use repository-relative paths. Do not use absolute paths or `..` traversal. Store concise results rather than raw logs, prompts, secrets, personal data, credentials, or protected payloads. Finalized run artifacts are append-only evidence; corrections use a successor record with explicit lineage.

This design follows the repository decision in ADR 0011 and its official OpenAI references.

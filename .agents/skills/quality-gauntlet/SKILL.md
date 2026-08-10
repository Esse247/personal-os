---
name: quality-gauntlet
description: Run a bounded, evidence-driven quality and repair pass for PERSONAL OS milestones. Use for meaningful or high-risk implementation, release or completion claims, explicit quality passes, critical domain behavior, migrations, and changes affecting architecture, security, permissions, finance, data access, agent autonomy, external actions, or user-facing flows. Do not invoke for trivial typo/format-only edits, low-risk covered refactors, or read-only answers unless the user asks.
---

# Quality Gauntlet

Use `quality/README.md` as the artifact contract. This skill coordinates a finite workflow; it never gives a model authority to approve its own work, execute commands stored in YAML automatically, or recursively enqueue repairs.

## 1. Establish the gate before implementation

1. Use `project-continuity` to reconstruct the repository state and authoritative sources.
2. Create a versioned success contract under `quality/contracts/` before the baseline. Bind scope, exclusions, mandatory capability and regression criteria, evaluator types, severity on failure, required independent roles, and a repair budget.
3. Default to three repair iterations. Four or five require an explicit pre-baseline justification and approver; more than five is invalid.
4. Create the active run under `quality/runs/`, bind it to the contract ID, path, and SHA-256, and record iteration zero as the baseline. A run may record an unborn/uncommitted repository honestly.

Do not weaken or rewrite an active contract after seeing results. Supersede it with explicit lineage when requirements legitimately change.

## 2. Evaluate in authority order

Evaluate applicable criteria from strongest to weakest:

1. deterministic tests, static analysis, security checks, and schema validation;
2. domain invariants, authorization/consent gates, integration tests, and regressions;
3. artifact or browser evidence for user-facing behavior;
4. independent specialist or rubric review;
5. human/product judgment when requirements cannot be resolved mechanically.

Deterministic evidence outranks model opinion. UI scope needs browser evidence when tooling is available. Finance, permission, and Level 4/5 paths need mandatory authorization tests. Architecture or security risk tags require matching independent reviewer roles.

Record exact commands, exit codes, concise material results, and safe evidence references. Never store secrets, personal data, or large transcripts in quality artifacts.

## 3. Repair one confirmed failure

Select the highest-severity confirmed failure: P0, then P1, P2, P3. P0 freezes the affected side-effecting path; P1 blocks PASS; P2 blocks when mandatory or below threshold; P3 is polish.

For one iteration only:

1. choose one stable `failure_key` and one focused repair;
2. record the repair author and changed paths;
3. rerun the targeted evaluator and all relevant regressions;
4. recompute the severity vector against the best prior result;
5. keep the repair only when it improves the best result without an unacceptable regression.

Renaming a failure does not reset its attempt count. Builders and repair authors may self-check, but may not provide final independent acceptance.

## 4. Stop deliberately

- `PASS`: every mandatory and regression criterion passes, no P0/P1 remains, rubric thresholds are met, all required author-independent reviewers accept, and continuity records are reconciled.
- `FAIL`: evaluation conclusively rejects the milestone and the run closes without a further repair path.
- `ESCALATE`: safe progress needs changed authority, requirements, an unavailable dependency, a user/product decision, or more work than the bounded loop permits.

Escalate immediately for conflicting or unmeasurable requirements or a repair that would breach authoritative constraints. Escalate after the same failure survives three focused repairs, two consecutive iterations fail to improve the best result, or the approved budget is exhausted with a blocker. Never continue merely to seek a perfect score.

## 5. Close and reconcile

Run structural validation during work. Use the named pass gate only after independent decisions and continuity references exist:

```text
npm run validate:quality
npm run validate:quality -- --require-pass <run-id>
```

Then use `evidence-gate`, update only changed truth in `docs/EVIDENCE.md`, `docs/BUILD_STATUS.md`, the active checklist, risks/decisions, and `docs/HANDOFF.md`, and run continuity plus proportionate regressions. Structural validity of a truthful FAIL or ESCALATE record is not milestone acceptance.

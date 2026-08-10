---
name: project-continuity
description: Resume, select, and hand off work in the PERSONAL OS repository using its manifest, source hierarchy, build status, evidence, risks, and active checklist. Use when starting or ending a PERSONAL OS task, recovering context, choosing the next task, changing phase/status, or preparing a handoff.
---

# Project Continuity

## Start work

1. Read `PROJECT_MANIFEST.yaml` completely.
2. Read the manifest targets for build status, handoff, active checklist, evidence, risks, and open questions.
3. Read the ADRs and authoritative sources relevant to the requested area.
4. Inspect working-tree state and preserve unrelated user changes.
5. Verify current capability mode before describing anything as live.
6. Select the smallest unfinished task that advances the active phase and state its acceptance evidence.

Resolve contradictions according to `AGENTS.md`. Do not infer completion or revive a deferred capability from stale prose.

## Work checkpoint

Keep implementation within the current phase and architecture boundaries. Batch status/document changes at meaningful checkpoints. When behavior or a durable decision changes, update its authoritative source or add a numbered ADR; do not duplicate the same truth in multiple places.

## End work

1. Run proportionate verification and capture exact command, exit status, and material result.
2. Update `docs/EVIDENCE.md` with observed evidence only.
3. Reconcile the active checklist and `spec/capabilities.yaml` with verified behavior.
4. Update `docs/BUILD_STATUS.md` without overstating incomplete or mocked capability.
5. Put one concrete next task, context, and guardrails in `docs/HANDOFF.md`.
6. Update risks/open questions when evidence changed them.
7. Run the manifest's continuity command.

Do not mark the phase complete while required work, a ship blocker, or independent review remains.

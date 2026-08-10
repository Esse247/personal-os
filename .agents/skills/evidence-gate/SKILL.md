---
name: evidence-gate
description: Validate PERSONAL OS implementation, release, capability, and completion claims against executable evidence and continuity records. Use before saying a task, checklist item, demonstration flow, security control, integration, phase, or release is complete, working, safe, implemented, or live.
---

# Evidence Gate

## Gate a claim

1. State the exact claim and find its acceptance criteria in `PROJECT_MANIFEST.yaml`, the active checklist, specification, ADR, or authoritative source.
2. Identify commands or observable behavior that can falsify the claim. Code inspection alone is insufficient for runtime claims.
3. Run the narrowest relevant checks, then the required aggregate gate. Use a clean database/environment where setup, migration, or idempotency is part of the claim.
4. Record command, timestamp, exit status, meaningful result, environment limitations, and any skipped check in `docs/EVIDENCE.md`.
5. Confirm code, API, UI, `spec/capabilities.yaml`, checklist, build status, and handoff agree.

## Claim rules

- `implemented` requires executable code and passing focused tests.
- `working demonstration` requires the end-to-end verifier or direct observable flow, not isolated units.
- `live` requires a real authorized provider and integration-readiness evidence; Foundation v0.1 forbids this status.
- `secure`, `release-ready`, or phase completion requires independent review and no unresolved ship blocker.
- A skipped/unavailable command is a limitation or deferral, never a pass.
- A mock result proves only mocked behavior and must remain labeled.

If evidence is insufficient, report the verified subset and the exact missing check. Never convert planned commands, reviewer recommendations, or inspection into successful evidence.

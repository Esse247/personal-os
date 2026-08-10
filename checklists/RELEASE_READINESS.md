# Release readiness checklist

## Truth and scope

- [x] Build status, capabilities, checklist, evidence, and handoff agree.
- [x] No mocked/planned feature is described as live.
- [x] No real secret, personal data, provider call, or external side effect exists.
- [x] Deferred items include rationale and do not conceal a Foundation v0.1 completion blocker.

## Reproducibility and verification

- [x] Dependency-free-copy documented setup succeeds with an explicit trusted Python bootstrap.
- [x] Migration from zero, historical migration upgrade, and idempotent synthetic fixture load succeed.
- [x] Build, lint, strict type checks, unit and integration tests pass.
- [x] Local demo verifier proves both flows and ambiguous behavior.
- [x] Continuity validator passes.
- [x] Frontend is checked at desktop and narrow viewport with keyboard-accessible decisions.

## Architecture and security

- [x] Architecture boundary/provider substitution tests pass.
- [x] Permission, household isolation, provenance, approval, audit, XSS, and mock-only tests pass.
- [x] Independent architecture/security reviewers have no ship blocker.
- [x] No unresolved high-impact defect or high/critical dependency/secret finding remains.

## Handoff

- [x] Evidence includes exact commands, exit status, timestamp, and meaningful results.
- [x] Decision changes have ADRs and indexed documentation updates.
- [x] Handoff names one exact next goal with guardrails.

This release gate accepts only the localhost, mock-only, synthetic-data Foundation v0.1 demonstration. PostgreSQL/Docker runtime, production identity, live integrations, real data, and external actions are not released.

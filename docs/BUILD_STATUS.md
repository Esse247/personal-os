# Build status

- **Current phase:** Foundation v0.1
- **Status:** Complete and independently accepted for the localhost, mock-only, synthetic-data scope
- **Capability mode:** Local, mock-only, synthetic-data-only
- **Last updated:** 2026-08-10

## Established

- Repository source hierarchy, continuity protocol, ADRs, machine-readable capability/permission/integration specs, active checklists, and five validated repo skills.
- Modular-monolith boundaries, framework-free domain transitions, centralized policy, typed provider contracts, deterministic scheduling/finance, provenance, approval, idempotency, audit, and worker boundaries.
- SQLAlchemy persistence with immutable Alembic revisions, durable command receipts, compare-and-swap updates, schedule-block conflict guards, idempotent synthetic fixtures, and append-only audit history.
- Typed FastAPI surface and responsive React dashboard with explicit local/mock/synthetic presentation.
- Required haircut scheduling/decision flow, finance categorisation flow, and ambiguity-without-invention behavior.

## Final verified checkpoint

- A dependency-free temporary copy completed the documented Windows setup with an explicit trusted Python bootstrap, then passed the full verification command.
- Ruff/ESLint lint, strict Python/TypeScript type checks, 26 backend unit tests, one frontend component/XSS-safety test, and 19 HTTP/persistence integration tests pass.
- Production frontend build, migration from zero and historical upgrade, idempotent fixtures, continuity validation, deterministic demo verification, and the four Foundation-era repo-skill validations pass.
- In-app browser verification passed at desktop and 375 px, including capture/change/approve/clarification interactions, keyboard labels/focus, no horizontal overflow, and no browser console warning/error.
- Independent architecture, security, and evidence reviewers accepted the final tree and reconciled records. Their focused probes cover replay/mutation, CAS and overlap races, durable denial audit, snapshot binding, household isolation, provider substitution, fail-closed configuration, provenance, correlation, worker policy, capability parity, and clean-copy continuity.
- `pip-audit` found no known third-party Python vulnerability and `npm audit` found zero vulnerabilities; the scoped credential scan found no credential material.

## Post-acceptance operating hardening

- `AGENTS.md` is a 521-word navigation and recovery protocol that explicitly reconstructs mission, architecture, phase, verified state, active goal, unresolved decisions, risks, and exact next action while protecting the accepted phase.
- Quality run `qg-20260810-operating-rules-run-001` added a bounded repo skill, pre-baseline hashed success contracts, lifecycle-derived severity vectors, inert validation, regression/security/evidence gates, independent review, and finite PASS/FAIL/ESCALATE behavior.
- The post-hardening full verification passes 57 backend unit tests, one frontend test, 19 integration tests, strict lint/types, production build, quality/continuity validation, and both local mock/synthetic demo flows.
- Independent continuity, gauntlet-architecture, and final evidence reviewers accepted the stable tree with no P0/P1 finding. Foundation v0.1 product behavior and capability truth did not change.

## Explicit constraints and deferrals

- Docker was unavailable, so Docker Compose/PostgreSQL runtime was not executed. PostgreSQL-backed verification is required before any pilot or production claim.
- `pip-audit` cannot resolve the local editable `personal-os` package against PyPI; it did audit its installed third-party environment.
- Dependency-origin Starlette/TestClient and Python 3.12 SQLite datetime-adapter deprecation warnings remain non-blocking and tracked for v0.2.
- Production authentication, live providers, real data, and external actions remain prohibited and unimplemented.

No capability is live. Foundation v0.1 is complete only for the bounded local/mock/synthetic scope above.

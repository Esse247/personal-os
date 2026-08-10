# Foundation v0.1 implementation plan

## Phase 1 — continuity and decisions

Create the manifest, indexed authoritative sources, ADRs, repo-scoped skills, specifications, checklists, assumptions, risks, and phased plan. Gate: continuity validator can identify all declared targets.

## Phase 2 — authoritative backend slice

Implement framework-free domain transitions, application commands, ports, mock adapters, SQL persistence/migrations, synthetic fixtures, audit history, permissions, scheduling, classification, and typed FastAPI endpoints. Gate: unit and integration tests pass with no network or real secrets.

## Phase 3 — dashboard and decisions

Implement the responsive React dashboard, capture flow, proposal approval/change/rejection, finance view, activity history, and visible mock status. Gate: strict TypeScript, lint, frontend tests, and production build pass.

## Phase 4 — demonstration and hardening

Run migrations and fixtures from zero, execute both flows and the ambiguous-input behavior, test provider substitution and boundary enforcement, and verify the local built UI/API. Gate: one deterministic demonstration verifier passes.

## Phase 5 — independent acceptance

An author-independent architecture/security review and test execution pass must identify and resolve ship blockers. Record exact evidence, reconcile capabilities/checklists/status, document rationale for deferrals, and leave one next goal.

## Scope control

The broad future domain is documented, but v0.1 implements only the smallest complete slice. No live provider, production auth, external side effect, full agent runtime, health decision, or payment workflow may enter this phase.

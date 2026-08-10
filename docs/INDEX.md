# Documentation index

Start with `../PROJECT_MANIFEST.yaml`; it is the compact machine-readable map and command registry.

## Authoritative product and design sources

- [Project charter](PROJECT_CHARTER.md) — mission, scope, principles, success conditions.
- [Product source of truth](PRODUCT_SOURCE_OF_TRUTH.md) — users, flows, capability truth, non-goals.
- [Architecture](ARCHITECTURE.md) — modular-monolith boundaries and runtime topology.
- [Domain model](DOMAIN_MODEL.md) — entities, aggregates, invariants, and transitions.
- [Data and memory model](DATA_AND_MEMORY_MODEL.md) — provenance, confidence, validity, retention.
- [Autonomy and approvals](AUTONOMY_AND_APPROVALS.md) — action levels and execution gates.
- [Security, privacy, and threat model](SECURITY_PRIVACY_THREAT_MODEL.md) — trust boundaries and controls.
- [Integration contracts](INTEGRATION_CONTRACTS.md) — provider-neutral ports and mock policy.
- [Model routing](MODEL_ROUTING.md) — risk-aware model selection without vendor coupling.
- [Scheduling engine](SCHEDULING_ENGINE.md) — deterministic feasibility and humane scoring.
- [UX and notification principles](UX_AND_NOTIFICATION_PRINCIPLES.md) — user sovereignty and attention rules.

## Delivery and continuity

- [Implementation plan](IMPLEMENTATION_PLAN.md)
- [Roadmap](ROADMAP.md)
- [Build status](BUILD_STATUS.md)
- [Handoff](HANDOFF.md)
- [Evidence](EVIDENCE.md)
- [Open questions](OPEN_QUESTIONS.md)
- [Risk register](RISK_REGISTER.md)
- [Decision records](decisions/README.md)
- [Foundation checklist](../checklists/FOUNDATION_V0_1.md)
- [Persistence & Execution Foundation v0.2 checklist](../checklists/PERSISTENCE_EXECUTION_V0_2.md)
- [Quality gauntlet protocol](../quality/README.md)
- [Current quality contract](../quality/contracts/qg-20260810-persistence-execution-v02.yaml)
- [Current quality run](../quality/runs/qg-20260810-persistence-execution-v02-run-005.yaml)

## Command map

After setup, commands are run from the repository root.

| Purpose | Windows | macOS/Linux |
|---|---|---|
| Setup | `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1` | `./scripts/setup.sh` |
| Develop | `powershell -ExecutionPolicy Bypass -File scripts/dev.ps1` | `./scripts/dev.sh` |
| Full verification | `npm run verify` | `npm run verify` |
| Quality artifact validation | `npm run validate:quality` | `npm run validate:quality` |
| PostgreSQL clean verification | `npm run verify:postgresql` | `npm run verify:postgresql` |
| Durable execution tests | `npm run test:execution` | `npm run test:execution` |
| Process one local internal event | `npm run execution:once` | `npm run execution:once` |
| List failed local internal events | `npm run execution:failed` | `npm run execution:failed` |
| Dependency advisory scan (network) | `npm run audit:dependencies` | `npm run audit:dependencies` |
| Local demonstration | `npm run demo:verify` | `npm run demo:verify` |
| Migration | `npm run db:migrate` | `npm run db:migrate` |
| Synthetic fixtures | `npm run fixtures:load` | `npm run fixtures:load` |

The default services bind to `127.0.0.1`. Docker Compose is an optional reproducibility path, not evidence of a locally verified Docker run unless `docs/EVIDENCE.md` says otherwise.

The setup scripts require Python 3.12 or newer. If it is not on `PATH`, set `PERSONAL_OS_BOOTSTRAP_PYTHON` to a trusted interpreter or pass `-BootstrapPython <path>` to `scripts/setup.ps1` on Windows.

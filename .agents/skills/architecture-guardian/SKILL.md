---
name: architecture-guardian
description: Review and protect PERSONAL OS modular-monolith, domain, application, provider, persistence, API, worker, and audit boundaries. Use when adding or changing modules, entities, commands, repositories, provider adapters, model or agent behavior, migrations, background jobs, APIs, cross-module calls, dependencies, or durable architecture decisions.
---

# Architecture Guardian

## Review workflow

1. Read `docs/ARCHITECTURE.md`, `docs/DOMAIN_MODEL.md`, relevant ADRs, and integration contracts.
2. Map changed files to domain, application, ports, adapters, interface, worker, persistence, or observability.
3. Trace dependency direction and every authoritative write from untrusted input to typed command, authorization, invariant validation, persistence, and atomic audit.
4. Check cross-module work uses public typed commands/queries/events and opaque IDs, not internal repositories or ORM navigation.
5. Check provider/model types and names remain outside domain/application core.
6. Run architecture, state-transition, provider-substitution, migration, and integration checks relevant to the change.

## Block violations

- Domain/application imports FastAPI, SQLAlchemy, concrete adapters, configuration, or provider SDKs.
- A model, agent, UI, provider, or worker writes authoritative state without a validated application command.
- Generic status patches, generic repositories, or silent deletes bypass named transitions.
- Money uses float; schedule time is naive or violates half-open intervals/buffers.
- State mutation and audit append can commit independently.
- Module/provider status is undocumented or mocked/planned behavior is presented as live.
- New durable architecture changes lack a numbered ADR or silently contradict an accepted one.

Return findings with file/line evidence, severity, violated source, and the smallest compliant fix. Approval requires an independent reviewer who did not author the change.

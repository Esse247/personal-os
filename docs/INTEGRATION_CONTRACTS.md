# Integration contracts

## Port rules

Provider-specific code lives only in adapters. Domain/application code consumes canonical ports. Every request carries actor/delegation context, correlation ID, declared capability, deadline, purpose, and an idempotency key for writes. Every response carries provider ID, mock/live mode, external reference/version where applicable, observed time, provenance, warnings, and canonical error type.

Read, prepare/draft, and write/send capabilities remain separate even if one provider implements several.

## Required ports

| Port | Foundation behavior |
|---|---|
| ModelProvider | Schema-constrained interpretation proposal only; deterministic mock; no commands or repository. |
| CalendarProvider | Mock availability/event reads; external create/update prohibited. |
| NotificationProvider | Mock preparation/recording only; specialist cannot dispatch. |
| EmailProvider | Null/mock draft contract; sending prohibited. |
| BankingProvider | Synthetic transaction read contract only; payment capability absent. |
| WearableProvider | Null/mock timestamped observation contract. |
| LocationProvider | Null/mock timestamped observation contract. |
| VoiceProvider | Null/mock transcript/synthesis contract with sensitivity. |
| SearchProvider | Null/mock sourced-result contract. |
| FileStorageProvider | Null/mock opaque reference and retention metadata contract. |
| ToolProvider | Canonical capability declaration and authorized envelope; external execution prohibited. |

## Contract behavior

Adapters must define supported capabilities, statuses (`planned`, `mocked`, `implemented`, `live`, `prohibited`), timeout/error mapping, idempotency, provenance, and sensitivity handling. Unsupported calls return a typed failure, never fallback to a live network provider.

Provider substitution tests run canonical fixtures against alternative mock implementations and ensure no provider types leak inward. Startup rejects `live` in Foundation v0.1. Mock adapters make no outbound provider call.

## ToolAction schema

Each declared action contains permission, level, environment, reversibility, idempotency semantics, approval policy, expected evidence, retry policy, recovery path, data recipient, and disclosure purpose. The policy gate runs before an adapter and again before any future execution.

## Future onboarding gate

A real adapter cannot be introduced until the integration-readiness checklist covers authentication/secret storage, scopes and consent, sandbox/test account, data mapping, rate/error behavior, deletion/retention, webhook verification, idempotency, observability/redaction, incident rollback, contract tests, threat review, and capability-status update.

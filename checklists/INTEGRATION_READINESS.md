# Integration readiness checklist

Status legend: `[x]` verified for a named provider; `[ ]` required and incomplete; `[~]` deliberately deferred because no live provider is authorized.

Apply this checklist independently to each future real provider. Every item is deliberately deferred in Foundation v0.1 because live providers are prohibited; none is represented as passed.

- [~] Provider and exact read/draft/write capabilities are named separately.
- [~] User benefit and data-minimisation rationale are approved.
- [~] Sandbox/test environment and provider terms/licensing are understood.
- [~] Authentication, minimum scopes, consent, revocation, and secret-broker design are reviewed.
- [~] Canonical data mapping preserves source IDs, versions, time, confidence, sensitivity, and deletion signals.
- [~] Timeouts, pagination, rate limits, retries, idempotency, partial failure, and recovery are specified.
- [~] Webhook authenticity/replay/order behavior is tested if applicable.
- [~] Provider errors cannot fall through to another/live adapter.
- [~] Contract and substitution suites cover success, unsupported capability, timeout, malformed data, and duplicate delivery.
- [~] Logs, audit, metrics, and support tooling redact protected content.
- [~] Retention, export, deletion, residency, and incident response are agreed.
- [~] Threat model and permission/action-level mapping receive independent review.
- [~] Capability spec/UI/docs move through mocked -> implemented -> live only with evidence.
- [~] Rollback/disable switch and user-visible disconnection behavior are tested.

# ADR 0008: Provider-neutral, mock-only foundation

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

Define canonical ports for model, calendar, notification, email, banking, wearable, location, voice, search, file storage, and tools. Keep read/draft/write capabilities distinct. Foundation v0.1 registers deterministic mock/null adapters only; unknown or live modes fail startup.

Capability status is machine-readable and shown in the UI as planned, mocked, implemented, live, or prohibited. No real SDK, credential, or network fallback is included.

## Consequences

Provider substitution is testable and product claims remain honest. Real adapter onboarding requires an integration ADR, threat review, consent/scopes, secrets, sandbox evidence, and readiness checklist.

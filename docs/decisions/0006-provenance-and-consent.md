# ADR 0006: Provenance, ownership, and consent boundaries

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

Every fact-like record preserves source type/identifier, observed/recorded time, validity, confidence, confirmation, sensitivity, and relevant actor/data subject. `USER_STATED`, `TOOL_OBSERVED`, `SYSTEM_INFERRED`, and `SYSTEM_PREDICTED` remain distinct.

User identity, human data subject, and household membership are separate concepts. Membership grants no private payload access. Sharing requires an explicit, active, purpose/resource/action/time-scoped grant. Derived data inherits the highest sensitivity of its inputs.

## Consequences

Queries and context assembly require policy filtering. More metadata is stored, but inference cannot silently become fact and household convenience cannot override privacy.

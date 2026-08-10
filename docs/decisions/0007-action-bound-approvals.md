# ADR 0007: Action-bound approvals

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

Represent approval as an immutable decision bound to normalized payload digest, requester/approver, target/provider/environment, permission/action level, resource version, policy version, expiry, nonce, and idempotency key. The execution gate atomically claims it and rechecks policy, consent, digest, version, and expiry.

Requesters, agents, workers, tools, and adapters cannot self-approve. Material change requires a new approval. Level 5 always requires future explicit human confirmation and is prohibited in v0.1.

## Consequences

Simple boolean approval fields are forbidden. Schedule approval in v0.1 authorizes only a reversible internal block, not a live calendar write.

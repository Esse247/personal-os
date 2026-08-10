# Autonomy and approvals

## Action levels

| Level | Meaning | Foundation v0.1 policy |
|---|---|---|
| 0 | Observe/read | Allowed only with scoped permission; mock/synthetic sources. |
| 1 | Analyse or suggest | Allowed with scoped inputs and provenance. |
| 2 | Draft or simulate | Allowed; clearly labeled, no authoritative or external effect. |
| 3 | Reversible internal write | Allowed through validated command, policy, idempotency, and audit; approval as declared. |
| 4 | External side effect | Mock simulation only; live execution prohibited. |
| 5 | Financial, legal, identity, health, or irreversible action | Prohibited; future design always requires explicit human approval and revalidation. |
| Prohibited | Outside permission, consent, environment, or capability | Deny before adapter invocation and audit the denial. |

Unknown permissions, levels, providers, actors, and environments fail closed.

## Tool action declaration

Every tool action contract declares a stable permission, action level, allowed environment, input/output schema and sensitivity, reversibility, idempotency behavior, approval rule, expected evidence, retryable failures and limits, data recipient/purpose, and rollback or recovery path.

## Approval binding

An approval is a decision artifact, not a boolean. It binds:

- normalized immutable action/proposal payload and SHA-256 digest;
- requester, on-behalf-of user, designated approver, target, provider, and environment;
- action level, permission, disclosed data/audience, reversibility, and expected consequence;
- affected resource/proposal versions and policy version;
- creation/expiry times, one-time nonce, and idempotency key.

The requester, agent, worker, adapter, and tool cannot self-approve. Execution atomically claims the approval, verifies digest/version/expiry, and reruns permission and consent checks. A material change or stale version requires a new approval.

## Foundation decisions

Approving a schedule proposal authorizes one reversible internal ScheduleBlock (Level 3), not an external calendar event. Changing a proposal supersedes the prior revision. Rejecting it keeps the commitment visible and actionable. No Level 4/5 live action is registered.

## Delegation

Chief of Staff and specialists have no inherent access. A delegation is restricted to actor/user, task and run, resource selectors, stable permissions, purpose, expiry, and maximum action level. Specialists cannot redelegate, approve, or send notifications directly. Revocation invalidates pending delegations, context packages, approvals, and queued actions that depend on the grant.

## Retries and recovery

Writes require unique idempotency keys. Retry is bounded by the action contract, reauthorized at every attempt, and recorded. Level 5 actions will never auto-retry. Failed or cancelled actions remain visible and cannot be reported as success.

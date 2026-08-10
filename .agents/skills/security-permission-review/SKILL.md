---
name: security-permission-review
description: Review PERSONAL OS authorization, consent, privacy, provenance, approvals, audit, tool actions, provider modes, agent delegation, sensitive UI or logging, and side effects. Use for any change involving personal or household data, identity, permissions, sharing, finance, health, schedules, approvals, providers, agents, workers, notifications, audit history, external actions, or release security.
---

# Security Permission Review

## Establish scope

Read `docs/SECURITY_PRIVACY_THREAT_MODEL.md`, `docs/AUTONOMY_AND_APPROVALS.md`, `spec/permissions.yaml`, relevant ADRs, and the security checklist. Identify actor, data subject/controller, resource, purpose, sensitivity, permission, action level, environment, recipient, and side effect.

## Trace controls

1. Verify the server creates identity/delegation context and the central policy is called for reads, writes, jobs, tools, audit reads, and notifications.
2. Prove household membership alone grants no payload or metadata access; require an explicit active scoped grant.
3. Treat user/model/provider text as untrusted data and require strict typed commands.
4. For approval, verify immutable payload digest, actor/approver, versions, environment, policy, expiry, nonce, one-time claim, and immediate reauthorization.
5. Verify unknown permissions/providers/environments and all Foundation v0.1 live Level 4/5 actions fail closed before adapter invocation.
6. Check provenance/source type, confidence, validity, confirmation, sensitivity inheritance, audit completeness/immutability, and redaction.
7. Run negative tests for IDOR, forged identity, grant expiry/revocation, prompt injection, approval mutation/replay/staleness, duplicate delivery, audit leakage, XSS, and mock/live crossing.

## Review outcome

Classify findings by impact and point to exact evidence. Any real secret/personal data/live side effect, non-local default exposure, implicit household access, model direct write, reusable or mutable approval, fail-open capability, unaudited consequential mutation, mutable or leaking audit, or failing isolation/permission/provenance test is a ship blocker.

Do not call Foundation v0.1 production-secure. Independent review is required before closing the security checklist.

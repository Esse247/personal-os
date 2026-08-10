# Security review checklist

## Data and identity

- [x] Only synthetic fixtures; scoped secret scan finds no credential or personal data.
- [x] Server derives the development principal and rejects forged ownership/role/action-level claims.
- [x] Household membership alone grants no private resource, metadata, count, search, dashboard, or audit access.
- [x] Sharing/consent contracts are purpose/resource/action/time scoped and default deny.
- [x] Derived data retains provenance and highest input sensitivity.

## Command, permission, and approval

- [x] Every exposed read/write/job/tool/audit decision reaches the central policy port.
- [x] Unknown permissions/providers/environments/actions fail closed.
- [x] Model/provider/UI output cannot bypass typed command validation.
- [x] Level 4/5 live action is absent or denied before adapter invocation.
- [x] Approval binds exact digest, actor, approver, target, environment, versions, policy, expiry, and nonce.
- [x] Approval replay, mutation, stale state, self-approval, and concurrent consumption fail.
- [x] Idempotency and retry policies prevent duplicate writes.

## Audit and provenance

- [x] Allowed, denied, changed, rejected, failed, and successful consequential actions are attributable.
- [x] Successful state and audit append commit atomically; a rolled-back race records its denial in a fresh transaction.
- [x] Application roles/routes cannot update or delete audit records.
- [x] Audit reads are resource-authorized and payloads/logs are redacted.
- [x] Source categories, confidence, validity, confirmation, and sensitivity are validated.
- [x] Inferences/predictions cannot overwrite or masquerade as observed/confirmed facts.

## Runtime and web

- [x] Default bind is `127.0.0.1`; UI persistently labels local/mock/synthetic mode.
- [x] Live/unknown provider mode and credential-shaped configuration fail startup.
- [x] CORS is local allowlisted; protected responses are `no-store`.
- [x] Untrusted captured/provider strings render inertly; no generic mass-assignment route exists.
- [x] Mock adapters make no provider network calls.
- [x] Dependency and secret scans have no unresolved high/critical finding.

## Independent conclusion

- [x] Reviewer did not author the implementation under review.
- [x] Evidence records exact commands, exit codes, and material findings.
- [x] No critical/high ship blocker remains in the localhost/mock/synthetic scope.

`pip-audit` cannot resolve the local editable project itself against PyPI; it reported no known vulnerability in the installed third-party Python environment. Live-provider and production-identity review remains deliberately out of scope.

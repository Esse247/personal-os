# Security, privacy, and threat model

## Scope and posture

Foundation v0.1 is a localhost, synthetic-data, mock-adapter demonstration. It is not production authentication or a production security claim. Services bind to `127.0.0.1`; live provider selection and unknown modes fail startup.

## Assets and trust boundaries

Protected assets include personal/household records, schedules, financial/health/identity data, consent grants, approvals, audit history, provider credentials (future), and user attention. Boundaries exist at browser/API, identity/policy, application/domain, database, worker, model/agent context, and provider adapter interfaces.

All captured text, model output, provider content, transaction memos, file content, and client-supplied ownership/role fields are untrusted.

## Primary threats and controls

| Threat | Impact | Required controls |
|---|---|---|
| Household or object-level data exposure | Critical | Server-side resource authorization; membership is never consent; non-enumerating denial; audit views use the same policy. |
| Agent/model authority laundering | Critical | Task-scoped delegation; typed command pipeline; agents request but cannot grant/approve authority. |
| Approval mutation/replay/TOCTOU | Critical | Exact payload digest, actor/version/expiry/policy binding, one-time claim, reauthorization before execution. |
| Accidental mock/live crossing | Critical | Only mock adapters registered; capability registry and persistent UI label; fail-closed startup; zero provider network calls. |
| Prompt injection or mass assignment | High | Treat content as data; strict schemas/known fields; no model repository access; ignore client identity/permission claims. |
| Retry/worker duplicate action | High | Transactional outbox; unique consumer receipt/effect; atomic delivery audit/state; bounded retry; policy recheck after claim and before effect. |
| Expired worker completes after reassignment | High | Database-time lease, unguessable fencing token, current owner/token/expiry predicates, stale-worker rollback. |
| Queued payload leaks sensitive source data | High | Finite versioned event catalog, allowlisted scalar payload keys, size bounds, ownership/sensitivity envelope, no raw text/credentials/provider payload. |
| Audit tampering or leakage | High | Append-only port, no mutation route, redacted structured payloads, resource-level read authorization. |
| Inference masquerades as fact | High | Distinct source type, input provenance, confidence and confirmation; no destructive overwrite. |
| Stored XSS/CSRF/localhost abuse | High | React output encoding, origin allowlist, development identity, no-store data, body limits, no generic write routes. |
| Consent revoked after context/job creation | High | Revoke dependent grants/delegations/approvals/jobs and recheck at each use. |

## Central authorization

All queries, commands, jobs, tool calls, audit reads, and notification decisions use:

`authorize(auth_context, permission, resource_ref, purpose) -> decision + rule_id`

`auth_context` is server-created and includes principal plus delegation chain. Default deny; deny overrides allow. Model output cannot introduce permissions. Household admins can manage membership without gaining private payload access.

Private records carry data subject/controller, household context where relevant, visibility, sensitivity, provenance, and version. Sharing requires an active grant that names grantor, grantee, resource/fields/actions, purpose/channels, category, issue/expiry/revocation, and provenance.

## Web and runtime containment

- Synthetic development identity comes from server configuration, not trusted client IDs.
- Mutation routes accept explicit commands and idempotency keys; no generic patch/status endpoint.
- CORS permits only local frontend origins; sensitive responses are `no-store`.
- Unknown/live provider modes, real credential-shaped environment configuration, and Level 4/5 execution fail closed.
- PostgreSQL startup requires the exact Alembic head; application `create_all` is refused.
- The v0.2 worker registry accepts only local internal Level 3 handlers. Failed work is
  owner-scoped, explicit recovery is separately authorized, and stale fencing rolls back
  effect, receipt, audit, and state together.
- Logs exclude credentials, raw account identifiers, sensitive free text, and stack traces in client responses.
- Mock content containing HTML/script must render inertly.

## Abuse cases that must remain tested

Cross-person IDOR through primary APIs, search/counts/dashboard/audit; household co-membership access; forged owner/role/action level; malicious transaction memo; specialist scope expansion; mutated/replayed/stale approval; duplicate worker delivery; queued action after consent revocation; ambiguous input inventing facts; scheduler restoring a rejected proposal; UI stored XSS; environment silently selecting live mode.

## Ship blockers

Any live credential/data/provider/side effect; non-local default binding; unauthenticated write; implicit household access; non-central authorization; model direct write; mutable/reusable approval; unaudited consequential mutation; mutable audit history; provider fail-open; capability-status mismatch; inference overwriting fact; failed permission/provenance/approval/ambiguity/provider/audit/isolation tests; or unresolved high-impact dependency/secret finding blocks completion.

## Deferred security decisions

Production identity/session and reauthentication, key/secret broker, encryption/key rotation, retention/export/deletion, consent UX, multi-person approval authority, production deployment perimeter, formal dependency/penetration review, and externally anchored audit integrity are deliberately deferred.

# Risk register

| ID | Risk | Impact / likelihood | Mitigation and evidence gate | Status |
|---|---|---|---|---|
| R-001 | Household membership leaks another person’s data or metadata. | Critical / medium | Default-deny resource policy, explicit grants, cross-person API/dashboard/audit tests. | Mitigated and verified for v0.1 |
| R-002 | Mock capability is mistaken for live or a live adapter starts accidentally. | Critical / medium | Mock-only registry, startup fail closed, persistent UI status, no-network tests, truthful specs. | Mitigated and verified for v0.1 |
| R-003 | Model/provider content changes authoritative state or authority. | Critical / medium | Typed proposal/command boundary, architecture scan, schema/state tests. | Mitigated and verified for v0.1 |
| R-004 | Approval is stale, mutated, replayed, or self-approved. | Critical / medium | Digest/version/actor/expiry binding, one-time claim, policy recheck, tests. | Mitigated and independently verified |
| R-005 | Audit history is incomplete, mutable, or privacy-leaking. | High / medium | Atomic append port, no mutation API, read authorization/redaction tests. | Mitigated and independently verified |
| R-006 | Scheduler over-optimises or violates hard constraints/buffers. | High / medium | Pure feasibility rules, protected unstructured time, deterministic conflict/override tests. | Mitigated and verified for v0.1 |
| R-007 | Ambiguous intent invents deadline, attendee, or action. | High / medium | Missing-field result and no-commitment test; confirmed world fact only. | Mitigated and verified for v0.1 |
| R-008 | Financial amount/category corrupts source data. | High / low | Minor units, immutable import, versioned deterministic classification, tests. | Mitigated and verified for v0.1 |
| R-009 | Local SQLite behavior diverges from PostgreSQL. | Medium / medium | SQLAlchemy/Alembic, portable schema, Compose/PostgreSQL integration gate before pilot. | Accepted for v0.1; tracked |
| R-010 | Dependency or setup drift prevents reproducibility. | Medium / medium | Locks, scripts, clean setup evidence, Docker path, version bounds. | Mitigated; dependency-free-copy setup verified |
| R-011 | Broad domain scope produces shallow/unverified scaffolding. | High / medium | Implement only required vertical slice; document remaining entities/contracts. | Mitigated for v0.1 by bounded vertical slice |
| R-012 | Local development identity is mistaken for authentication. | High / medium | Visible local-only status, localhost bind, ADR and non-goal, production deployment prohibited. | Accepted for v0.1 |
| R-013 | Captured/provider text creates stored XSS or log injection. | High / medium | React encoding, structured logging/redaction, malicious fixture test. | Mitigated and verified for v0.1 |
| R-014 | Unsupported completion claim is made without running demo/build/tests. | High / medium | Evidence gate skill, active checklist, independent acceptance, continuity validator. | Mitigated by final evidence and independent acceptance |
| R-015 | A model-led quality loop self-approves, changes its own success criteria, or continues without bound. | High / medium | Pre-baseline hashed contract, inert validator, independent review, stable failure keys, three-repair default, and mandatory stop/escalation rules. | Mitigated and independently verified |

# Open questions

Conservative defaults apply until these decisions receive explicit product and security design.

| ID | Question | Current safe default | Target phase |
|---|---|---|---|
| OQ-001 | What exact records/fields may a person share with a household, for which purposes? | Private by default; explicit field/resource/action/purpose/time-scoped grant. | pre-pilot Identity, Consent & Data Lifecycle |
| OQ-002 | Who may approve an action that affects multiple people? | Every affected person’s authority is required; no household-admin bypass. | pre-pilot Identity, Consent & Data Lifecycle |
| OQ-003 | What production identity, session, recovery, and reauthentication mechanisms apply? | Synthetic localhost identity only; no production deployment. | pre-pilot Identity, Consent & Data Lifecycle |
| OQ-004 | What are retention, deletion, export, and legal-hold policies? | No real data; minimise fixtures/logs and keep no secrets. | pre-pilot Identity, Consent & Data Lifecycle |
| OQ-005 | What authentication strength is required for Level 5 actions? | Level 5 prohibited. | pre-Level-5 |
| OQ-006 | Is SQLite acceptable beyond the local demo? | Resolved by ADR 0012: PostgreSQL defines production semantics; SQLite is lightweight local/test only. | resolved in v0.2 |
| OQ-007 | Which first provider is eligible for a consented read-only pilot? | None; all are mock/planned. | v0.3 |
| OQ-008 | How should rejected schedule suggestions decay or remain excluded? | The exact rejected proposal is not silently recreated; ask/recalculate on material new input. | future scheduling hardening |
| OQ-009 | What accessibility conformance target and supported browser/device matrix apply? | Semantic keyboard-usable responsive foundation; formal target deferred. | future UX/release hardening |

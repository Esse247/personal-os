# Open questions

Conservative defaults apply until these decisions receive explicit product and security design.

| ID | Question | Current safe default | Target phase |
|---|---|---|---|
| OQ-001 | What exact records/fields may a person share with a household, for which purposes? | Private by default; explicit field/resource/action/purpose/time-scoped grant. | v0.2 |
| OQ-002 | Who may approve an action that affects multiple people? | Every affected person’s authority is required; no household-admin bypass. | v0.2 |
| OQ-003 | What production identity, session, recovery, and reauthentication mechanisms apply? | Synthetic localhost identity only; no production deployment. | v0.2 |
| OQ-004 | What are retention, deletion, export, and legal-hold policies? | No real data; minimise fixtures/logs and keep no secrets. | v0.2 |
| OQ-005 | What authentication strength is required for Level 5 actions? | Level 5 prohibited. | pre-Level-5 |
| OQ-006 | Is SQLite acceptable beyond the local demo? | No; PostgreSQL is the intended durable runtime. | v0.2 |
| OQ-007 | Which first provider is eligible for a consented read-only pilot? | None; all are mock/planned. | v0.3 |
| OQ-008 | How should rejected schedule suggestions decay or remain excluded? | The exact rejected proposal is not silently recreated; ask/recalculate on material new input. | v0.2 |
| OQ-009 | What accessibility conformance target and supported browser/device matrix apply? | Semantic keyboard-usable responsive foundation; formal target deferred. | v0.2 |

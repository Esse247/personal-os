# Domain model

## Modeling rules

Important nouns have typed identities and explicit state. Not every noun is an aggregate root. Transitions occur through named commands, not arbitrary patches. Authoritative records are never silently deleted to imply completion. All fact-like data carries provenance and ownership/visibility metadata.

## Core catalog

| Entity | Foundation role |
|---|---|
| User | Authenticated system principal; synthetic development identity in v0.1. |
| Person | Human data subject; privacy boundary independent of `User`. |
| Household | Coordination container, never an implicit data-access grant. |
| Goal / Project / Task | Outcomes, bounded initiatives, and executable work. |
| Commitment | Promised outcome that must reach an explicit disposition. |
| Intent | Captured statement plus structured interpretation or clarification need. |
| Observation | Tool-observed input that retains source and time. |
| Inference | Derived claim with inputs, confidence, and confirmation state. |
| WorldFact | Active knowledge claim with provenance, validity, and supersession. |
| CalendarEvent | Provider-neutral observed or proposed event. |
| ScheduleBlock | Internal allocation of time; not automatically an external event. |
| Constraint / Preference / Routine | Hard rule, soft choice, and repeatable pattern. |
| Notification | Centrally mediated attention request. |
| Agent / AgentRun | Bounded capability identity and attributable execution. |
| Tool / ToolAction | Declared capability and gated attempted action. |
| Approval | Human decision bound to one immutable action/proposal revision. |
| Integration | Provider configuration and truthful capability mode. |
| FinancialAccount / Transaction / Budget | Exact-money source records and planning. |
| HouseProject / Contractor / Quote / Invoice / Milestone | House-build coordination records. |
| HealthSignal | Sensitive observation contract only; no v0.1 implementation. |
| AuditEvent | Append-only attributable record of allowed, denied, and failed actions. |
| CandidateInsight | Planned permission-scoped opportunity/risk hypothesis with evidence, expected value, urgency, confidence, expiry, and specialist routing; not yet implemented. |
| ExecutiveSynthesis | Planned Chief-of-Staff contract combining bounded specialist assessments into priorities and preparation/action proposals; never an authority grant. |
| OutcomeVerification | Planned expected-versus-observed action evidence and result status. |
| LearningRecord | Planned provenance-bearing conclusion from verified behaviour/outcomes; cannot silently change permission or fact authority. |
| OutboxEvent | Versioned, redacted internal delivery envelope committed atomically with authoritative state and audit in v0.2. |

## Aggregate transitions

### Intent

`captured -> needs_clarification -> structured -> committed`

`captured|needs_clarification|structured -> dismissed`

Structured requires validated fields and explicit provenance for resolved facts. Missing required facts produce one clarification request and no commitment or schedule.

### Commitment

Interim `captured` must eventually become one of: `completed`, `scheduled`, `delegated`, `waiting`, or `deliberately_abandoned`.

- `scheduled` requires an approved internal block reference.
- `delegated` requires a responsible party and review date.
- `waiting` requires a reason and review date.
- `deliberately_abandoned` requires actor and reason.
- User override may reschedule or move a commitment to waiting; it is never treated as punishment/failure.
- No delete command exists.

### ScheduleProposal

`proposed -> approved | rejected | superseded | expired`

A requested change supersedes the old revision and creates a new proposal. Approval binds the proposal version and input snapshot hash; stale approvals fail.

### ScheduleBlock

`tentative -> confirmed -> completed | cancelled`

The v0.1 block is an internal Level 3 write. External calendar creation would be a distinct Level 4 tool action and is prohibited in this phase.

### Approval

`requested -> approved | rejected | expired | cancelled`

Future external execution introduces `executing -> succeeded | failed`. Approval is one-time, expiring, actor-bound, payload-digest-bound, and policy/version-bound.

### ToolAction

`planned -> awaiting_approval -> authorized -> running -> succeeded | failed | cancelled | rolled_back`

Only the authorization gate may enter `authorized`. Level 4/5 live execution is unavailable in v0.1.

### AgentRun

`queued -> running -> waiting_for_approval | succeeded | failed | cancelled`

Runs have bounded steps/time, task-scoped delegation, and no self-enqueue loop. Specialists emit activity/proposals, not direct notifications.

### Transaction classification

Imported transaction fields remain immutable. Classification revisions are append-only: `proposed -> confirmed | corrected | rejected`. Deterministic rule ID, confidence, source, and actor are retained.

### Knowledge claim

`active -> confirmed | disputed | superseded | expired`

`SYSTEM_INFERRED` and `SYSTEM_PREDICTED` claims never overwrite `USER_STATED` or `TOOL_OBSERVED` claims. A higher-confidence claim is still not permission or consent.

### Candidate insight and executive synthesis (planned contracts)

`observed -> candidate -> assessed -> prepared | deferred | rejected | expired | superseded`

A candidate requires evidence references, owner/controller and data-subject scope,
sensitivity, expected value, urgency, confidence, affected domains, and expiry/review time.
It is not a notification, approval, fact, or action. Executive synthesis retains each
specialist input and its provenance, records cross-domain trade-offs, and can emit only a
preparation or gated action proposal. Neither contract expands permission.

### Outcome verification and learning (planned contracts)

`expected -> observing -> verified | partially_verified | failed | inconclusive`

Learning consumes verified evidence and remains attributable and reversible/supersedable.
It may adjust future ranking or preparation only through an explicit rule/version; it never
converts confidence into consent, authority, or an observed fact.

## Cross-aggregate invariants

- All records have stable IDs, UTC timestamps, owner/data-subject scope where relevant, and optimistic versions.
- Every command has actor, correlation ID, and idempotency key.
- State and its audit event commit atomically.
- Money is integer minor units and ISO currency.
- Schedule intervals are half-open and cannot overlap hard constraints.
- Household membership cannot satisfy a private-resource authorization predicate.
- A model, provider, adapter, agent, or UI cannot directly mutate an aggregate.

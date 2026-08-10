# Product source of truth

## Relationship model

The intended coordination path is:

`USER <-> CHIEF OF STAFF <-> SPECIALIST AGENTS / TOOLS`

The Chief of Staff may aggregate proposals and notification intents. Specialists never independently expand scope, approve actions, write authoritative state, or overwhelm the user with direct notifications.

## Foundation users

- A root user using a synthetic local persona.
- Synthetic household people whose private data remains isolated without explicit consent.
- Developers validating the architecture without production credentials.

`User` is an authenticated system identity. `Person` is a human data subject. They are not interchangeable.

## Required demonstration A: haircut commitment

1. Capture: “I need a haircut before the wedding next month.”
2. Persist the raw statement as `USER_STATED` provenance.
3. Resolve “the wedding” only from a confirmed synthetic world fact; otherwise ask for clarification.
4. Create a validated structured intent and commitment.
5. Read availability from a mock calendar snapshot.
6. Deterministically propose a feasible schedule block with buffer and rationale.
7. Display it on the dashboard and approval queue.
8. Allow approve, change, or reject; a change creates a new revision, and rejection leaves the commitment actionable.
9. Append an attributable event for each transition.

## Required demonstration B: synthetic finance

1. Load an immutable synthetic house-project transaction.
2. Categorise it with an explicit deterministic rule or mock provider.
3. Display amount, currency, project linkage, category, source, confidence, and capability mode.
4. Preserve the imported source and append classification/audit history.
5. Make no live banking request or financial action.

## Ambiguous input

An input such as “Book something next month” lacks an object and usable constraints. It must become an intent in `needs_clarification`; it must not create a commitment, deadline, attendee, calendar event, or invented fact.

## Dashboard foundation

The responsive local interface contains Now, Today, Current primary project, Commitments, Schedule, Capture, Projects, synthetic Household/house finance, Agent/activity history, Approval queue, and System status. Mock/synthetic status is persistent and explicit.

## Non-goals

Production authentication, multi-device sync, live PWA push, real integrations, autonomous execution, model quality optimization, payment initiation, health guidance, house-project procurement, and complete CRUD for every future entity are deferred.

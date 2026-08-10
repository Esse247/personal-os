# Product source of truth

## Product North Star

PERSONAL OS is a private, proactive personal and household AI organisation. It remembers
intentions, goals, commitments, and context; observes authorised signals; notices risks,
needs, and opportunities; coordinates bounded specialist functions; prepares useful work;
acts only within explicit authority; verifies outcomes; and learns from real behaviour and
results.

Its defining user experience is:

> The assistant noticed, prepared, or completed something genuinely useful that I had not
> thought to ask for.

The product must actively improve progress, wealth, time, knowledge, health, opportunity,
and completion of meaningful work. Safety and privacy are necessary operating constraints,
not the whole product value. The system is not a stream of simulated thoughts and does not
run models continuously merely to appear intelligent.

The permanent operating principle is:

**ALWAYS OBSERVING · SELECTIVELY REASONING · PROACTIVELY PREPARING · SAFELY ACTING ·
CONTINUOUSLY LEARNING**

## Relationship model

The intended coordination path is:

`USER <-> CHIEF OF STAFF <-> SPECIALIST AGENTS / TOOLS`

The Chief of Staff may aggregate proposals and notification intents. Specialists never independently expand scope, approve actions, write authoritative state, or overwhelm the user with direct notifications.

All specialists use one shared permission-controlled world model. Structured contracts
carry observations, candidate insights, proposals, executive briefs, action requests,
verification evidence, and learning outcomes. The Chief of Staff is the executive synthesis
layer: it makes cross-domain priority judgements and coordinates specialists, but it does
not override deterministic permission, approval, provenance, or audit rules.

## Proactive operating loop

1. Persist intentions, commitments, authorised observations, and outcome evidence with
   ownership, provenance, sensitivity, and validity.
2. React to meaningful events and state changes; do not generate fixed-frequency random
   thoughts or continuous high-frequency LLM calls.
3. Form bounded `CandidateInsight` records containing expected value, urgency, confidence,
   evidence references, affected domains, sensitivity, and an expiry/review point.
4. Route only worthwhile candidates to relevant specialists and then to an
   `ExecutiveSynthesis` contract that can combine cross-domain trade-offs.
5. Prepare a proposal or artifact. Low-risk reversible actions require valid standing
   permission; consequential actions enter the approval queue.
6. Record expected evidence, execute through an allowlisted provider-neutral capability,
   verify the actual result, and retain learning evidence without silently expanding
   future authority.

Candidate insights and executive synthesis are durable, permission-scoped contracts—not
notifications, approvals, facts, or actions. They may be deferred, rejected, superseded,
or expire without disturbing authoritative source records.

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

For the accepted Foundation baseline and active Persistence & Execution v0.2 scope,
production authentication, multi-device sync, live PWA push, real integrations,
autonomous specialist execution, continuous model polling, model quality optimization,
payment initiation, health guidance, house-project procurement, and complete CRUD for
every future entity are deferred. These phase boundaries do not reduce the long-term North
Star; they keep each authority and reliability layer evidence-driven.

# Project charter

## Mission

Build the ultimate proactive personal and household assistant: a private AI organisation
that understands the user's authorised world, coordinates specialist capabilities, and
helps before, during, and after the user explicitly asks. It exists to increase meaningful
progress, wealth, time, knowledge, health, opportunity, and completed work without taking
away user authority, privacy, or control.

The intended experience is: **the assistant noticed, prepared, or completed something
genuinely useful that the user had not thought to ask for.**

This is not primarily a cognitive simulation and must not generate constant random
thoughts. Its operating principle is:

**ALWAYS OBSERVING · SELECTIVELY REASONING · PROACTIVELY PREPARING · SAFELY ACTING ·
CONTINUOUSLY LEARNING**

Observation means permission-scoped, event-driven intake from authorised sources—not
continuous surveillance or high-frequency model calls. Learning means explicit evidence
from actual behaviour and verified outcomes—not silent authority expansion.

## Foundation v0.1 scope

This phase establishes project memory, explicit domain and security boundaries, provider-neutral contracts, a local mock-only application, two synthetic end-to-end flows, and executable verification. It is deliberately not a broad product implementation.

Foundation v0.1 remains the accepted product baseline. Persistence & Execution Foundation
v0.2 strengthens PostgreSQL semantics and safe event delivery only; it does not add live
signals, unrestricted agents, or external actions.

## Long-term operating model

One permission-controlled world model supports intentions, goals, commitments, context,
and authorised calendar, financial, project, household, communication, health, and
environmental observations. Specialists analyse bounded views and exchange structured
observations, candidate insights, proposals, and evidence. A Chief of Staff layer performs
cross-domain executive synthesis, prioritises attention, coordinates preparation, and
routes actions through deterministic authority gates.

The system progresses through an event-driven loop:

`authorised signal -> candidate insight -> selective specialist reasoning -> executive synthesis -> preparation/action proposal -> permission or approval -> execution -> outcome verification -> learning evidence`

Low-risk reversible actions may eventually run under explicit standing permission.
Consequential actions require approval. Every action must define expected evidence and be
verified afterward. Provider and model choices remain neutral and replaceable.

## Product promises

1. The human remains sovereign and can approve, change, reject, or abandon proposals.
2. Deterministic code owns authoritative state, permissions, arithmetic, constraints, and execution.
3. Models and agents interpret and propose through validated contracts; they are never databases or implicit authorities.
4. Every consequential transition is attributable, provenance-bearing, and auditable.
5. Personal data is private by default. Household membership alone grants no payload access.
6. Provider, tool, and model choices remain replaceable.
7. Rest, buffers, spontaneity, and creative exploration are first-class scheduling requirements.
8. Proactivity is selective and value-driven; specialist activity does not become an
   unbounded notification stream or autonomous self-enqueue loop.
9. The shared world model is permission-filtered at every read and action boundary.
10. Specialists communicate through typed contracts; the Chief of Staff owns executive
    synthesis, while deterministic policy owns authority.

## Phase boundaries

The accepted Foundation baseline and active v0.2 work contain no real credentials,
personal data, production authentication, live provider SDKs, outbound provider actions,
payments, health decisions, legal actions, or uncontrolled agent loops. Capability status
must distinguish `planned`, `mocked`, `implemented`, `live`, and `prohibited` truthfully.

## Success

Success requires an installable and testable local repository, working mock demonstration flows, independently reviewed security/permission and architecture boundaries, accurate status/evidence/handoff records, and no unresolved high-impact foundation defect.

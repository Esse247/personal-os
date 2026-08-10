# Scheduling engine

## Separation of responsibilities

Language interpretation may propose a scheduling request. A deterministic component alone validates feasibility, detects conflicts, ranks candidates, creates proposals, and recalculates after change.

## Inputs

- Hard constraints: fixed events, availability, deadlines, required dependencies, consent/policy.
- Soft preferences: time of day, energy suitability, location/context, focus/transition preference.
- Work attributes: effort estimate, priority, project, interruption cost, dependencies.
- Humane capacity: pre/post buffers, protected rest, unstructured time, maximum planned load.
- Current reality: present time, current calendar snapshot/version, completed work, user overrides.

All time uses timezone-aware values; stored times are UTC and intervals are half-open.

## Algorithm for v0.1

1. Resolve deadline and duration only from confirmed facts/preferences.
2. Intersect mock availability with the planning horizon.
3. Remove hard-conflict intervals and apply buffers.
4. Reject candidates that exceed deadline or protected/unstructured capacity.
5. Score feasible candidates by explicit soft preferences, energy/context fit, interruption cost, and earliest useful completion.
6. Use stable deterministic tie-breaking.
7. Persist a proposal with rationale, input snapshot hash/version, provenance, and alternatives count.

If no feasible slot exists, return an explanation/clarification need, never an invalid block.

## Decisions and overrides

Approval re-reads the current calendar snapshot and revalidates its provider/version/hash binding, feasibility, confirmed blocks, hard constraints, proposal version, and payload digest before creating a reversible internal ScheduleBlock. Proposal and commitment updates use database compare-and-swap; block persistence adds commitment and exact-interval uniqueness as a concurrent guard. A losing database race rolls back its staged success state and records a denial audit in a fresh transaction. A change supersedes the old proposal and recalculates from present reality. A rejection is remembered; automatic recalculation cannot silently restore the rejected proposal. Schedule deviation is new input, not failure.

## Deferred capabilities

Recurring multi-user optimization, travel-time integration, DST property suites across all zones, stochastic duration, solver-based global optimization, production calendar writes, and adaptive energy prediction are later phases.

# UX and notification principles

## Interaction principles

- Show the user what the system believes, why, where it came from, and what will happen next.
- Make approve, change, reject, undo/recovery, and deliberate abandonment obvious.
- Treat override as a normal signal that triggers recalculation, not as non-compliance.
- Keep planned, mocked, implemented, live, inferred, predicted, and confirmed states visibly distinct.
- Preserve whitespace in time: buffers, rest, spontaneity, and creative exploration are not “unused capacity.”
- Keep the immediate “Now” view calm; disclose detail progressively.
- Use accessible labels, keyboard focus, readable contrast, responsive layout, and inert rendering of untrusted text.

## Dashboard hierarchy

The header persistently shows `LOCAL / MOCK / SYNTHETIC`. Now and Today lead. Current project, commitments, schedule, and approval queue support decisions. Capture is always accessible. Finance and activity show provenance/confidence without suggesting a live account connection. System status describes adapter modes and deferred capabilities truthfully.

## Notification policy

Specialist agents emit notification intents only. The Chief of Staff notification policy deduplicates, rates, schedules, respects quiet hours and sensitivity, prefers digests, and chooses the least disruptive channel. Notification content minimises sensitive detail. Foundation v0.1 records mock notification activity and sends nothing externally.

## Failure presentation

Denied, ambiguous, stale, infeasible, and failed operations remain visible with a plain-language next step. The UI never reports success before committed state and evidence exist.

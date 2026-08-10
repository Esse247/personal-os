# ADR 0009: Deterministic scheduling and financial computation

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

Language models may interpret an intent or propose a classification. Deterministic code validates schedule constraints/conflicts, ranks feasible slots, performs money arithmetic, and applies auditable categorization rules. Store money as integer minor units plus ISO currency; use timezone-aware half-open schedule intervals.

## Consequences

Results are repeatable and testable. The scheduler must preserve buffers and unstructured time, explain infeasibility, and recalculate from current reality after override. Imported transactions remain immutable; classification is versioned.

# Model routing

## Principle

Models interpret, reason, summarise, and propose. They do not own truth, permissions, arithmetic, scheduling feasibility, or execution. The application selects a provider through `ModelProvider`; provider names never appear in domain logic.

## Routing inputs

The deterministic router considers task type, required capability, action risk, data sensitivity/privacy policy, latency budget, cost budget, context size, structured-output requirement, and confidence/evaluation requirement. It can select a mock provider, a future eligible provider, or `no_model`.

## Foundation policy

Foundation v0.1 registers only a deterministic mock interpreter. It recognises the narrow demonstration fixtures, returns a typed proposal and uncertainty/missing-fields list, and cannot directly issue a domain command. Unknown or ambiguous inputs require clarification.

## Future safeguards

- Minimise and permission-filter context before provider selection.
- Never treat provider text or confidence as approval.
- Validate schema, size, identifiers, provenance references, and allowed fields.
- Record selected policy/routing rationale, not hidden chain-of-thought.
- Apply task/time/step/cost limits to every agent run.
- Evaluate quality and safety before a model/provider becomes eligible for a risk tier.
- Provide deterministic fallback or human clarification when confidence is insufficient.

# ADR 0011: Bounded evidence-driven quality gauntlet

- **Status:** Accepted
- **Date:** 2026-08-10

## Context

Meaningful milestones need a repeatable way to define success, combine deterministic evaluation with calibrated review, repair confirmed failures, and stop without unbounded agent loops. The workflow must preserve the repository source hierarchy and cannot turn model opinion or a typed result into authority.

Official OpenAI guidance recommends concise layered `AGENTS.md` instructions, success criteria defined before difficult iterative work, machine-readable run evidence, focused changes with explicit stopping rules, reusable skills for repeated workflows, and task-specific evals that prefer automation over vague judgment:

- [AGENTS.md configuration](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Iterate on difficult problems](https://learn.chatgpt.com/codex/use-cases/iterate-on-difficult-problems)
- [Save workflows as skills](https://learn.chatgpt.com/use-cases/reusable-codex-skills)
- [Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)

## Decision

Adopt a repository-scoped `quality-gauntlet` skill and versioned YAML contracts/runs under `quality/`. Define the contract before the baseline and bind each run to its contract ID, repository-relative path, and canonical SHA-256.

Use a default maximum of three repair iterations. Four or five require explicit pre-baseline justification and an approver; more than five is invalid. Each iteration selects one stable highest-severity failure, applies one focused repair, reruns targeted and relevant regression checks, and compares a deterministic severity vector with the best retained result. Stop with PASS, FAIL, or ESCALATE under documented conditions.

The validator is inert: it parses artifacts but never executes recorded commands, edits files, invokes agents, or applies repairs. It distinguishes structural validity from milestone acceptance and derives PASS eligibility from mandatory deterministic/regression results, unresolved severity, rubric thresholds, continuity reconciliation, and author-independent reviewer decisions. Deterministic failure always outranks model opinion.

Quality artifacts are evidence snapshots subordinate to the manifest, ADRs, specifications, active checklist, and continuity records. They do not independently change capability, phase, release, permission, or product truth.

## Consequences

Meaningful work gains measurable entry/exit conditions, stable failure identity, finite repair budgets, and auditable reviewer independence. Truthful FAIL and ESCALATE records remain structurally valid history. The protocol adds artifact maintenance, but trivial typo/format-only work and read-only answers do not invoke it unless explicitly requested.

# Evidence

Evidence is append-only by verification checkpoint. Planned commands do not count as results.

## 2026-08-10 — repository and design baseline

| Command or review | Exit/result | Material evidence |
|---|---:|---|
| Repository inventory (`Get-ChildItem`, `rg --files`) | 0 | Repository contained only empty `outputs/` and `work/`; no prior implementation or instructions to preserve. |
| Local toolchain inventory | mixed, recorded | Node `v22.14.0` and Git `2.48.1`; standard-shell Python and Docker unavailable. Bundled Python 3.12 and pnpm paths were located for development. |
| Independent architecture/domain pre-implementation review | review complete | Recommended modular monolith, inward dependencies, relational state plus append-only audit, mock-only provider contracts, deterministic scheduling/finance, and a narrow vertical slice. This was design input, not implementation approval. |
| Independent security/privacy pre-implementation review | review complete | Identified household isolation, action-bound approvals, centralized policy, mock/live fail-closed behavior, provenance, and audit immutability as ship gates. This was design input, not implementation approval. |
| Independent verification-design review | review complete | Defined unit/integration/demo acceptance for transitions, ambiguity, providers, permissions, audit, fixtures, dashboard, and continuity. This was design input, not an executed test result. |

## Latest verification run

### 2026-08-10 — implementation checkpoint (pre-independent acceptance)

| Command | Exit | Material result |
|---|---:|---|
| Repo skill `quick_validate.py` for all four `.agents/skills/*` directories | 0 | All four skills reported `Skill is valid!`. |
| `npm run lint` | 0 | Ruff check/format and ESLint passed with no warnings. |
| `npm run typecheck` | 0 | Mypy reported no issues across 46 Python source/test files; strict TypeScript passed. |
| `npm test` | 0 | 23 backend unit tests, 1 frontend test, and 10 backend integration tests passed. A dependency-origin Starlette/TestClient deprecation warning remains. |
| `npm run build` | 0 | Vite production build completed; 30 modules transformed, JS bundle 203.60 kB (63.91 kB gzip). |
| Migration integration test | 0 | Alembic applied from zero and a second upgrade was a no-op; required tables were present. |
| Fixture idempotency integration test | 0 | Two loads retained exactly two synthetic transactions (one per persona) and two finance audit events. |
| `npm run validate:continuity` | 0 | Manifest targets, authoritative sources, phase, handoff, evidence, numbered ADRs, and local links passed. Broken target/link/phase/evidence fixtures are covered by tests. |
| `npm run demo:verify` | 0 | Flow A committed intent, created revision 1 then revision 2, approved to `scheduled`, rejected a separate proposal to `waiting`, and verified audit actions; ambiguous input required clarification. Flow B returned deterministic materials category at 0.98 confidence with `TOOL_OBSERVED` source. Built frontend was served; live-capability list was empty. |
| In-app browser desktop + 375 px visual/interaction check | pass | All required regions rendered; capture, change, approval, and clarification worked; narrow layout had no horizontal overflow and sidebar was hidden; browser warning/error log was empty. |
| `npm install` during setup | 0 | 264 packages installed; npm reported 0 vulnerabilities. |

This is a first-party checkpoint, not final independent acceptance. Docker/PostgreSQL runtime was not executed because Docker is unavailable on this machine.

## 2026-08-10 — final Foundation v0.1 acceptance checkpoint

Checkpoint recorded at `2026-08-10T18:50:28Z`. This section supersedes the earlier test counts without rewriting that historical checkpoint.

| Command or review | Exit/result | Material evidence |
|---|---:|---|
| Dependency-free temporary copy, then `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -BootstrapPython C:\Users\TheLo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` | 0 | Created a new virtual environment, installed the editable backend plus declared audit tooling and 264 npm packages, applied migrations, loaded deterministic fixtures, passed setup self-check, and reported zero npm vulnerabilities. Python was supplied explicitly because this machine's `python` command is only the Windows Store alias. |
| `npm.cmd run verify` in the dependency-free temporary copy | 0 | Clean environment passed Ruff/format, ESLint, mypy over 47 files, strict TypeScript, 26 backend unit tests, 1 frontend test, 19 integration tests, production build, continuity validation, and both-flow demo verification. The command completed in 65.5 seconds. |
| `npm.cmd run verify` in the authoritative workspace after the race-denial remediation | 0 | The same full surface passed in 30.2 seconds. Vite transformed 30 modules; output JavaScript was 203.60 kB (63.91 kB gzip). Demo reported `local-mock-synthetic`, no live capabilities, scheduled/changed/rejected flow A, clarified ambiguity, and deterministic finance flow B. |
| `node scripts/python.mjs -m pytest backend/tests/integration/test_persistence.py -q` | 0 | 6 persistence tests passed, including a forced losing approval transaction proving rollback plus a durable fresh-transaction denial audit. |
| Independent public-API approval-race probe | accept | Two file-backed SQLite approval requests returned `[200, 409]`, produced one block, no server error, and exactly one `schedule.decision_denied` event with `denied:concurrent-or-duplicate-write`. |
| `npm.cmd run audit:dependencies` (independent rerun) | 0 | `pip-audit` reported no known vulnerability in the installed third-party Python environment; the local editable `personal-os` project was explicitly skipped because it is not a PyPI package. `npm audit` reported zero vulnerabilities. |
| Scoped `rg` credential-material scan excluding `.git`, dependencies, caches, work, outputs, and lockfile | 0 | No OpenAI/GitHub/AWS credential prefix or private-key material matched. The declared Compose password remains explicitly synthetic/local-only and is not a provider credential. |
| Independent architecture acceptance | accept | Fresh full verification passed plus an 11-test focused boundary suite covering replay/mutation, scheduling constraints, CAS/race denial, stale snapshots, migrations, correlation, provider contracts, fail-closed configuration, capability parity, and worker policy. No architecture ship blocker remained. |
| Independent security acceptance | accept | 45 backend tests and 1 frontend test passed; focused public-API negative probes passed. No Critical/High security ship blocker remained in the localhost/mock/synthetic scope. |
| Independent evidence acceptance | accept | Fresh aggregate, replay/mutation, persistence/migration/fixture, forced race-denial, fail-closed configuration, capability parity, clean-copy continuity, setup check, four skill validations, dependency audits, and authoritative-record reconciliation passed. No unsupported Foundation completion claim remained. |
| In-app browser desktop and 375 px verification | pass | Required dashboard regions and capture/change/approve/clarification interactions rendered correctly, focus/labels were usable, no narrow-layout overflow appeared, and the browser console had no warning/error. |

Known non-blocking output is limited to dependency-origin Starlette/TestClient and Python 3.12 SQLite datetime-adapter deprecation warnings. Docker was not installed, so PostgreSQL/Compose runtime remains unexecuted and is a mandatory pre-pilot gate. Production identity, live providers, real data, and external actions remain prohibited rather than deferred as hidden implementation claims. Credential-shaped strings in configuration tests are intentional negative fixtures, not real credentials.

## 2026-08-10 — post-acceptance operating hardening

Checkpoint recorded at `2026-08-10T19:58:05Z` for quality run `qg-20260810-operating-rules-run-001`. This is repository operating infrastructure; it does not reopen Foundation v0.1 or change a product capability.

| Command or review | Exit/result | Material evidence |
|---|---:|---|
| Pre-implementation success contract and baseline | recorded | Contract `qg-20260810-operating-rules` fixed measurable capability/regression/review criteria and a three-repair budget before implementation; its canonical SHA-256 is `bd055bbdf80f702d67402bacbae8ec38cbf4b507856031e377b3b508c33ef1d2`. Baseline `npm.cmd run verify` exited 0 with 26 backend unit, one frontend, and 19 integration tests. |
| Official OpenAI research review | complete | AGENTS layering, difficult-problem iteration, reusable-skills, eval-best-practice, and model-guidance sources informed the concise recovery map, predeclared success contract, machine-readable evidence, focused repairs, and explicit stopping rule recorded in ADR 0011. |
| Quality skill `quick_validate.py` | 0 | `.agents/skills/quality-gauntlet` reported `Skill is valid!`. |
| `.venv\Scripts\python.exe -m pytest backend\tests\unit\test_quality_validator.py backend\tests\unit\test_continuity_validator.py -q` | 0 | 36 focused tests passed in 0.83 seconds, including forged-vector, failed-regression, risk-routing, command-evidence, continuity-binding, budget-state, and lineage probes. |
| Pre-review `npm.cmd run validate:quality -- --require-pass qg-20260810-operating-rules-run-001` | expected 1 | The gate refused the active run because final disposition, required criteria, and independent reviewers were absent; structural validity did not become acceptance. |
| Independent continuity review (`russell-continuity`) | accept | AGENTS recovery/authority/instruction/boundedness rubric scored 15/16; 521 words, 32 nonblank lines, 4030 UTF-8 bytes, and all explicit local references resolved. No P0/P1 finding; Foundation remained accepted. |
| Initial independent gauntlet-architecture review | reject | Adversarial probes found one systemic P1 acceptance-derivation defect covering forged vectors, retained failed regressions, incomplete security routing, commandless deterministic PASS, and missing continuity binding. This became the third and final repair rather than being overridden by passing routine tests. |
| Final `npm.cmd run verify` after repair iteration 3 | 0 | In 28.5 seconds, Ruff/format/ESLint, mypy over 49 files, TypeScript, 57 backend unit tests, one frontend test, 19 integration tests, production build, quality, continuity, and both-flow mock/synthetic demo passed. `live_capabilities` remained empty. |
| Final independent gauntlet-architecture review (`faraday-gauntlet`) | accept | Eight selected adversarial probes and 36 focused tests passed; contract hash/path, failure lifecycle, regression retention, risk routing, command evidence, exhausted-budget review state, continuity binding, lineage, inertness, and structural-versus-PASS semantics were accepted. Rubric scored 15/16 with no P0/P1 finding. |
| `npm.cmd run validate:quality -- --require-pass qg-20260810-operating-rules-run-001` | 0 | Derived acceptance passed only after all mandatory/regression criteria, lifecycle vectors, rubric thresholds, independent reviewers, and reconciled continuity evidence satisfied the gate. |
| Final reconciled `npm.cmd run verify` | 0 | In 31.9 seconds, the final records and implementation passed lint, strict types, 57 backend unit tests, one frontend test, 19 integration tests, production build, quality, continuity, and both-flow mock/synthetic demo; `live_capabilities` remained empty. |

Residual P2 limitations are explicit: command execution and reviewer identity are attestational rather than cryptographically proven, and semantic risk-tag omission cannot be inferred reliably from free-text scope. Docker/PostgreSQL remains the unchanged pre-pilot evidence gate.

### Metric correction — 2026-08-10T20:04:35Z

The append-only reviewer/run text above records `4030` UTF-8 bytes for `AGENTS.md`. An independent final audit and a direct filesystem-byte check established the exact value as `4025`; the earlier value came from a text-decoding measurement and is superseded by this correction. The word count remains 521 and the nonblank-line count remains 32, so every policy threshold and review conclusion is unchanged.

| Command | Exit | Material result |
|---|---:|---|
| `node -e` direct `AGENTS.md` buffer/text metrics | 0 | `{"words":521,"nonblankLines":32,"utf8Bytes":4025}`. |

### Independent final evidence acceptance

The read-only evidence reviewer accepted the reconciled run after the metric correction. Its independent results were: derived quality PASS exit 0; continuity exit 0; all five skills valid; 36 focused tests pass; full verification exit 0 with 57 backend unit, one frontend, and 19 integration tests; exact capability parity with no live capability; and the unchanged PostgreSQL-first CI handoff. No P0/P1 unsupported claim remained. The two residual P2 limitations—attestational command/reviewer identity and unexecuted Docker/PostgreSQL runtime—remain explicit.

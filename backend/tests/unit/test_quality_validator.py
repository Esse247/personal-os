from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from scripts.validate_quality import (
    canonical_sha256,
    derive_pass_errors,
    validate_agents,
    validate_contract,
    validate_cross_run_lineage,
    validate_run,
)


def success_contract() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract_id": "contract-001",
        "goal": "Prove a bounded repository change.",
        "milestone": "operating-hardening",
        "created_at": "2026-08-10T20:00:00Z",
        "owner_role": "root-builder",
        "scope": {"in": ["quality policy"], "out": ["product behavior"]},
        "iteration_budget": 3,
        "criteria": [
            {
                "id": "CAP-001",
                "class": "capability",
                "description": "The requested capability works.",
                "mandatory": True,
                "severity_on_fail": "P1",
                "evaluator": "deterministic",
                "command": "recorded command only",
                "expected": "The check exits zero.",
            },
            {
                "id": "REG-001",
                "class": "regression",
                "description": "Existing behavior remains green.",
                "mandatory": True,
                "severity_on_fail": "P1",
                "evaluator": "deterministic",
                "command": "recorded regression only",
                "expected": "The regression exits zero.",
            },
            {
                "id": "REV-001",
                "class": "review",
                "description": "An independent reviewer accepts the change.",
                "mandatory": True,
                "severity_on_fail": "P1",
                "evaluator": "independent_review",
                "command": None,
                "expected": "The reviewer accepts.",
            },
        ],
        "required_reviewers": [{"role": "quality-review", "independent": True}],
        "stop_conditions": {
            "success": [
                "every mandatory criterion passes",
                "every regression passes",
                "every required reviewer accepts",
            ],
            "escalate": [
                "the same failure survives 3 repairs",
                "2 consecutive iterations produce no improvement",
                "the iteration budget is exhausted",
                "requirements conflict",
                "an external dependency or decision blocks progress",
                "a repair would violate a constraint",
            ],
        },
    }


def check(
    criterion_id: str,
    result: str = "PASS",
    *,
    exit_code: int | None = 0,
) -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "command": "recorded, never executed",
        "exit_code": exit_code,
        "result": result,
        "evidence": f"Recorded {result} evidence for {criterion_id}.",
    }


def iteration(
    number: int,
    before: list[int],
    after: list[int],
    assessment: str,
    *,
    failure_id: str = "F-001",
) -> dict[str, Any]:
    return {
        "number": number,
        "primary_failure_id": failure_id,
        "repair": {"author_id": "root-builder", "summary": "One focused repair."},
        "before": {"quality_vector": before, "evidence": "Before measurement."},
        "after": {"quality_vector": after, "evidence": "After measurement."},
        "assessment": assessment,
        "kept": assessment == "IMPROVED",
        "targeted_checks": [check("CAP-001")],
        "regression_checks": [check("REG-001")],
    }


def completed_run(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": "run-001",
        "contract_id": contract["contract_id"],
        "contract_path": "quality/contracts/contract.yaml",
        "contract_sha256": canonical_sha256(contract),
        "goal": contract["goal"],
        "milestone": contract["milestone"],
        "repository_revision": None,
        "workspace_state": "uncommitted",
        "started_at": "2026-08-10T20:00:00Z",
        "status": "COMPLETE",
        "builder_ids": ["root-builder"],
        "baseline": {
            "summary": "One P1 failure is confirmed.",
            "quality_vector": [0, 1, 0, 0],
            "checks": [check("CAP-001", "FAIL", exit_code=1), check("REG-001")],
        },
        "iterations": [iteration(1, [0, 1, 0, 0], [0, 0, 0, 0], "IMPROVED")],
        "final_checks": [check("CAP-001"), check("REG-001"), check("REV-001", exit_code=None)],
        "reviewers": [
            {
                "reviewer_id": "reviewer-one",
                "role": "quality-review",
                "independent": True,
                "disposition": "ACCEPT",
                "evidence": "Independent review accepted the evidence.",
            }
        ],
        "failures": [
            {
                "id": "F-001",
                "failure_key": "missing-capability",
                "criterion_ids": ["CAP-001"],
                "severity": "P1",
                "status": "RESOLVED",
                "attempts": 1,
                "discovered_iteration": 0,
                "resolved_iteration": 1,
                "summary": "The capability was absent.",
                "resolution": "The focused repair satisfied its check.",
            }
        ],
        "remaining_risks": [],
        "continuity": {
            "evidence_ref": "docs/EVIDENCE.md",
            "evidence_status": "RECONCILED",
            "build_status_ref": "docs/BUILD_STATUS.md",
            "build_status_status": "UNCHANGED_REVIEWED",
            "handoff_ref": "docs/HANDOFF.md",
            "handoff_status": "RECONCILED",
            "checklist_ref": "checklists/ACTIVE.md",
            "checklist_status": "UNCHANGED_REVIEWED",
        },
        "final_disposition": "PASS",
        "completed_at": "2026-08-10T20:10:00Z",
    }


def validate_pair(
    tmp_path: Path, contract: dict[str, Any], run: dict[str, Any]
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    contract_path = tmp_path / "quality/contracts/contract.yaml"
    run_path = tmp_path / "quality/runs/run.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "checklists").mkdir(exist_ok=True)
    (tmp_path / "docs/EVIDENCE.md").write_text(f"# Evidence\n\n{run['run_id']}\n", encoding="utf-8")
    (tmp_path / "docs/BUILD_STATUS.md").write_text("# Status\n", encoding="utf-8")
    (tmp_path / "docs/HANDOFF.md").write_text("# Handoff\n", encoding="utf-8")
    (tmp_path / "checklists/ACTIVE.md").write_text("# Checklist\n", encoding="utf-8")
    (tmp_path / "PROJECT_MANIFEST.yaml").write_text(
        "checklists:\n  active: checklists/ACTIVE.md\n", encoding="utf-8"
    )
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    contract_errors, criteria, reviewers = validate_contract(contract, contract_path, tmp_path)
    run_errors = validate_run(
        run,
        run_path,
        tmp_path,
        contract,
        contract_path,
        criteria,
        reviewers,
    )
    return contract_errors + run_errors, criteria, reviewers


def test_valid_completed_run_is_structurally_valid_and_derives_pass(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    errors, criteria, reviewers = validate_pair(tmp_path, contract, run)
    assert errors == []
    assert derive_pass_errors(run, contract, criteria, reviewers, "run-001", tmp_path) == []


def test_contract_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["contract_sha256"] = "0" * 64
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("contract_sha256: mismatch" in error for error in errors)


def test_run_contract_path_must_be_safe_and_resolve_to_loaded_contract(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["contract_path"] = "../contract.yaml"
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("contract_path: unsafe repository-relative reference" in error for error in errors)
    assert any("contract_path: does not resolve to loaded contract" in error for error in errors)

    other_path = tmp_path / "quality/contracts/other.yaml"
    other_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    run["contract_path"] = "quality/contracts/other.yaml"
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("contract_path: does not resolve to loaded contract" in error for error in errors)


def test_run_goal_milestone_and_optional_workspace_metadata_are_validated(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run.update(
        {
            "goal": "A different goal.",
            "milestone": "different-milestone",
            "repository_revision": "",
            "workspace_state": "unknown",
        }
    )
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("goal: does not match loaded contract" in error for error in errors)
    assert any("milestone: does not match loaded contract" in error for error in errors)
    assert any("repository_revision: must be a non-empty string" in error for error in errors)
    assert any("workspace_state: must be committed or uncommitted" in error for error in errors)


def test_budget_above_three_requires_justification_and_approver(tmp_path: Path) -> None:
    contract = success_contract()
    contract["iteration_budget"] = 4
    errors, _, _ = validate_contract(
        contract, tmp_path / "quality/contracts/contract.yaml", tmp_path
    )
    assert any("budget_extension: must be" in error for error in errors)

    contract["budget_extension"] = {
        "justification": "One explicitly approved extra repair.",
        "approved_by": "repository-owner",
    }
    errors, _, _ = validate_contract(
        contract, tmp_path / "quality/contracts/contract.yaml", tmp_path
    )
    assert errors == []


def test_budget_never_exceeds_five(tmp_path: Path) -> None:
    contract = success_contract()
    contract["iteration_budget"] = 6
    contract["budget_extension"] = {
        "justification": "Too many repairs.",
        "approved_by": "repository-owner",
    }
    errors, _, _ = validate_contract(
        contract, tmp_path / "quality/contracts/contract.yaml", tmp_path
    )
    assert any("integer from 1 through 5" in error for error in errors)


def test_iterations_must_be_contiguous_and_match_recorded_attempts(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["iterations"][0]["number"] = 2
    run["failures"][0]["attempts"] = 0
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("contiguous from 1" in error for error in errors)
    assert any("recorded 0, derived 1" in error for error in errors)


def test_failure_keys_are_unique_and_primary_failure_must_exist(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    duplicate = deepcopy(run["failures"][0])
    duplicate.update({"id": "F-002", "attempts": 0, "status": "CONFIRMED"})
    duplicate.pop("resolution")
    duplicate.pop("resolved_iteration")
    run["failures"].append(duplicate)
    run["iterations"][0]["primary_failure_id"] = "F-404"
    run["failures"][0]["attempts"] = 0
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("duplicate failure_key" in error for error in errors)
    assert any("unknown failure 'F-404'" in error for error in errors)


def test_highest_impact_failure_must_be_selected(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["baseline"]["quality_vector"] = [1, 1, 0, 0]
    run["iterations"][0]["before"]["quality_vector"] = [1, 1, 0, 0]
    run["iterations"][0]["after"]["quality_vector"] = [1, 0, 0, 0]
    run["failures"].append(
        {
            "id": "F-000",
            "failure_key": "critical-regression",
            "criterion_ids": ["REG-001"],
            "severity": "P0",
            "status": "CONFIRMED",
            "attempts": 0,
            "discovered_iteration": 0,
            "summary": "A critical regression remains open.",
        }
    )
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("highest-impact open derived severity" in error for error in errors)


def test_quality_vectors_derive_assessment_and_best_retained_state(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["iterations"][0]["assessment"] = "NO_CHANGE"
    run["iterations"][0]["kept"] = False
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("assessment: must be IMPROVED" in error for error in errors)
    assert any("kept: must be true" in error for error in errors)


def test_failure_lifecycle_rejects_forged_vectors_and_requires_resolution_iteration(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["baseline"]["quality_vector"] = [0, 0, 0, 0]
    run["iterations"][0]["before"]["quality_vector"] = [0, 0, 0, 0]
    run["failures"][0].pop("resolved_iteration")
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("baseline.quality_vector" in error and "derived" in error for error in errors)
    assert any("before.quality_vector" in error and "derived" in error for error in errors)
    assert any("RESOLVED failure requires" in error for error in errors)


def test_new_failure_may_worsen_later_before_vector_when_lifecycle_proves_it(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["iterations"].append(
        iteration(2, [0, 1, 0, 0], [0, 0, 0, 0], "IMPROVED", failure_id="F-002")
    )
    run["failures"].append(
        {
            "id": "F-002",
            "failure_key": "later-finding",
            "criterion_ids": ["CAP-001"],
            "severity": "P1",
            "status": "RESOLVED",
            "attempts": 1,
            "discovered_iteration": 2,
            "resolved_iteration": 2,
            "summary": "Independent review discovered a later finding.",
            "resolution": "Iteration two resolved the later finding.",
        }
    )
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert errors == []


def test_kept_repair_cannot_retain_failed_regression(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["iterations"][0]["regression_checks"][0] = check("REG-001", "FAIL", exit_code=1)
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("kept repair requires every regression check to PASS" in error for error in errors)


def test_command_backed_and_regression_passes_require_command_and_zero_exit(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["final_checks"][0].update({"command": None, "exit_code": None})
    run["final_checks"][1].update({"command": "regression", "exit_code": None})
    run["final_checks"][2].update({"command": None, "exit_code": None})
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("command-backed PASS requires a non-empty" in error for error in errors)
    assert sum("command-backed PASS requires exit_code 0" in error for error in errors) >= 2
    assert not any("final_checks[2]: command-backed" in error for error in errors)


def test_independent_reviewer_cannot_be_a_builder(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["reviewers"][0]["reviewer_id"] = "root-builder"
    errors, criteria, reviewers = validate_pair(tmp_path, contract, run)
    assert any("authored the run or a repair" in error for error in errors)
    assert any(
        "not author-independent" in error
        for error in derive_pass_errors(run, contract, criteria, reviewers, "run-001", tmp_path)
    )


def test_two_consecutive_no_improvement_iterations_force_escalation(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run.update(
        {
            "status": "ACTIVE",
            "iterations": [
                iteration(1, [0, 1, 0, 0], [0, 1, 0, 0], "NO_CHANGE"),
                iteration(2, [0, 1, 0, 0], [0, 1, 0, 0], "NO_CHANGE"),
            ],
            "final_checks": [],
            "reviewers": [],
            "final_disposition": None,
            "completed_at": None,
        }
    )
    run["failures"][0].update({"status": "CONFIRMED", "attempts": 2})
    run["failures"][0].pop("resolution")
    run["failures"][0].pop("resolved_iteration")
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("2 consecutive iterations produced no improvement" in error for error in errors)


def test_unresolved_failure_after_three_repairs_forces_escalation(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run.update(
        {
            "status": "ACTIVE",
            "baseline": {
                "summary": "One P1 remains through three attempts.",
                "quality_vector": [0, 1, 0, 0],
                "checks": [check("CAP-001", "FAIL", exit_code=1)],
            },
            "iterations": [
                iteration(1, [0, 1, 0, 0], [0, 1, 0, 0], "NO_CHANGE"),
                iteration(2, [0, 1, 0, 0], [0, 1, 0, 0], "NO_CHANGE"),
                iteration(3, [0, 1, 0, 0], [0, 1, 0, 0], "NO_CHANGE"),
            ],
            "final_checks": [],
            "reviewers": [],
            "final_disposition": None,
            "completed_at": None,
        }
    )
    run["failures"][0].update({"status": "CONFIRMED", "attempts": 3})
    run["failures"][0].pop("resolution")
    run["failures"][0].pop("resolved_iteration")
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("survived 3 repairs" in error for error in errors)
    assert any("iteration budget is exhausted" in error for error in errors)


def test_awaiting_review_allows_exhausted_successful_repairs_but_not_more_work(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    contract["iteration_budget"] = 1
    run = completed_run(contract)
    run.update(
        {
            "contract_sha256": canonical_sha256(contract),
            "status": "AWAITING_REVIEW",
            "reviewers": [],
            "final_disposition": None,
            "completed_at": None,
        }
    )
    run.pop("continuity")
    run["final_checks"][2].update({"command": None, "exit_code": None, "result": "PARTIAL"})
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert errors == []

    run["status"] = "ACTIVE"
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("iteration budget is exhausted" in error for error in errors)

    run["status"] = "AWAITING_REVIEW"
    run["iterations"].append(iteration(2, [0, 0, 0, 0], [0, 0, 0, 0], "NO_CHANGE"))
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("exceeds budget 1" in error for error in errors)


def test_awaiting_review_rejects_unresolved_p1_and_unreached_budget(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run.update(
        {
            "status": "AWAITING_REVIEW",
            "final_disposition": None,
            "completed_at": None,
        }
    )
    run.pop("continuity")
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("repair budget to be reached exactly" in error for error in errors)

    contract["iteration_budget"] = 1
    run["contract_sha256"] = canonical_sha256(contract)
    run["failures"][0].update({"status": "CONFIRMED"})
    run["failures"][0].pop("resolution")
    run["failures"][0].pop("resolved_iteration")
    run["iterations"][0]["after"]["quality_vector"] = [0, 1, 0, 0]
    run["iterations"][0].update({"assessment": "NO_CHANGE", "kept": False})
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("permits only RESOLVED failures" in error for error in errors)


def test_typed_pass_does_not_override_failed_mandatory_check(tmp_path: Path) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run["final_checks"][0] = check("CAP-001", "FAIL", exit_code=1)
    errors, criteria, reviewers = validate_pair(tmp_path, contract, run)
    assert errors == []
    acceptance = derive_pass_errors(run, contract, criteria, reviewers, "run-001", tmp_path)
    assert any("criterion CAP-001 lacks a final PASS" in error for error in acceptance)


def test_required_rubric_scores_are_derived_against_dimension_and_total_minima(
    tmp_path: Path,
) -> None:
    rubric_path = tmp_path / "quality/rubrics/repository-operating-rules.yaml"
    rubric_path.parent.mkdir(parents=True)
    rubric = {
        "schema_version": 1,
        "rubric_id": "repository-operating-rules-v1",
        "minimum_total": 12,
        "dimensions": [
            {
                "id": dimension,
                "range": [0, 4],
                "minimum": 3,
                "description": f"Score {dimension}.",
            }
            for dimension in ("recovery", "authority", "instruction_economy", "boundedness")
        ],
    }
    rubric_path.write_text(yaml.safe_dump(rubric, sort_keys=False), encoding="utf-8")
    contract = success_contract()
    contract["required_reviewers"][0]["rubric_ref"] = (
        "quality/rubrics/repository-operating-rules.yaml"
    )
    run = completed_run(contract)
    run["contract_sha256"] = canonical_sha256(contract)
    run["rubric_results"] = [
        {
            "rubric_ref": "quality/rubrics/repository-operating-rules.yaml",
            "reviewer_id": "reviewer-one",
            "scores": {
                "recovery": 3,
                "authority": 3,
                "instruction_economy": 3,
                "boundedness": 3,
            },
            "total": 12,
        }
    ]
    errors, criteria, reviewers = validate_pair(tmp_path, contract, run)
    assert errors == []
    assert derive_pass_errors(run, contract, criteria, reviewers, "run-001", tmp_path) == []

    run["rubric_results"][0]["scores"]["boundedness"] = 2
    run["rubric_results"][0]["total"] = 11
    errors, criteria, reviewers = validate_pair(tmp_path, contract, run)
    assert errors == []
    acceptance = derive_pass_errors(run, contract, criteria, reviewers, "run-001", tmp_path)
    assert any("scores.boundedness: below minimum 3" in error for error in acceptance)
    assert any("total: below rubric minimum 12" in error for error in acceptance)


def test_architecture_and_security_risks_require_matching_review_roles(tmp_path: Path) -> None:
    contract = success_contract()
    contract["risk_tags"] = ["architecture", "security"]
    errors, _, _ = validate_contract(
        contract, tmp_path / "quality/contracts/contract.yaml", tmp_path
    )
    assert any("architecture reviewer role" in error for error in errors)
    assert any("security/permission reviewer role" in error for error in errors)


def test_sensitive_risk_tags_require_security_review_and_command_backed_authorization(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    contract["risk_tags"] = [
        "permissions",
        "authorization",
        "privacy",
        "sensitive-data",
        "data-access",
        "finance",
        "agent-autonomy",
        "providers",
        "external-actions",
        "side-effects",
        "l4",
        "l5",
    ]
    errors, _, _ = validate_contract(
        contract, tmp_path / "quality/contracts/contract.yaml", tmp_path
    )
    assert any("security-sensitive risk requires" in error for error in errors)
    assert any("mandatory command-backed authorization criterion" in error for error in errors)

    contract["required_reviewers"].append({"role": "security-permission", "independent": True})
    contract["criteria"].append(
        {
            "id": "AUTH-001",
            "class": "capability",
            "description": "Authorization gates are tested.",
            "mandatory": True,
            "severity_on_fail": "P1",
            "evaluator": "authorization",
            "command": "npm run test:authorization",
            "expected": "Authorization tests exit zero.",
        }
    )
    errors, _, _ = validate_contract(
        contract, tmp_path / "quality/contracts/contract.yaml", tmp_path
    )
    assert not any("security-sensitive risk requires" in error for error in errors)
    assert not any("mandatory command-backed authorization criterion" in error for error in errors)


def test_contract_references_must_be_safe_repo_relative_and_resolve(tmp_path: Path) -> None:
    contract = success_contract()
    contract["references"] = ["../escape.md", str(tmp_path / "absolute.md"), "missing.md"]
    errors, _, _ = validate_contract(
        contract, tmp_path / "quality/contracts/contract.yaml", tmp_path
    )
    assert sum("unsafe repository-relative reference" in error for error in errors) >= 2
    assert any("referenced path does not exist 'missing.md'" in error for error in errors)


def test_complete_run_requires_exact_reconciled_continuity_and_evidence_run_id(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run.pop("continuity")
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert any("COMPLETE run requires continuity reconciliation" in error for error in errors)

    run = completed_run(contract)
    run["continuity"]["checklist_ref"] = "docs/HANDOFF.md"
    errors, criteria, reviewers = validate_pair(tmp_path, contract, run)
    assert any("checklist_ref: must equal manifest-selected reference" in error for error in errors)
    (tmp_path / "docs/EVIDENCE.md").write_text("# No run reference\n", encoding="utf-8")
    run_errors = validate_run(
        run,
        tmp_path / "quality/runs/run.yaml",
        tmp_path,
        contract,
        tmp_path / "quality/contracts/contract.yaml",
        criteria,
        reviewers,
    )
    assert any("evidence does not contain run_id" in error for error in run_errors)


def test_finalized_historical_run_keeps_its_checklist_when_manifest_advances(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    errors, criteria, reviewers = validate_pair(tmp_path, contract, run)
    assert errors == []
    (tmp_path / "checklists/NEXT.md").write_text("# Next checklist\n", encoding="utf-8")
    (tmp_path / "PROJECT_MANIFEST.yaml").write_text(
        "checklists:\n"
        "  active: checklists/NEXT.md\n"
        "quality:\n"
        "  current_run: quality/runs/next.yaml\n",
        encoding="utf-8",
    )

    run_errors = validate_run(
        run,
        tmp_path / "quality/runs/run.yaml",
        tmp_path,
        contract,
        tmp_path / "quality/contracts/contract.yaml",
        criteria,
        reviewers,
    )

    assert not any("checklist_ref: must equal manifest-selected" in error for error in run_errors)


def test_active_legacy_run_remains_valid_until_final_lifecycle_reconciliation(
    tmp_path: Path,
) -> None:
    contract = success_contract()
    run = completed_run(contract)
    run.update({"status": "ACTIVE", "final_disposition": None, "completed_at": None})
    run.pop("continuity")
    run["failures"][0].pop("discovered_iteration")
    run["failures"][0].pop("resolved_iteration")
    errors, _, _ = validate_pair(tmp_path, contract, run)
    assert errors == []


def test_successor_run_cannot_reset_escalation_or_unresolved_failure_key() -> None:
    contract = success_contract()
    predecessor = completed_run(contract)
    predecessor.update(
        {
            "run_id": "run-001",
            "status": "COMPLETE",
            "final_disposition": "ESCALATE",
        }
    )
    predecessor["failures"][0].update({"status": "ESCALATED"})
    predecessor["failures"][0].pop("resolution")
    predecessor["failures"][0].pop("resolved_iteration")
    successor = completed_run(contract)
    successor.update({"run_id": "run-002", "started_at": "2026-08-10T21:00:00Z"})
    successor["failures"] = []
    runs = {"run-001": predecessor, "run-002": successor}
    errors = validate_cross_run_lineage({"contract-001": contract}, runs)
    assert any("successor lineage is required" in error for error in errors)

    successor["lineage"] = {
        "predecessor_run_id": "run-001",
        "predecessor_contract_id": "contract-001",
        "escalation_resolution_ref": "docs/EVIDENCE.md",
        "carried_failure_keys": [],
        "resolved_failure_keys": ["missing-capability"],
    }
    assert validate_cross_run_lineage({"contract-001": contract}, runs) == []


def write_agents_fixture(tmp_path: Path) -> None:
    (tmp_path / "quality").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "PROJECT_MANIFEST.yaml").write_text("project: test\n", encoding="utf-8")
    (tmp_path / "docs/INDEX.md").write_text("# Index\n", encoding="utf-8")
    policy = {
        "schema_version": 1,
        "target": "AGENTS.md",
        "limits": {"max_lines": 10, "max_words": 30, "max_bytes": 500},
        "required_headings": ["Source hierarchy"],
        "required_phrases": ["provider-neutral"],
        "required_references": ["PROJECT_MANIFEST.yaml", "docs/INDEX.md"],
    }
    (tmp_path / "quality/agents-policy.yaml").write_text(
        yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
    )
    (tmp_path / "AGENTS.md").write_text(
        "# Protocol\n\n## Source hierarchy\n\n"
        "Use `PROJECT_MANIFEST.yaml` and `docs/INDEX.md`; stay provider-neutral.\n",
        encoding="utf-8",
    )


def test_agents_policy_accepts_concise_document_with_resolving_refs(tmp_path: Path) -> None:
    write_agents_fixture(tmp_path)
    assert validate_agents(tmp_path) == []


def test_agents_policy_detects_limits_missing_content_and_broken_refs(tmp_path: Path) -> None:
    write_agents_fixture(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        "# Protocol\n\n" + "filler words here\n" * 12 + "`docs/MISSING.md`\n",
        encoding="utf-8",
    )
    errors = validate_agents(tmp_path)
    assert any("max_lines limit exceeded" in error for error in errors)
    assert any("missing required heading" in error for error in errors)
    assert any("missing required phrase" in error for error in errors)
    assert any("referenced path does not exist 'docs/MISSING.md'" in error for error in errors)


def test_agents_policy_rejects_unknown_limit_keys(tmp_path: Path) -> None:
    write_agents_fixture(tmp_path)
    policy_path = tmp_path / "quality/agents-policy.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    policy["limits"]["max_vibes"] = 1
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    assert any("unknown limit 'max_vibes'" in error for error in validate_agents(tmp_path))

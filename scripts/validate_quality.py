from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1
SEVERITIES = ("P0", "P1", "P2", "P3")
RESULTS = ("PASS", "FAIL", "PARTIAL", "SKIP")
EVALUATORS = (
    "deterministic",
    "static_analysis",
    "security_scan",
    "integration",
    "artifact_inspection",
    "independent_review",
    "model_review",
    "human_review",
    "browser",
    "authorization",
)
COMMAND_BACKED_EVALUATORS = {
    "deterministic",
    "static_analysis",
    "security_scan",
    "integration",
    "authorization",
}
SECURITY_RISK_TAGS = {
    "security",
    "permission",
    "permissions",
    "authorization",
    "privacy",
    "sensitive-data",
    "data-access",
    "finance",
    "agent-autonomy",
    "provider",
    "providers",
    "external-action",
    "external-actions",
    "side-effect",
    "side-effects",
}
AUTHORIZATION_RISK_TAGS = {"finance", "permission", "permissions", "l4", "l5"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CODE_SPAN_PATTERN = re.compile(r"`([^`\n]+)`")
URI_OR_DRIVE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

CONTRACT_ROOT_KEYS = {
    "schema_version",
    "contract_id",
    "goal",
    "milestone",
    "created_at",
    "owner_role",
    "scope",
    "iteration_budget",
    "budget_extension",
    "risk_tags",
    "lineage",
    "references",
    "criteria",
    "required_reviewers",
    "stop_conditions",
}
RUN_ROOT_KEYS = {
    "schema_version",
    "run_id",
    "contract_id",
    "contract_path",
    "contract_sha256",
    "goal",
    "milestone",
    "repository_revision",
    "workspace_state",
    "started_at",
    "status",
    "builder_ids",
    "references",
    "baseline",
    "iterations",
    "final_checks",
    "reviewers",
    "rubric_results",
    "continuity",
    "lineage",
    "failures",
    "remaining_risks",
    "final_disposition",
    "completed_at",
}


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Return the stable SHA-256 used to bind a run to its parsed contract."""
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_mapping(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"{label}: unreadable YAML: {exc}")
        return None
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) for key in payload
    ):
        errors.append(f"{label}: root must be a string-keyed mapping")
        return None
    return payload


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        errors.append(f"{label}: must be a string-keyed mapping")
        return None
    return value


def _list(value: Any, label: str, errors: list[str]) -> list[Any] | None:
    if not isinstance(value, list):
        errors.append(f"{label}: must be a list")
        return None
    return value


def _check_keys(
    payload: dict[str, Any],
    *,
    required: set[str],
    allowed: set[str],
    label: str,
    errors: list[str],
) -> None:
    for key in sorted(required - payload.keys()):
        errors.append(f"{label}: missing required field '{key}'")
    for key in sorted(payload.keys() - allowed):
        errors.append(f"{label}: unknown field '{key}'")


def _nonempty_string(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: must be a non-empty string")
        return None
    return value


def _identifier(value: Any, label: str, errors: list[str]) -> str | None:
    text = _nonempty_string(value, label, errors)
    if text is not None and ID_PATTERN.fullmatch(text) is None:
        errors.append(f"{label}: must match {ID_PATTERN.pattern}")
        return None
    return text


def _timestamp(
    value: Any, label: str, errors: list[str], *, nullable: bool = False
) -> None:
    if value is None and nullable:
        return
    text = _nonempty_string(value, label, errors)
    if text is None:
        return
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label}: must be an ISO-8601 timestamp")


def _string_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    nonempty: bool = False,
    identifiers: bool = False,
) -> list[str]:
    items = _list(value, label, errors)
    if items is None:
        return []
    if nonempty and not items:
        errors.append(f"{label}: must not be empty")
    output: list[str] = []
    for index, item in enumerate(items):
        result = (
            _identifier(item, f"{label}[{index}]", errors)
            if identifiers
            else _nonempty_string(item, f"{label}[{index}]", errors)
        )
        if result is not None:
            output.append(result)
    if len(output) != len(set(output)):
        errors.append(f"{label}: values must be unique")
    return output


def _safe_repo_reference(
    root: Path, reference: Any, label: str, errors: list[str]
) -> None:
    text = _nonempty_string(reference, label, errors)
    if text is None:
        return
    raw = text.strip().strip("<>").split("#", 1)[0]
    normalized = raw.replace("\\", "/")
    if (
        not normalized
        or normalized.startswith(("/", "//"))
        or URI_OR_DRIVE_PATTERN.match(normalized)
        or ".." in Path(normalized).parts
    ):
        errors.append(f"{label}: unsafe repository-relative reference '{text}'")
        return
    resolved = (root / normalized).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: reference escapes repository root '{text}'")
        return
    if not resolved.exists():
        errors.append(f"{label}: referenced path does not exist '{text}'")


def _reference_list(value: Any, root: Path, label: str, errors: list[str]) -> None:
    references = _list(value, label, errors)
    if references is None:
        return
    seen: set[str] = set()
    for index, reference in enumerate(references):
        if isinstance(reference, str) and reference in seen:
            errors.append(f"{label}: references must be unique")
        if isinstance(reference, str):
            seen.add(reference)
        _safe_repo_reference(root, reference, f"{label}[{index}]", errors)


def _risk_tags(value: Any, label: str, errors: list[str]) -> set[str]:
    return {
        tag.lower().replace("_", "-")
        for tag in _string_list(value, label, errors, identifiers=True)
    }


def _quality_vector(
    value: Any, label: str, errors: list[str]
) -> tuple[int, int, int, int] | None:
    items = _list(value, label, errors)
    if items is None:
        return None
    if len(items) != len(SEVERITIES):
        errors.append(f"{label}: must contain four counts ordered P0, P1, P2, P3")
        return None
    if any(type(item) is not int or item < 0 for item in items):
        errors.append(f"{label}: counts must be non-negative integers")
        return None
    return (items[0], items[1], items[2], items[3])


def _validate_risk_routing(
    risk_tags: set[str], reviewer_roles: set[str], label: str, errors: list[str]
) -> None:
    role_text = " ".join(reviewer_roles).lower()
    if "architecture" in risk_tags and "architecture" not in role_text:
        errors.append(
            f"{label}: architecture risk requires an architecture reviewer role"
        )
    if risk_tags.intersection(SECURITY_RISK_TAGS) and not any(
        token in role_text for token in ("security", "permission")
    ):
        errors.append(
            f"{label}: security-sensitive risk requires a security/permission reviewer role"
        )


def _validate_authorization_routing(
    risk_tags: set[str],
    criteria_by_id: dict[str, dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    if not risk_tags.intersection(AUTHORIZATION_RISK_TAGS):
        return
    authorization_criteria = [
        criterion
        for criterion in criteria_by_id.values()
        if criterion.get("mandatory") is True
        and criterion.get("evaluator") == "authorization"
        and isinstance(criterion.get("command"), str)
        and bool(str(criterion.get("command")).strip())
    ]
    if not authorization_criteria:
        errors.append(
            f"{label}: finance/permission/L4/L5 risk requires a mandatory "
            "command-backed authorization criterion"
        )


def validate_contract(
    payload: dict[str, Any], path: Path, root: Path
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    label = (
        path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    )
    errors: list[str] = []
    required = {
        "schema_version",
        "contract_id",
        "goal",
        "milestone",
        "owner_role",
        "scope",
        "iteration_budget",
        "criteria",
        "required_reviewers",
        "stop_conditions",
    }
    _check_keys(
        payload,
        required=required,
        allowed=CONTRACT_ROOT_KEYS,
        label=label,
        errors=errors,
    )
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{label}.schema_version: must equal {SCHEMA_VERSION}")
    _identifier(payload.get("contract_id"), f"{label}.contract_id", errors)
    _nonempty_string(payload.get("goal"), f"{label}.goal", errors)
    _nonempty_string(payload.get("milestone"), f"{label}.milestone", errors)
    _identifier(payload.get("owner_role"), f"{label}.owner_role", errors)
    if "created_at" in payload:
        _timestamp(payload.get("created_at"), f"{label}.created_at", errors)

    scope = _mapping(payload.get("scope"), f"{label}.scope", errors)
    if scope is not None:
        _check_keys(
            scope,
            required={"in", "out"},
            allowed={"in", "out"},
            label=f"{label}.scope",
            errors=errors,
        )
        _string_list(scope.get("in"), f"{label}.scope.in", errors, nonempty=True)
        _string_list(scope.get("out"), f"{label}.scope.out", errors, nonempty=True)

    budget = payload.get("iteration_budget")
    if type(budget) is not int or not 1 <= budget <= 5:
        errors.append(f"{label}.iteration_budget: must be an integer from 1 through 5")
    if type(budget) is int and budget > 3:
        extension = _mapping(
            payload.get("budget_extension"), f"{label}.budget_extension", errors
        )
        if extension is not None:
            _check_keys(
                extension,
                required={"justification", "approved_by"},
                allowed={"justification", "approved_by"},
                label=f"{label}.budget_extension",
                errors=errors,
            )
            _nonempty_string(
                extension.get("justification"),
                f"{label}.budget_extension.justification",
                errors,
            )
            _nonempty_string(
                extension.get("approved_by"),
                f"{label}.budget_extension.approved_by",
                errors,
            )
    elif "budget_extension" in payload:
        errors.append(
            f"{label}.budget_extension: only permitted when iteration_budget exceeds 3"
        )

    if "references" in payload:
        _reference_list(payload.get("references"), root, f"{label}.references", errors)
    if "lineage" in payload:
        lineage = _mapping(payload.get("lineage"), f"{label}.lineage", errors)
        if lineage is not None:
            _check_keys(
                lineage,
                required={
                    "supersedes_contract_id",
                    "predecessor_run_id",
                    "escalation_resolution_ref",
                },
                allowed={
                    "supersedes_contract_id",
                    "predecessor_run_id",
                    "escalation_resolution_ref",
                },
                label=f"{label}.lineage",
                errors=errors,
            )
            _identifier(
                lineage.get("supersedes_contract_id"),
                f"{label}.lineage.supersedes_contract_id",
                errors,
            )
            _identifier(
                lineage.get("predecessor_run_id"),
                f"{label}.lineage.predecessor_run_id",
                errors,
            )
            _safe_repo_reference(
                root,
                lineage.get("escalation_resolution_ref"),
                f"{label}.lineage.escalation_resolution_ref",
                errors,
            )

    criteria_by_id: dict[str, dict[str, Any]] = {}
    criterion_classes: set[str] = set()
    contract_risk_tags = (
        _risk_tags(payload.get("risk_tags"), f"{label}.risk_tags", errors)
        if "risk_tags" in payload
        else set()
    )
    criteria = _list(payload.get("criteria"), f"{label}.criteria", errors)
    if criteria is not None:
        if not criteria:
            errors.append(f"{label}.criteria: must not be empty")
        for index, raw_criterion in enumerate(criteria):
            criterion_label = f"{label}.criteria[{index}]"
            criterion = _mapping(raw_criterion, criterion_label, errors)
            if criterion is None:
                continue
            _check_keys(
                criterion,
                required={
                    "id",
                    "class",
                    "description",
                    "mandatory",
                    "severity_on_fail",
                    "evaluator",
                    "expected",
                },
                allowed={
                    "id",
                    "class",
                    "description",
                    "mandatory",
                    "severity_on_fail",
                    "evaluator",
                    "command",
                    "expected",
                    "risk_tags",
                    "rubric_ref",
                },
                label=criterion_label,
                errors=errors,
            )
            criterion_id = _identifier(
                criterion.get("id"), f"{criterion_label}.id", errors
            )
            if criterion_id is not None:
                if criterion_id in criteria_by_id:
                    errors.append(
                        f"{label}.criteria: duplicate criterion id '{criterion_id}'"
                    )
                criteria_by_id[criterion_id] = criterion
            criterion_class = criterion.get("class")
            if criterion_class not in {"capability", "regression", "review"}:
                errors.append(
                    f"{criterion_label}.class: must be capability, regression, or review"
                )
            else:
                criterion_classes.add(criterion_class)
            _nonempty_string(
                criterion.get("description"), f"{criterion_label}.description", errors
            )
            if type(criterion.get("mandatory")) is not bool:
                errors.append(f"{criterion_label}.mandatory: must be a boolean")
            if criterion.get("severity_on_fail") not in SEVERITIES:
                errors.append(
                    f"{criterion_label}.severity_on_fail: must be P0, P1, P2, or P3"
                )
            evaluator = criterion.get("evaluator")
            if evaluator not in EVALUATORS:
                errors.append(
                    f"{criterion_label}.evaluator: unsupported evaluator '{evaluator}'"
                )
            command = criterion.get("command")
            if command is not None and (
                not isinstance(command, str) or not command.strip()
            ):
                errors.append(
                    f"{criterion_label}.command: must be null or a non-empty string"
                )
            _nonempty_string(
                criterion.get("expected"), f"{criterion_label}.expected", errors
            )
            if "risk_tags" in criterion:
                contract_risk_tags.update(
                    _risk_tags(
                        criterion.get("risk_tags"),
                        f"{criterion_label}.risk_tags",
                        errors,
                    )
                )
            if "rubric_ref" in criterion:
                _safe_repo_reference(
                    root,
                    criterion.get("rubric_ref"),
                    f"{criterion_label}.rubric_ref",
                    errors,
                )
    missing_classes = {"capability", "regression", "review"} - criterion_classes
    if missing_classes:
        errors.append(
            f"{label}.criteria: missing required classes {', '.join(sorted(missing_classes))}"
        )

    required_reviewers: dict[str, dict[str, Any]] = {}
    reviewers = _list(
        payload.get("required_reviewers"), f"{label}.required_reviewers", errors
    )
    if reviewers is not None:
        if not reviewers:
            errors.append(f"{label}.required_reviewers: must not be empty")
        for index, raw_reviewer in enumerate(reviewers):
            reviewer_label = f"{label}.required_reviewers[{index}]"
            reviewer = _mapping(raw_reviewer, reviewer_label, errors)
            if reviewer is None:
                continue
            _check_keys(
                reviewer,
                required={"role", "independent"},
                allowed={"role", "independent", "rubric_ref", "minimum_score"},
                label=reviewer_label,
                errors=errors,
            )
            role = _identifier(reviewer.get("role"), f"{reviewer_label}.role", errors)
            if role is not None:
                if role in required_reviewers:
                    errors.append(
                        f"{label}.required_reviewers: duplicate role '{role}'"
                    )
                required_reviewers[role] = reviewer
            if reviewer.get("independent") is not True:
                errors.append(
                    f"{reviewer_label}.independent: required reviewers must be independent"
                )
            if "rubric_ref" in reviewer:
                _safe_repo_reference(
                    root,
                    reviewer.get("rubric_ref"),
                    f"{reviewer_label}.rubric_ref",
                    errors,
                )
            if "minimum_score" in reviewer and type(
                reviewer.get("minimum_score")
            ) not in (
                int,
                float,
            ):
                errors.append(f"{reviewer_label}.minimum_score: must be numeric")

    _validate_risk_routing(contract_risk_tags, set(required_reviewers), label, errors)
    _validate_authorization_routing(contract_risk_tags, criteria_by_id, label, errors)
    if "ui" in contract_risk_tags and not any(
        criterion.get("evaluator") == "browser" for criterion in criteria_by_id.values()
    ):
        errors.append(f"{label}: UI risk requires a browser-evaluated criterion")
    stop_conditions = _mapping(
        payload.get("stop_conditions"), f"{label}.stop_conditions", errors
    )
    if stop_conditions is not None:
        _check_keys(
            stop_conditions,
            required={"success", "escalate"},
            allowed={"success", "escalate"},
            label=f"{label}.stop_conditions",
            errors=errors,
        )
        success = _string_list(
            stop_conditions.get("success"),
            f"{label}.stop_conditions.success",
            errors,
            nonempty=True,
        )
        escalate = _string_list(
            stop_conditions.get("escalate"),
            f"{label}.stop_conditions.escalate",
            errors,
            nonempty=True,
        )
        success_text = " ".join(success).lower()
        for marker, description in (
            ("mandatory", "mandatory criteria"),
            ("regression", "regressions"),
            ("reviewer", "required reviewers"),
        ):
            if marker not in success_text:
                errors.append(
                    f"{label}.stop_conditions.success: must address {description}"
                )
        escalate_text = " ".join(escalate).lower()
        escalation_markers = (
            (("3", "repair"), "three failed repairs"),
            (("2", "improvement"), "two no-improvement iterations"),
            (("budget",), "budget exhaustion"),
            (("conflict",), "requirement conflict"),
            (("external",), "external dependency or decision"),
            (("violate",), "constraint-violating repairs"),
        )
        for markers, description in escalation_markers:
            if not all(marker in escalate_text for marker in markers):
                errors.append(
                    f"{label}.stop_conditions.escalate: must address {description}"
                )

    return errors, criteria_by_id, required_reviewers


def _validate_check(
    raw_check: Any,
    *,
    label: str,
    criteria_by_id: dict[str, dict[str, Any]],
    root: Path,
    errors: list[str],
) -> dict[str, Any] | None:
    check = _mapping(raw_check, label, errors)
    if check is None:
        return None
    _check_keys(
        check,
        required={"criterion_id", "result", "evidence"},
        allowed={
            "criterion_id",
            "command",
            "exit_code",
            "result",
            "evidence",
            "evidence_refs",
        },
        label=label,
        errors=errors,
    )
    criterion_id = _identifier(
        check.get("criterion_id"), f"{label}.criterion_id", errors
    )
    criterion = criteria_by_id.get(criterion_id or "")
    if criterion_id is not None and criterion_id not in criteria_by_id:
        errors.append(f"{label}.criterion_id: unknown criterion '{criterion_id}'")
    command = check.get("command")
    if command is not None and (not isinstance(command, str) or not command.strip()):
        errors.append(f"{label}.command: must be null or a non-empty string")
    exit_code = check.get("exit_code")
    if exit_code is not None and type(exit_code) is not int:
        errors.append(f"{label}.exit_code: must be an integer or null")
    result = check.get("result")
    if result not in RESULTS:
        errors.append(f"{label}.result: must be PASS, FAIL, PARTIAL, or SKIP")
    if result == "PASS" and type(exit_code) is int and exit_code != 0:
        errors.append(f"{label}: PASS cannot record non-zero exit_code {exit_code}")
    command_backed_pass = (
        result == "PASS"
        and criterion is not None
        and (
            criterion.get("class") == "regression"
            or criterion.get("evaluator") in COMMAND_BACKED_EVALUATORS
        )
    )
    if command_backed_pass:
        if not isinstance(command, str) or not command.strip():
            errors.append(
                f"{label}: command-backed PASS requires a non-empty recorded command"
            )
        if type(exit_code) is not int or exit_code != 0:
            errors.append(f"{label}: command-backed PASS requires exit_code 0")
    _nonempty_string(check.get("evidence"), f"{label}.evidence", errors)
    if "evidence_refs" in check:
        _reference_list(
            check.get("evidence_refs"), root, f"{label}.evidence_refs", errors
        )
    return check


def _validate_checks(
    value: Any,
    *,
    label: str,
    criteria_by_id: dict[str, dict[str, Any]],
    root: Path,
    errors: list[str],
    nonempty: bool = False,
    regression_only: bool = False,
) -> list[dict[str, Any]]:
    raw_checks = _list(value, label, errors)
    if raw_checks is None:
        return []
    if nonempty and not raw_checks:
        errors.append(f"{label}: must not be empty")
    checks: list[dict[str, Any]] = []
    for index, raw_check in enumerate(raw_checks):
        check = _validate_check(
            raw_check,
            label=f"{label}[{index}]",
            criteria_by_id=criteria_by_id,
            root=root,
            errors=errors,
        )
        if check is not None:
            checks.append(check)
            criterion = criteria_by_id.get(str(check.get("criterion_id")))
            if (
                regression_only
                and criterion is not None
                and criterion.get("class") != "regression"
            ):
                errors.append(
                    f"{label}[{index}]: regression check must reference a regression criterion"
                )
    return checks


def _validate_rubric_results(
    value: Any,
    *,
    root: Path,
    label: str,
    reviewer_ids: set[str],
    errors: list[str],
    require_thresholds: bool,
) -> list[tuple[str, str]]:
    if value is None:
        return []
    raw_results = _list(value, label, errors)
    if raw_results is None:
        return []
    evaluated: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, raw_result in enumerate(raw_results):
        result_label = f"{label}[{index}]"
        result = _mapping(raw_result, result_label, errors)
        if result is None:
            continue
        _check_keys(
            result,
            required={"rubric_ref", "reviewer_id", "scores", "total"},
            allowed={"rubric_ref", "reviewer_id", "scores", "total"},
            label=result_label,
            errors=errors,
        )
        reference = _nonempty_string(
            result.get("rubric_ref"), f"{result_label}.rubric_ref", errors
        )
        reviewer_id = _identifier(
            result.get("reviewer_id"), f"{result_label}.reviewer_id", errors
        )
        if reviewer_id is not None and reviewer_id not in reviewer_ids:
            errors.append(
                f"{result_label}.reviewer_id: unknown run reviewer '{reviewer_id}'"
            )
        if reference is None or reviewer_id is None:
            continue
        _safe_repo_reference(root, reference, f"{result_label}.rubric_ref", errors)
        normalized = reference.strip().strip("<>").split("#", 1)[0].replace("\\", "/")
        result_key = (reviewer_id, normalized)
        if result_key in seen:
            errors.append(
                f"{label}: duplicate result for reviewer '{reviewer_id}' and rubric '{normalized}'"
            )
        seen.add(result_key)
        rubric_path = (root / normalized).resolve()
        if not rubric_path.exists() or not rubric_path.is_file():
            continue
        rubric = _load_mapping(rubric_path, normalized, errors)
        if rubric is None:
            continue
        _check_keys(
            rubric,
            required={"schema_version", "rubric_id", "minimum_total", "dimensions"},
            allowed={"schema_version", "rubric_id", "minimum_total", "dimensions"},
            label=normalized,
            errors=errors,
        )
        if rubric.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{normalized}.schema_version: must equal {SCHEMA_VERSION}")
        _identifier(rubric.get("rubric_id"), f"{normalized}.rubric_id", errors)
        minimum_total = rubric.get("minimum_total")
        if not isinstance(minimum_total, (int, float)) or isinstance(
            minimum_total, bool
        ):
            errors.append(f"{normalized}.minimum_total: must be numeric")
            minimum_total = None
        raw_dimensions = _list(
            rubric.get("dimensions"), f"{normalized}.dimensions", errors
        )
        dimensions: dict[str, tuple[float, float, float]] = {}
        if raw_dimensions is not None:
            if not raw_dimensions:
                errors.append(f"{normalized}.dimensions: must not be empty")
            for dimension_index, raw_dimension in enumerate(raw_dimensions):
                dimension_label = f"{normalized}.dimensions[{dimension_index}]"
                dimension = _mapping(raw_dimension, dimension_label, errors)
                if dimension is None:
                    continue
                _check_keys(
                    dimension,
                    required={"id", "range", "minimum", "description"},
                    allowed={"id", "range", "minimum", "description"},
                    label=dimension_label,
                    errors=errors,
                )
                dimension_id = _identifier(
                    dimension.get("id"), f"{dimension_label}.id", errors
                )
                score_range = dimension.get("range")
                minimum = dimension.get("minimum")
                valid_range = (
                    isinstance(score_range, list)
                    and len(score_range) == 2
                    and all(
                        isinstance(bound, (int, float)) and not isinstance(bound, bool)
                        for bound in score_range
                    )
                    and float(score_range[0]) <= float(score_range[1])
                )
                if not valid_range:
                    errors.append(
                        f"{dimension_label}.range: must be an ordered numeric [minimum, maximum]"
                    )
                if not isinstance(minimum, (int, float)) or isinstance(minimum, bool):
                    errors.append(f"{dimension_label}.minimum: must be numeric")
                _nonempty_string(
                    dimension.get("description"),
                    f"{dimension_label}.description",
                    errors,
                )
                if (
                    dimension_id is not None
                    and valid_range
                    and isinstance(score_range, list)
                    and isinstance(minimum, (int, float))
                    and not isinstance(minimum, bool)
                ):
                    lower = float(score_range[0])
                    upper = float(score_range[1])
                    threshold = float(minimum)
                    if not lower <= threshold <= upper:
                        errors.append(
                            f"{dimension_label}.minimum: must fall within the declared range"
                        )
                    if dimension_id in dimensions:
                        errors.append(
                            f"{normalized}.dimensions: duplicate id '{dimension_id}'"
                        )
                    dimensions[dimension_id] = (lower, upper, threshold)

        scores = _mapping(result.get("scores"), f"{result_label}.scores", errors)
        valid_scores: dict[str, float] = {}
        if scores is not None:
            unknown_scores = set(scores) - set(dimensions)
            missing_scores = set(dimensions) - set(scores)
            for dimension_id in sorted(unknown_scores):
                errors.append(
                    f"{result_label}.scores: unknown dimension '{dimension_id}'"
                )
            for dimension_id in sorted(missing_scores):
                errors.append(
                    f"{result_label}.scores: missing dimension '{dimension_id}'"
                )
            for dimension_id, score in scores.items():
                if not isinstance(score, (int, float)) or isinstance(score, bool):
                    errors.append(
                        f"{result_label}.scores.{dimension_id}: must be numeric"
                    )
                    continue
                numeric_score = float(score)
                valid_scores[dimension_id] = numeric_score
                limits = dimensions.get(dimension_id)
                if limits is not None and not limits[0] <= numeric_score <= limits[1]:
                    errors.append(
                        f"{result_label}.scores.{dimension_id}: outside rubric range"
                    )
                if (
                    require_thresholds
                    and limits is not None
                    and numeric_score < limits[2]
                ):
                    errors.append(
                        f"{result_label}.scores.{dimension_id}: below minimum {limits[2]:g}"
                    )
        total = result.get("total")
        if not isinstance(total, (int, float)) or isinstance(total, bool):
            errors.append(f"{result_label}.total: must be numeric")
        elif set(valid_scores) == set(dimensions):
            derived_total = sum(valid_scores.values())
            if abs(float(total) - derived_total) > 1e-9:
                errors.append(
                    f"{result_label}.total: recorded {float(total):g}, derived {derived_total:g}"
                )
            if (
                require_thresholds
                and isinstance(minimum_total, (int, float))
                and float(total) < float(minimum_total)
            ):
                errors.append(
                    f"{result_label}.total: below rubric minimum {float(minimum_total):g}"
                )
        evaluated.append(result_key)
    return evaluated


def _open_failure_ids(
    failures_by_id: dict[str, dict[str, Any]],
    iteration: int,
    *,
    after: bool,
) -> set[str]:
    open_ids: set[str] = set()
    for failure_id, failure in failures_by_id.items():
        discovered = failure.get("discovered_iteration")
        resolved = failure.get("resolved_iteration")
        if type(discovered) is not int:
            continue
        if iteration == 0:
            is_open = discovered == 0 and (type(resolved) is not int or resolved > 0)
        elif after:
            is_open = discovered <= iteration and (
                type(resolved) is not int or resolved > iteration
            )
        else:
            is_open = discovered <= iteration and (
                type(resolved) is not int or resolved >= iteration
            )
        if is_open:
            open_ids.add(failure_id)
    return open_ids


def _derived_quality_vector(
    failures_by_id: dict[str, dict[str, Any]],
    iteration: int,
    *,
    after: bool,
) -> tuple[int, int, int, int]:
    counts = [0, 0, 0, 0]
    for failure_id in _open_failure_ids(failures_by_id, iteration, after=after):
        severity = failures_by_id[failure_id].get("severity")
        if severity in SEVERITIES:
            counts[SEVERITIES.index(str(severity))] += 1
    return (counts[0], counts[1], counts[2], counts[3])


def _validate_continuity(
    value: Any,
    *,
    root: Path,
    label: str,
    run_id: str | None,
    required: bool,
    errors: list[str],
) -> None:
    if value is None:
        if required:
            errors.append(f"{label}: COMPLETE run requires continuity reconciliation")
        return
    continuity = _mapping(value, label, errors)
    if continuity is None:
        return
    expected_keys = {
        "evidence_ref",
        "evidence_status",
        "build_status_ref",
        "build_status_status",
        "handoff_ref",
        "handoff_status",
        "checklist_ref",
        "checklist_status",
    }
    _check_keys(
        continuity,
        required=expected_keys,
        allowed=expected_keys,
        label=label,
        errors=errors,
    )
    manifest = _load_mapping(
        root / "PROJECT_MANIFEST.yaml", "PROJECT_MANIFEST.yaml", errors
    )
    active_checklist: Any = None
    if manifest is not None:
        checklists = manifest.get("checklists")
        if isinstance(checklists, dict):
            active_checklist = checklists.get("active")
    expected_refs = {
        "evidence_ref": "docs/EVIDENCE.md",
        "build_status_ref": "docs/BUILD_STATUS.md",
        "handoff_ref": "docs/HANDOFF.md",
        "checklist_ref": active_checklist,
    }
    for ref_key, expected_ref in expected_refs.items():
        reference = continuity.get(ref_key)
        _safe_repo_reference(root, reference, f"{label}.{ref_key}", errors)
        if isinstance(reference, str):
            normalized = reference.replace("\\", "/")
            if not isinstance(expected_ref, str) or normalized != expected_ref:
                errors.append(
                    f"{label}.{ref_key}: must equal manifest-selected reference "
                    f"'{expected_ref}'"
                )
    for status_key in (
        "evidence_status",
        "build_status_status",
        "handoff_status",
        "checklist_status",
    ):
        if continuity.get(status_key) not in {"RECONCILED", "UNCHANGED_REVIEWED"}:
            errors.append(
                f"{label}.{status_key}: must be RECONCILED or UNCHANGED_REVIEWED"
            )
    evidence_ref = continuity.get("evidence_ref")
    if isinstance(evidence_ref, str) and run_id is not None:
        evidence_path = (root / evidence_ref.replace("\\", "/")).resolve()
        if evidence_path.is_file():
            try:
                evidence_text = evidence_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{label}.evidence_ref: unreadable evidence: {exc}")
            else:
                if run_id not in evidence_text:
                    errors.append(
                        f"{label}.evidence_ref: evidence does not contain run_id '{run_id}'"
                    )


def _validate_run_lineage_shape(
    value: Any, *, root: Path, label: str, errors: list[str]
) -> None:
    if value is None:
        return
    lineage = _mapping(value, label, errors)
    if lineage is None:
        return
    keys = {
        "predecessor_run_id",
        "predecessor_contract_id",
        "escalation_resolution_ref",
        "carried_failure_keys",
        "resolved_failure_keys",
    }
    _check_keys(lineage, required=keys, allowed=keys, label=label, errors=errors)
    _identifier(
        lineage.get("predecessor_run_id"), f"{label}.predecessor_run_id", errors
    )
    _identifier(
        lineage.get("predecessor_contract_id"),
        f"{label}.predecessor_contract_id",
        errors,
    )
    _safe_repo_reference(
        root,
        lineage.get("escalation_resolution_ref"),
        f"{label}.escalation_resolution_ref",
        errors,
    )
    carried = set(
        _string_list(
            lineage.get("carried_failure_keys"),
            f"{label}.carried_failure_keys",
            errors,
            identifiers=True,
        )
    )
    resolved = set(
        _string_list(
            lineage.get("resolved_failure_keys"),
            f"{label}.resolved_failure_keys",
            errors,
            identifiers=True,
        )
    )
    overlap = carried.intersection(resolved)
    if overlap:
        errors.append(
            f"{label}: failure keys cannot be both carried and resolved: "
            f"{', '.join(sorted(overlap))}"
        )


def validate_run(
    payload: dict[str, Any],
    path: Path,
    root: Path,
    contract: dict[str, Any],
    contract_path: Path,
    criteria_by_id: dict[str, dict[str, Any]],
    required_reviewers: dict[str, dict[str, Any]],
) -> list[str]:
    label = (
        path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    )
    errors: list[str] = []
    required = {
        "schema_version",
        "run_id",
        "contract_id",
        "contract_path",
        "contract_sha256",
        "goal",
        "milestone",
        "started_at",
        "status",
        "builder_ids",
        "baseline",
        "iterations",
        "final_checks",
        "reviewers",
        "failures",
        "remaining_risks",
        "final_disposition",
        "completed_at",
    }
    _check_keys(
        payload, required=required, allowed=RUN_ROOT_KEYS, label=label, errors=errors
    )
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{label}.schema_version: must equal {SCHEMA_VERSION}")
    run_id = _identifier(payload.get("run_id"), f"{label}.run_id", errors)
    run_contract_id = _identifier(
        payload.get("contract_id"), f"{label}.contract_id", errors
    )
    if run_contract_id != contract.get("contract_id"):
        errors.append(f"{label}.contract_id: does not match loaded contract")
    run_contract_path = _nonempty_string(
        payload.get("contract_path"), f"{label}.contract_path", errors
    )
    if run_contract_path is not None:
        _safe_repo_reference(root, run_contract_path, f"{label}.contract_path", errors)
        normalized_contract_path = run_contract_path.replace("\\", "/")
        resolved_contract_path = (root / normalized_contract_path).resolve()
        if resolved_contract_path != contract_path.resolve():
            errors.append(
                f"{label}.contract_path: does not resolve to loaded contract "
                f"'{contract_path.relative_to(root).as_posix()}'"
            )
    expected_hash = canonical_sha256(contract)
    if payload.get("contract_sha256") != expected_hash:
        errors.append(f"{label}.contract_sha256: mismatch; expected {expected_hash}")
    goal = _nonempty_string(payload.get("goal"), f"{label}.goal", errors)
    if goal is not None and goal != contract.get("goal"):
        errors.append(f"{label}.goal: does not match loaded contract")
    milestone = _nonempty_string(payload.get("milestone"), f"{label}.milestone", errors)
    if milestone is not None and milestone != contract.get("milestone"):
        errors.append(f"{label}.milestone: does not match loaded contract")
    if (
        "repository_revision" in payload
        and payload.get("repository_revision") is not None
    ):
        _nonempty_string(
            payload.get("repository_revision"), f"{label}.repository_revision", errors
        )
    if "workspace_state" in payload and payload.get("workspace_state") not in {
        "committed",
        "uncommitted",
    }:
        errors.append(f"{label}.workspace_state: must be committed or uncommitted")
    _timestamp(payload.get("started_at"), f"{label}.started_at", errors)
    status = payload.get("status")
    if status not in {"ACTIVE", "AWAITING_REVIEW", "COMPLETE"}:
        errors.append(f"{label}.status: must be ACTIVE, AWAITING_REVIEW, or COMPLETE")
    if "references" in payload:
        _reference_list(payload.get("references"), root, f"{label}.references", errors)
    _validate_run_lineage_shape(
        payload.get("lineage"), root=root, label=f"{label}.lineage", errors=errors
    )

    builder_ids = set(
        _string_list(
            payload.get("builder_ids"),
            f"{label}.builder_ids",
            errors,
            nonempty=True,
            identifiers=True,
        )
    )
    iterations = _list(payload.get("iterations"), f"{label}.iterations", errors)
    iteration_list = iterations if iterations is not None else []

    baseline_vector: tuple[int, int, int, int] | None = None
    baseline = _mapping(payload.get("baseline"), f"{label}.baseline", errors)
    if baseline is not None:
        _check_keys(
            baseline,
            required={"summary", "quality_vector", "checks"},
            allowed={"summary", "quality_vector", "checks"},
            label=f"{label}.baseline",
            errors=errors,
        )
        _nonempty_string(baseline.get("summary"), f"{label}.baseline.summary", errors)
        baseline_vector = _quality_vector(
            baseline.get("quality_vector"), f"{label}.baseline.quality_vector", errors
        )
        _validate_checks(
            baseline.get("checks"),
            label=f"{label}.baseline.checks",
            criteria_by_id=criteria_by_id,
            root=root,
            errors=errors,
            nonempty=True,
        )

    failures_by_id: dict[str, dict[str, Any]] = {}
    failure_keys: set[str] = set()
    run_risk_tags: set[str] = set()
    failures = _list(payload.get("failures"), f"{label}.failures", errors)
    lifecycle_present = bool(
        failures
        and any(
            isinstance(failure, dict)
            and ("discovered_iteration" in failure or "resolved_iteration" in failure)
            for failure in failures
        )
    )
    strict_lifecycle = status in {"AWAITING_REVIEW", "COMPLETE"} or lifecycle_present
    if failures is not None:
        for index, raw_failure in enumerate(failures):
            failure_label = f"{label}.failures[{index}]"
            failure = _mapping(raw_failure, failure_label, errors)
            if failure is None:
                continue
            required_failure_keys = {
                "id",
                "failure_key",
                "criterion_ids",
                "severity",
                "status",
                "attempts",
                "summary",
            }
            if strict_lifecycle:
                required_failure_keys.add("discovered_iteration")
            _check_keys(
                failure,
                required=required_failure_keys,
                allowed={
                    "id",
                    "failure_key",
                    "criterion_ids",
                    "severity",
                    "status",
                    "attempts",
                    "discovered_iteration",
                    "resolved_iteration",
                    "summary",
                    "resolution",
                    "risk_tags",
                },
                label=failure_label,
                errors=errors,
            )
            failure_id = _identifier(failure.get("id"), f"{failure_label}.id", errors)
            failure_key = _identifier(
                failure.get("failure_key"), f"{failure_label}.failure_key", errors
            )
            if failure_id is not None:
                if failure_id in failures_by_id:
                    errors.append(f"{label}.failures: duplicate id '{failure_id}'")
                failures_by_id[failure_id] = failure
            if failure_key is not None:
                if failure_key in failure_keys:
                    errors.append(
                        f"{label}.failures: duplicate failure_key '{failure_key}'"
                    )
                failure_keys.add(failure_key)
            criterion_ids = _string_list(
                failure.get("criterion_ids"),
                f"{failure_label}.criterion_ids",
                errors,
                nonempty=True,
                identifiers=True,
            )
            for criterion_id in criterion_ids:
                if criterion_id not in criteria_by_id:
                    errors.append(
                        f"{failure_label}.criterion_ids: unknown criterion '{criterion_id}'"
                    )
            if failure.get("severity") not in SEVERITIES:
                errors.append(f"{failure_label}.severity: must be P0, P1, P2, or P3")
            failure_status = failure.get("status")
            if failure_status not in {"CONFIRMED", "RESOLVED", "DEFERRED", "ESCALATED"}:
                errors.append(
                    f"{failure_label}.status: unsupported status '{failure_status}'"
                )
            attempts = failure.get("attempts")
            if type(attempts) is not int or attempts < 0:
                errors.append(
                    f"{failure_label}.attempts: must be a non-negative integer"
                )
            discovered = failure.get("discovered_iteration")
            if strict_lifecycle or "discovered_iteration" in failure:
                if type(discovered) is not int or discovered < 0:
                    errors.append(
                        f"{failure_label}.discovered_iteration: must be a non-negative integer"
                    )
                else:
                    maximum_discovery = len(iteration_list) + (
                        1 if status == "ACTIVE" else 0
                    )
                    if discovered > maximum_discovery:
                        errors.append(
                            f"{failure_label}.discovered_iteration: cannot exceed "
                            f"{maximum_discovery} for this run"
                        )
            resolved = failure.get("resolved_iteration")
            if failure_status == "RESOLVED" and strict_lifecycle:
                if type(resolved) is not int or resolved < 1:
                    errors.append(
                        f"{failure_label}.resolved_iteration: RESOLVED failure requires a positive iteration"
                    )
                elif type(discovered) is int and resolved < max(1, discovered):
                    errors.append(
                        f"{failure_label}.resolved_iteration: cannot precede discovery"
                    )
                elif resolved > len(iteration_list):
                    errors.append(
                        f"{failure_label}.resolved_iteration: exceeds recorded iterations"
                    )
            elif failure_status != "RESOLVED" and "resolved_iteration" in failure:
                errors.append(
                    f"{failure_label}.resolved_iteration: only permitted for RESOLVED failures"
                )
            _nonempty_string(failure.get("summary"), f"{failure_label}.summary", errors)
            if failure_status == "RESOLVED":
                _nonempty_string(
                    failure.get("resolution"), f"{failure_label}.resolution", errors
                )
            elif "resolution" in failure and failure.get("resolution") is not None:
                errors.append(
                    f"{failure_label}.resolution: only permitted for RESOLVED failures"
                )
            if "risk_tags" in failure:
                run_risk_tags.update(
                    _risk_tags(
                        failure.get("risk_tags"), f"{failure_label}.risk_tags", errors
                    )
                )
    if strict_lifecycle and baseline_vector is not None:
        derived_baseline = _derived_quality_vector(failures_by_id, 0, after=False)
        if baseline_vector != derived_baseline:
            errors.append(
                f"{label}.baseline.quality_vector: recorded {list(baseline_vector)}, "
                f"derived {list(derived_baseline)} from failure lifecycle"
            )
    attempt_counts: dict[str, int] = {}
    repair_authors: set[str] = set()
    best_vector = baseline_vector
    assessments: list[str] = []
    for index, raw_iteration in enumerate(iteration_list):
        iteration_label = f"{label}.iterations[{index}]"
        iteration = _mapping(raw_iteration, iteration_label, errors)
        if iteration is None:
            continue
        _check_keys(
            iteration,
            required={
                "number",
                "primary_failure_id",
                "repair",
                "before",
                "after",
                "assessment",
                "kept",
                "targeted_checks",
                "regression_checks",
            },
            allowed={
                "number",
                "primary_failure_id",
                "repair",
                "before",
                "after",
                "assessment",
                "kept",
                "targeted_checks",
                "regression_checks",
            },
            label=iteration_label,
            errors=errors,
        )
        expected_number = index + 1
        if iteration.get("number") != expected_number:
            errors.append(
                f"{iteration_label}.number: iterations must be contiguous from 1; expected {expected_number}"
            )
        failure_id = _identifier(
            iteration.get("primary_failure_id"),
            f"{iteration_label}.primary_failure_id",
            errors,
        )
        failure = failures_by_id.get(failure_id or "")
        if failure_id is not None and failure is None:
            errors.append(
                f"{iteration_label}.primary_failure_id: unknown failure '{failure_id}'"
            )
        elif failure_id is not None:
            attempt_counts[failure_id] = attempt_counts.get(failure_id, 0) + 1

        repair = _mapping(iteration.get("repair"), f"{iteration_label}.repair", errors)
        if repair is not None:
            _check_keys(
                repair,
                required={"author_id", "summary"},
                allowed={"author_id", "summary", "references"},
                label=f"{iteration_label}.repair",
                errors=errors,
            )
            author_id = _identifier(
                repair.get("author_id"), f"{iteration_label}.repair.author_id", errors
            )
            if author_id is not None:
                repair_authors.add(author_id)
                if author_id not in builder_ids:
                    errors.append(
                        f"{iteration_label}.repair.author_id: '{author_id}' is absent from builder_ids"
                    )
            _nonempty_string(
                repair.get("summary"), f"{iteration_label}.repair.summary", errors
            )
            if "references" in repair:
                _reference_list(
                    repair.get("references"),
                    root,
                    f"{iteration_label}.repair.references",
                    errors,
                )

        snapshots: dict[str, tuple[int, int, int, int] | None] = {}
        for snapshot_name in ("before", "after"):
            snapshot_label = f"{iteration_label}.{snapshot_name}"
            snapshot = _mapping(iteration.get(snapshot_name), snapshot_label, errors)
            if snapshot is None:
                snapshots[snapshot_name] = None
                continue
            _check_keys(
                snapshot,
                required={"quality_vector", "evidence"},
                allowed={"quality_vector", "evidence"},
                label=snapshot_label,
                errors=errors,
            )
            snapshots[snapshot_name] = _quality_vector(
                snapshot.get("quality_vector"),
                f"{snapshot_label}.quality_vector",
                errors,
            )
            _nonempty_string(
                snapshot.get("evidence"), f"{snapshot_label}.evidence", errors
            )
        before = snapshots.get("before")
        after = snapshots.get("after")
        effective_before = before
        effective_after = after
        if strict_lifecycle:
            derived_before = _derived_quality_vector(
                failures_by_id, expected_number, after=False
            )
            derived_after = _derived_quality_vector(
                failures_by_id, expected_number, after=True
            )
            effective_before = derived_before
            effective_after = derived_after
            if before is not None and before != derived_before:
                errors.append(
                    f"{iteration_label}.before.quality_vector: recorded {list(before)}, "
                    f"derived {list(derived_before)} from failure lifecycle"
                )
            if after is not None and after != derived_after:
                errors.append(
                    f"{iteration_label}.after.quality_vector: recorded {list(after)}, "
                    f"derived {list(derived_after)} from failure lifecycle"
                )
            open_before = _open_failure_ids(
                failures_by_id, expected_number, after=False
            )
            if failure_id is not None and failure_id not in open_before:
                errors.append(
                    f"{iteration_label}.primary_failure_id: selected failure is not open before repair"
                )
            open_severities = [
                SEVERITIES.index(str(failures_by_id[open_id].get("severity")))
                for open_id in open_before
                if failures_by_id[open_id].get("severity") in SEVERITIES
            ]
            if (
                failure is not None
                and failure.get("severity") in SEVERITIES
                and open_severities
                and SEVERITIES.index(str(failure.get("severity")))
                != min(open_severities)
            ):
                errors.append(
                    f"{iteration_label}.primary_failure_id: does not select the "
                    "highest-impact open derived severity"
                )
        else:
            if before is not None and best_vector is not None and before != best_vector:
                errors.append(
                    f"{iteration_label}.before.quality_vector: must equal the best "
                    f"retained vector {list(best_vector)}"
                )
            if (
                before is not None
                and failure is not None
                and failure.get("severity") in SEVERITIES
            ):
                severity_index = SEVERITIES.index(str(failure.get("severity")))
                if any(before[priority] > 0 for priority in range(severity_index)):
                    errors.append(
                        f"{iteration_label}.primary_failure_id: does not select the "
                        "highest-impact open severity"
                    )
                if before[severity_index] == 0:
                    errors.append(
                        f"{iteration_label}.before.quality_vector: records no open "
                        f"{SEVERITIES[severity_index]} failure"
                    )

        expected_assessment: str | None = None
        expected_kept: bool | None = None
        if effective_before is not None and effective_after is not None:
            if effective_after < effective_before:
                expected_assessment = "IMPROVED"
                expected_kept = True
                if not strict_lifecycle:
                    best_vector = effective_after
            elif effective_after == effective_before:
                expected_assessment = "NO_CHANGE"
                expected_kept = False
            else:
                expected_assessment = "REGRESSED"
                expected_kept = False
        assessment = iteration.get("assessment")
        if assessment not in {"IMPROVED", "NO_CHANGE", "REGRESSED"}:
            errors.append(
                f"{iteration_label}.assessment: unsupported value '{assessment}'"
            )
        else:
            assessments.append(assessment)
        if expected_assessment is not None and assessment != expected_assessment:
            errors.append(
                f"{iteration_label}.assessment: must be {expected_assessment} from the quality vectors"
            )
        if type(iteration.get("kept")) is not bool:
            errors.append(f"{iteration_label}.kept: must be a boolean")
        elif expected_kept is not None and iteration.get("kept") is not expected_kept:
            errors.append(
                f"{iteration_label}.kept: must be {str(expected_kept).lower()} from the quality vectors"
            )
        _validate_checks(
            iteration.get("targeted_checks"),
            label=f"{iteration_label}.targeted_checks",
            criteria_by_id=criteria_by_id,
            root=root,
            errors=errors,
            nonempty=True,
        )
        regression_checks = _validate_checks(
            iteration.get("regression_checks"),
            label=f"{iteration_label}.regression_checks",
            criteria_by_id=criteria_by_id,
            root=root,
            errors=errors,
            nonempty=True,
            regression_only=True,
        )
        if iteration.get("kept") is True and any(
            check.get("result") != "PASS" for check in regression_checks
        ):
            errors.append(
                f"{iteration_label}: kept repair requires every regression check to PASS"
            )

    for failure_id, failure in failures_by_id.items():
        recorded_attempts = failure.get("attempts")
        actual_attempts = attempt_counts.get(failure_id, 0)
        if type(recorded_attempts) is int and recorded_attempts != actual_attempts:
            errors.append(
                f"{label}.failures[{failure_id}].attempts: recorded {recorded_attempts}, derived {actual_attempts}"
            )

    final_checks = _validate_checks(
        payload.get("final_checks"),
        label=f"{label}.final_checks",
        criteria_by_id=criteria_by_id,
        root=root,
        errors=errors,
    )
    final_check_ids = [str(check.get("criterion_id")) for check in final_checks]
    if len(final_check_ids) != len(set(final_check_ids)):
        errors.append(f"{label}.final_checks: criterion ids must be unique")

    all_authors = builder_ids | repair_authors
    reviewers_by_role: dict[str, dict[str, Any]] = {}
    reviewers_by_id: dict[str, dict[str, Any]] = {}
    reviewer_ids: set[str] = set()
    reviewers = _list(payload.get("reviewers"), f"{label}.reviewers", errors)
    if reviewers is not None:
        for index, raw_reviewer in enumerate(reviewers):
            reviewer_label = f"{label}.reviewers[{index}]"
            reviewer = _mapping(raw_reviewer, reviewer_label, errors)
            if reviewer is None:
                continue
            _check_keys(
                reviewer,
                required={
                    "reviewer_id",
                    "role",
                    "independent",
                    "disposition",
                    "evidence",
                },
                allowed={
                    "reviewer_id",
                    "role",
                    "independent",
                    "disposition",
                    "score",
                    "evidence",
                    "evidence_refs",
                    "risk_tags_reviewed",
                },
                label=reviewer_label,
                errors=errors,
            )
            reviewer_id = _identifier(
                reviewer.get("reviewer_id"), f"{reviewer_label}.reviewer_id", errors
            )
            role = _identifier(reviewer.get("role"), f"{reviewer_label}.role", errors)
            if reviewer_id is not None:
                if reviewer_id in reviewer_ids:
                    errors.append(
                        f"{label}.reviewers: duplicate reviewer_id '{reviewer_id}'"
                    )
                reviewer_ids.add(reviewer_id)
                reviewers_by_id[reviewer_id] = reviewer
            if role is not None:
                if role in reviewers_by_role:
                    errors.append(
                        f"{label}.reviewers: duplicate reviewer role '{role}'"
                    )
                reviewers_by_role[role] = reviewer
            independent = reviewer.get("independent")
            if type(independent) is not bool:
                errors.append(f"{reviewer_label}.independent: must be a boolean")
            if independent is True and reviewer_id in all_authors:
                errors.append(
                    f"{reviewer_label}: independent reviewer '{reviewer_id}' authored the run or a repair"
                )
            if reviewer.get("disposition") not in {"ACCEPT", "REJECT", "ABSTAIN"}:
                errors.append(f"{reviewer_label}.disposition: unsupported value")
            if "score" in reviewer and type(reviewer.get("score")) not in (int, float):
                errors.append(f"{reviewer_label}.score: must be numeric")
            _nonempty_string(
                reviewer.get("evidence"), f"{reviewer_label}.evidence", errors
            )
            if "evidence_refs" in reviewer:
                _reference_list(
                    reviewer.get("evidence_refs"),
                    root,
                    f"{reviewer_label}.evidence_refs",
                    errors,
                )
            if "risk_tags_reviewed" in reviewer:
                _risk_tags(
                    reviewer.get("risk_tags_reviewed"),
                    f"{reviewer_label}.risk_tags_reviewed",
                    errors,
                )

    _validate_rubric_results(
        payload.get("rubric_results"),
        root=root,
        label=f"{label}.rubric_results",
        reviewer_ids=set(reviewers_by_id),
        errors=errors,
        require_thresholds=False,
    )

    remaining_risks = _list(
        payload.get("remaining_risks"), f"{label}.remaining_risks", errors
    )
    if remaining_risks is not None:
        risk_ids: set[str] = set()
        for index, raw_risk in enumerate(remaining_risks):
            risk_label = f"{label}.remaining_risks[{index}]"
            risk = _mapping(raw_risk, risk_label, errors)
            if risk is None:
                continue
            _check_keys(
                risk,
                required={"id", "severity", "summary"},
                allowed={"id", "severity", "summary", "risk_tags", "references"},
                label=risk_label,
                errors=errors,
            )
            risk_id = _identifier(risk.get("id"), f"{risk_label}.id", errors)
            if risk_id is not None:
                if risk_id in risk_ids:
                    errors.append(f"{label}.remaining_risks: duplicate id '{risk_id}'")
                risk_ids.add(risk_id)
            if risk.get("severity") not in SEVERITIES:
                errors.append(f"{risk_label}.severity: must be P0, P1, P2, or P3")
            _nonempty_string(risk.get("summary"), f"{risk_label}.summary", errors)
            if "risk_tags" in risk:
                run_risk_tags.update(
                    _risk_tags(risk.get("risk_tags"), f"{risk_label}.risk_tags", errors)
                )
            if "references" in risk:
                _reference_list(
                    risk.get("references"), root, f"{risk_label}.references", errors
                )

    _validate_risk_routing(run_risk_tags, set(required_reviewers), label, errors)
    _validate_authorization_routing(run_risk_tags, criteria_by_id, label, errors)

    _validate_continuity(
        payload.get("continuity"),
        root=root,
        label=f"{label}.continuity",
        run_id=run_id,
        required=status == "COMPLETE",
        errors=errors,
    )

    disposition = payload.get("final_disposition")
    completed_at = payload.get("completed_at")
    if status in {"ACTIVE", "AWAITING_REVIEW"}:
        if disposition is not None:
            errors.append(f"{label}.final_disposition: {status} run must use null")
        if completed_at is not None:
            errors.append(f"{label}.completed_at: {status} run must use null")
    elif status == "COMPLETE":
        if disposition not in {"PASS", "FAIL", "ESCALATE"}:
            errors.append(
                f"{label}.final_disposition: COMPLETE run requires PASS, FAIL, or ESCALATE"
            )
        _timestamp(completed_at, f"{label}.completed_at", errors)

    budget = contract.get("iteration_budget")
    if type(budget) is int:
        if len(iteration_list) > budget:
            errors.append(
                f"{label}: recorded {len(iteration_list)} iterations exceeds budget {budget}"
            )
        if status == "AWAITING_REVIEW" and len(iteration_list) != budget:
            errors.append(
                f"{label}: AWAITING_REVIEW requires the repair budget to be reached "
                f"exactly ({len(iteration_list)} != {budget})"
            )
        if len(iteration_list) == budget and status == "ACTIVE":
            errors.append(f"{label}: iteration budget is exhausted; run must stop")
        elif (
            len(iteration_list) == budget
            and status == "COMPLETE"
            and disposition not in {"PASS", "ESCALATE"}
        ):
            errors.append(
                f"{label}.final_disposition: exhausted budget requires PASS or ESCALATE"
            )
    if status == "AWAITING_REVIEW":
        for failure_id, failure in failures_by_id.items():
            failure_status = failure.get("status")
            severity = failure.get("severity")
            valid_deferral = failure_status == "DEFERRED" and severity in {"P2", "P3"}
            if valid_deferral and severity == "P2":
                raw_criterion_ids = failure.get("criterion_ids")
                criterion_ids = (
                    raw_criterion_ids if isinstance(raw_criterion_ids, list) else []
                )
                valid_deferral = bool(criterion_ids) and all(
                    criteria_by_id.get(str(criterion_id), {}).get("mandatory") is False
                    for criterion_id in criterion_ids
                )
            if failure_status != "RESOLVED" and not valid_deferral:
                errors.append(
                    f"{label}.failures[{failure_id}]: AWAITING_REVIEW permits only "
                    "RESOLVED failures or valid non-mandatory P2/P3 deferrals"
                )
    unresolved_three_attempt = any(
        attempt_counts.get(failure_id, 0) >= 3 and failure.get("status") != "RESOLVED"
        for failure_id, failure in failures_by_id.items()
    )
    if unresolved_three_attempt and not (
        status == "COMPLETE" and disposition == "ESCALATE"
    ):
        errors.append(
            f"{label}: an unresolved failure survived 3 repairs; run must ESCALATE"
        )
    two_no_improvement = any(
        left != "IMPROVED" and right != "IMPROVED"
        for left, right in pairwise(assessments)
    )
    if two_no_improvement and not (status == "COMPLETE" and disposition == "ESCALATE"):
        errors.append(
            f"{label}: 2 consecutive iterations produced no improvement; run must ESCALATE"
        )

    return errors


def derive_pass_errors(
    run: dict[str, Any],
    contract: dict[str, Any],
    criteria_by_id: dict[str, dict[str, Any]],
    required_reviewers: dict[str, dict[str, Any]],
    label: str,
    root: Path,
) -> list[str]:
    """Derive acceptance from evidence; never trust final_disposition by itself."""
    errors: list[str] = []
    if run.get("status") != "COMPLETE":
        errors.append(f"{label}: acceptance requires status COMPLETE")
    if run.get("final_disposition") != "PASS":
        errors.append(f"{label}: acceptance requires final_disposition PASS")

    raw_checks = run.get("final_checks")
    checks = raw_checks if isinstance(raw_checks, list) else []
    checks_by_id = {
        str(check.get("criterion_id")): check
        for check in checks
        if isinstance(check, dict)
    }
    for criterion_id, criterion in criteria_by_id.items():
        if criterion.get("mandatory") is True or criterion.get("class") == "regression":
            check = checks_by_id.get(criterion_id)
            if check is None or check.get("result") != "PASS":
                errors.append(f"{label}: criterion {criterion_id} lacks a final PASS")

    raw_failures = run.get("failures")
    failures = raw_failures if isinstance(raw_failures, list) else []
    for failure in failures:
        if (
            isinstance(failure, dict)
            and failure.get("severity") in {"P0", "P1"}
            and failure.get("status") != "RESOLVED"
        ):
            errors.append(
                f"{label}: unresolved {failure.get('severity')} failure {failure.get('id')} blocks PASS"
            )
    raw_risks = run.get("remaining_risks")
    risks = raw_risks if isinstance(raw_risks, list) else []
    for risk in risks:
        if isinstance(risk, dict) and risk.get("severity") in {"P0", "P1"}:
            errors.append(
                f"{label}: remaining {risk.get('severity')} risk {risk.get('id')} blocks PASS"
            )

    raw_builders = run.get("builder_ids")
    builders = (
        {str(item) for item in raw_builders}
        if isinstance(raw_builders, list)
        else set()
    )
    raw_iterations = run.get("iterations")
    iterations = raw_iterations if isinstance(raw_iterations, list) else []
    for iteration in iterations:
        if isinstance(iteration, dict) and isinstance(iteration.get("repair"), dict):
            builders.add(str(iteration["repair"].get("author_id")))
    raw_reviewers = run.get("reviewers")
    reviewers = raw_reviewers if isinstance(raw_reviewers, list) else []
    reviewer_ids = {
        str(reviewer.get("reviewer_id"))
        for reviewer in reviewers
        if isinstance(reviewer, dict)
    }
    rubric_evaluations = _validate_rubric_results(
        run.get("rubric_results"),
        root=root,
        label=f"{label}.rubric_results",
        reviewer_ids=reviewer_ids,
        errors=errors,
        require_thresholds=True,
    )
    for role, requirement in required_reviewers.items():
        matching = [
            reviewer
            for reviewer in reviewers
            if isinstance(reviewer, dict) and reviewer.get("role") == role
        ]
        if len(matching) != 1:
            errors.append(f"{label}: required reviewer role '{role}' is missing")
            continue
        reviewer = matching[0]
        reviewer_id = str(reviewer.get("reviewer_id"))
        if reviewer.get("independent") is not True or reviewer_id in builders:
            errors.append(f"{label}: reviewer role '{role}' is not author-independent")
        if reviewer.get("disposition") != "ACCEPT":
            errors.append(f"{label}: reviewer role '{role}' did not ACCEPT")
        minimum_score = requirement.get("minimum_score")
        if isinstance(minimum_score, (int, float)) and not isinstance(
            minimum_score, bool
        ):
            score = reviewer.get("score")
            if (
                not isinstance(score, (int, float))
                or isinstance(score, bool)
                or float(score) < float(minimum_score)
            ):
                errors.append(
                    f"{label}: reviewer role '{role}' is below minimum score {minimum_score}"
                )
        rubric_ref = requirement.get("rubric_ref")
        if isinstance(rubric_ref, str):
            normalized_ref = (
                rubric_ref.strip().strip("<>").split("#", 1)[0].replace("\\", "/")
            )
            if (reviewer_id, normalized_ref) not in rubric_evaluations:
                errors.append(
                    f"{label}: reviewer role '{role}' lacks required rubric '{normalized_ref}'"
                )

    return errors


def _looks_like_local_reference(text: str) -> bool:
    candidate = text.strip().strip("<>")
    if not candidate or any(character.isspace() for character in candidate):
        return False
    if candidate.startswith(("$", "--")) or "*" in candidate:
        return False
    suffix = Path(candidate.split("#", 1)[0]).suffix.lower()
    return (
        "/" in candidate
        or "\\" in candidate
        or suffix
        in {
            ".md",
            ".yaml",
            ".yml",
            ".json",
            ".py",
        }
    )


def validate_agents(root: Path) -> list[str]:
    errors: list[str] = []
    agents_path = root / "AGENTS.md"
    policy_path = root / "quality/agents-policy.yaml"
    if not agents_path.exists():
        return ["AGENTS.md: file is missing"]
    policy = _load_mapping(policy_path, "quality/agents-policy.yaml", errors)
    if policy is None:
        return errors
    text = agents_path.read_text(encoding="utf-8")

    target = policy.get("target", "AGENTS.md")
    if target != "AGENTS.md":
        errors.append("quality/agents-policy.yaml.target: must equal AGENTS.md")
    limits = _mapping(policy.get("limits"), "quality/agents-policy.yaml.limits", errors)
    if limits is not None:
        metrics = {
            "max_lines": len(text.splitlines()),
            "max_nonblank_lines": sum(bool(line.strip()) for line in text.splitlines()),
            "max_words": len(re.findall(r"\b[\w'-]+\b", text)),
            "max_bytes": len(text.encode("utf-8")),
        }
        for unknown_limit in sorted(set(limits) - set(metrics)):
            errors.append(
                f"quality/agents-policy.yaml.limits: unknown limit '{unknown_limit}'"
            )
        for key, actual in metrics.items():
            if key not in limits:
                continue
            limit = limits[key]
            if type(limit) is not int or limit < 1:
                errors.append(
                    f"quality/agents-policy.yaml.limits.{key}: must be positive integer"
                )
            elif actual > limit:
                errors.append(f"AGENTS.md: {key} limit exceeded ({actual} > {limit})")

    headings = {
        match.group(1).strip()
        for match in re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.MULTILINE)
    }
    required_headings = _string_list(
        policy.get("required_headings"),
        "quality/agents-policy.yaml.required_headings",
        errors,
        nonempty=True,
    )
    for heading in required_headings:
        normalized = re.sub(r"^#{1,6}\s+", "", heading).strip()
        if normalized not in headings:
            errors.append(f"AGENTS.md: missing required heading '{normalized}'")

    required_phrases = _string_list(
        policy.get("required_phrases"),
        "quality/agents-policy.yaml.required_phrases",
        errors,
        nonempty=True,
    )
    lower_text = text.lower()
    for phrase in required_phrases:
        if phrase.lower() not in lower_text:
            errors.append(f"AGENTS.md: missing required phrase '{phrase}'")

    required_references = _string_list(
        policy.get("required_references"),
        "quality/agents-policy.yaml.required_references",
        errors,
        nonempty=True,
    )
    for index, reference in enumerate(required_references):
        _safe_repo_reference(
            root,
            reference,
            f"quality/agents-policy.yaml.required_references[{index}]",
            errors,
        )
        if reference not in text:
            errors.append(f"AGENTS.md: missing required reference '{reference}'")

    discovered: set[str] = set()
    for match in MARKDOWN_LINK_PATTERN.finditer(text):
        reference = match.group(1).strip()
        if "://" not in reference and not reference.startswith("mailto:"):
            discovered.add(reference)
    for match in CODE_SPAN_PATTERN.finditer(text):
        reference = match.group(1).strip()
        if _looks_like_local_reference(reference):
            discovered.add(reference)
    for reference in sorted(discovered):
        _safe_repo_reference(
            root, reference, f"AGENTS.md reference '{reference}'", errors
        )
    return sorted(set(errors))


def _validate_schema_files(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in (
        "quality/schemas/success-contract.schema.json",
        "quality/schemas/run.schema.json",
    ):
        path = root / relative
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative}: unreadable JSON Schema: {exc}")
            continue
        if not isinstance(payload, dict) or payload.get("type") != "object":
            errors.append(f"{relative}: schema root must describe an object")
    return errors


def validate_cross_run_lineage(
    contracts: dict[str, dict[str, Any]],
    runs: dict[str, dict[str, Any]],
) -> list[str]:
    """Prevent a new run from silently resetting escalation or stable failures."""
    errors: list[str] = []
    for run_id, run in runs.items():
        raw_lineage = run.get("lineage")
        if not isinstance(raw_lineage, dict):
            continue
        predecessor_id = raw_lineage.get("predecessor_run_id")
        predecessor = runs.get(str(predecessor_id))
        if predecessor is None:
            errors.append(
                f"quality run {run_id}.lineage: unknown predecessor_run_id "
                f"'{predecessor_id}'"
            )
            continue
        if predecessor_id == run_id:
            errors.append(f"quality run {run_id}.lineage: run cannot succeed itself")
        if raw_lineage.get("predecessor_contract_id") != predecessor.get("contract_id"):
            errors.append(
                f"quality run {run_id}.lineage.predecessor_contract_id: does not "
                "match predecessor run"
            )
        if run.get("milestone") != predecessor.get("milestone"):
            errors.append(
                f"quality run {run_id}.lineage: predecessor must share the milestone"
            )

    runs_by_milestone: dict[str, list[dict[str, Any]]] = {}
    for run in runs.values():
        milestone = run.get("milestone")
        if isinstance(milestone, str):
            runs_by_milestone.setdefault(milestone, []).append(run)
    for milestone_runs in runs_by_milestone.values():
        milestone_runs.sort(
            key=lambda run: (str(run.get("started_at", "")), str(run.get("run_id", "")))
        )
        for predecessor, successor in pairwise(milestone_runs):
            raw_failures = predecessor.get("failures")
            predecessor_failures = (
                raw_failures if isinstance(raw_failures, list) else []
            )
            unresolved_keys = {
                str(failure.get("failure_key"))
                for failure in predecessor_failures
                if isinstance(failure, dict)
                and failure.get("status") != "RESOLVED"
                and isinstance(failure.get("failure_key"), str)
            }
            requires_lineage = predecessor.get(
                "final_disposition"
            ) == "ESCALATE" or bool(unresolved_keys)
            if not requires_lineage:
                continue
            successor_id = str(successor.get("run_id"))
            predecessor_id = str(predecessor.get("run_id"))
            lineage = successor.get("lineage")
            if not isinstance(lineage, dict):
                errors.append(
                    f"quality run {successor_id}: predecessor {predecessor_id} "
                    "escalated or has unresolved failures; successor lineage is required"
                )
                continue
            if lineage.get("predecessor_run_id") != predecessor_id:
                errors.append(
                    f"quality run {successor_id}.lineage.predecessor_run_id: must "
                    f"equal '{predecessor_id}'"
                )
            predecessor_contract_id = str(predecessor.get("contract_id"))
            if lineage.get("predecessor_contract_id") != predecessor_contract_id:
                errors.append(
                    f"quality run {successor_id}.lineage.predecessor_contract_id: "
                    f"must equal '{predecessor_contract_id}'"
                )
            carried_raw = lineage.get("carried_failure_keys")
            resolved_raw = lineage.get("resolved_failure_keys")
            carried = set(carried_raw) if isinstance(carried_raw, list) else set()
            resolved = set(resolved_raw) if isinstance(resolved_raw, list) else set()
            accounted = carried | resolved
            missing = unresolved_keys - accounted
            if missing:
                errors.append(
                    f"quality run {successor_id}.lineage: unresolved stable failure "
                    f"keys were reset: {', '.join(sorted(missing))}"
                )
            extra = accounted - unresolved_keys
            if extra:
                errors.append(
                    f"quality run {successor_id}.lineage: non-predecessor failure "
                    f"keys claimed: {', '.join(sorted(str(item) for item in extra))}"
                )
            successor_failures_raw = successor.get("failures")
            successor_failures = (
                successor_failures_raw
                if isinstance(successor_failures_raw, list)
                else []
            )
            successor_by_key = {
                str(failure.get("failure_key")): failure
                for failure in successor_failures
                if isinstance(failure, dict)
                and isinstance(failure.get("failure_key"), str)
            }
            missing_carried = carried - set(successor_by_key)
            if missing_carried:
                errors.append(
                    f"quality run {successor_id}.lineage: carried failure keys absent "
                    f"from successor failures: {', '.join(sorted(missing_carried))}"
                )
            unresolved_claimed_resolved = {
                key
                for key in resolved
                if key in successor_by_key
                and successor_by_key[key].get("status") != "RESOLVED"
            }
            if unresolved_claimed_resolved:
                errors.append(
                    f"quality run {successor_id}.lineage: resolved failure keys remain "
                    f"open: {', '.join(sorted(unresolved_claimed_resolved))}"
                )

            successor_contract_id = str(successor.get("contract_id"))
            if successor_contract_id != predecessor_contract_id:
                successor_contract = contracts.get(successor_contract_id)
                contract_lineage = (
                    successor_contract.get("lineage")
                    if isinstance(successor_contract, dict)
                    else None
                )
                if not isinstance(contract_lineage, dict):
                    errors.append(
                        f"quality contract {successor_contract_id}: successor contract "
                        "lineage is required"
                    )
                else:
                    if (
                        contract_lineage.get("supersedes_contract_id")
                        != predecessor_contract_id
                    ):
                        errors.append(
                            f"quality contract {successor_contract_id}.lineage: must "
                            f"supersede '{predecessor_contract_id}'"
                        )
                    if contract_lineage.get("predecessor_run_id") != predecessor_id:
                        errors.append(
                            f"quality contract {successor_contract_id}.lineage: must "
                            f"name predecessor run '{predecessor_id}'"
                        )
                    if contract_lineage.get("escalation_resolution_ref") != lineage.get(
                        "escalation_resolution_ref"
                    ):
                        errors.append(
                            f"quality contract {successor_contract_id}.lineage: resolution "
                            "reference must match successor run"
                        )
    return errors


def validate_repository(
    root: Path, *, artifacts_only: bool = False
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    root = root.resolve()
    errors = _validate_schema_files(root)
    if not artifacts_only:
        errors.extend(validate_agents(root))

    contracts: dict[str, dict[str, Any]] = {}
    contract_meta: dict[
        str, tuple[Path, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
    ] = {}
    contract_paths = sorted((root / "quality/contracts").glob("*.y*ml"))
    if not contract_paths:
        errors.append("quality/contracts: no success contracts found")
    for path in contract_paths:
        payload = _load_mapping(path, path.relative_to(root).as_posix(), errors)
        if payload is None:
            continue
        contract_errors, criteria, reviewers = validate_contract(payload, path, root)
        errors.extend(contract_errors)
        contract_id = payload.get("contract_id")
        if isinstance(contract_id, str):
            if contract_id in contracts:
                errors.append(
                    f"quality/contracts: duplicate contract_id '{contract_id}'"
                )
            contracts[contract_id] = payload
            contract_meta[contract_id] = (path, criteria, reviewers)

    runs: dict[str, dict[str, Any]] = {}
    run_paths = sorted((root / "quality/runs").glob("*.y*ml"))
    if not run_paths:
        errors.append("quality/runs: no quality runs found")
    for path in run_paths:
        payload = _load_mapping(path, path.relative_to(root).as_posix(), errors)
        if payload is None:
            continue
        run_id = payload.get("run_id")
        if isinstance(run_id, str):
            if run_id in runs:
                errors.append(f"quality/runs: duplicate run_id '{run_id}'")
            runs[run_id] = payload
        contract_id = payload.get("contract_id")
        if not isinstance(contract_id, str) or contract_id not in contracts:
            errors.append(
                f"{path.relative_to(root).as_posix()}.contract_id: no matching contract"
            )
            continue
        _, criteria, reviewers = contract_meta[contract_id]
        errors.extend(
            validate_run(
                payload,
                path,
                root,
                contracts[contract_id],
                contract_meta[contract_id][0],
                criteria,
                reviewers,
            )
        )
    errors.extend(validate_cross_run_lineage(contracts, runs))
    return sorted(set(errors)), contracts, runs


def _select_run(
    selector: str,
    root: Path,
    runs: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[str, dict[str, Any]] | None:
    if selector in runs:
        return selector, runs[selector]
    normalized = selector.replace("\\", "/")
    _safe_repo_reference(root, normalized, "--require-pass", errors)
    path = (root / normalized).resolve()
    if errors:
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"--require-pass: unreadable run: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append("--require-pass: selected run is not a mapping")
        return None
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or run_id not in runs:
        errors.append("--require-pass: selected file is not a discovered quality run")
        return None
    return run_id, runs[run_id]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate inert, bounded quality-gauntlet contracts and recorded runs."
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--all", action="store_true", help="validate policy and all artifacts"
    )
    mode.add_argument(
        "--artifacts-only", action="store_true", help="skip AGENTS.md policy validation"
    )
    mode.add_argument(
        "--require-pass",
        metavar="RUN_ID_OR_PATH",
        help="derive acceptance for one structurally valid completed run",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors, contracts, runs = validate_repository(
        root, artifacts_only=bool(args.artifacts_only)
    )
    if args.require_pass and not errors:
        selected = _select_run(args.require_pass, root, runs, errors)
        if selected is not None:
            run_id, run = selected
            contract_id = run.get("contract_id")
            contract = contracts.get(str(contract_id))
            if contract is None:
                errors.append(f"{run_id}: matching contract is unavailable")
            else:
                contract_path = root / "quality/contracts" / f"{contract_id}.yaml"
                contract_errors, criteria, reviewers = validate_contract(
                    contract, contract_path, root
                )
                errors.extend(contract_errors)
                errors.extend(
                    derive_pass_errors(run, contract, criteria, reviewers, run_id, root)
                )
    if errors:
        print("Quality validation failed:")
        for error in sorted(set(errors)):
            print(f"- {error}")
        return 1
    if args.require_pass:
        print(f"Quality acceptance passed: {args.require_pass}")
    else:
        mode_name = "artifacts" if args.artifacts_only else "policy and artifacts"
        print(
            f"Quality validation passed: {mode_name}; "
            f"{len(contracts)} contract(s), {len(runs)} run(s)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

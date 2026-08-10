from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

REQUIRED_SOURCES = (
    "AGENTS.md",
    "PROJECT_MANIFEST.yaml",
    "docs/INDEX.md",
    "docs/PROJECT_CHARTER.md",
    "docs/PRODUCT_SOURCE_OF_TRUTH.md",
    "docs/ARCHITECTURE.md",
    "docs/DOMAIN_MODEL.md",
    "docs/DATA_AND_MEMORY_MODEL.md",
    "docs/AUTONOMY_AND_APPROVALS.md",
    "docs/SECURITY_PRIVACY_THREAT_MODEL.md",
    "docs/INTEGRATION_CONTRACTS.md",
    "docs/MODEL_ROUTING.md",
    "docs/SCHEDULING_ENGINE.md",
    "docs/UX_AND_NOTIFICATION_PRINCIPLES.md",
    "docs/ROADMAP.md",
    "docs/BUILD_STATUS.md",
    "docs/HANDOFF.md",
    "docs/EVIDENCE.md",
    "docs/OPEN_QUESTIONS.md",
    "docs/RISK_REGISTER.md",
    "checklists/FOUNDATION_V0_1.md",
    "checklists/SECURITY_REVIEW.md",
    "checklists/INTEGRATION_READINESS.md",
    "checklists/RELEASE_READINESS.md",
    "spec/capabilities.yaml",
    "spec/permissions.yaml",
    "spec/integrations.yaml",
)

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def load_manifest(root: Path) -> dict[str, Any]:
    payload = yaml.safe_load(
        (root / "PROJECT_MANIFEST.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise TypeError("PROJECT_MANIFEST.yaml must contain a mapping")
    return payload


def declared_targets(manifest: dict[str, Any]) -> list[str]:
    targets: list[str] = []
    for key in (
        "authoritative_sources",
        "specifications",
        "completion_records",
        "quality",
    ):
        values = manifest.get(key, {})
        if isinstance(values, dict):
            targets.extend(str(value) for value in values.values())
    decisions = manifest.get("decisions", {})
    if isinstance(decisions, dict):
        targets.extend(str(value) for value in decisions.values())
    checklists = manifest.get("checklists", {})
    if isinstance(checklists, dict):
        targets.extend(str(value) for value in checklists.values())
    skills = manifest.get("repo_skills", [])
    if isinstance(skills, list):
        targets.extend(str(value) for value in skills)
    return targets


def check_local_links(root: Path) -> list[str]:
    errors: list[str] = []
    for document in (root / "docs").rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            target = match.group(1).strip().strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{document.relative_to(root)}: broken link -> {target}")
    return errors


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_manifest(root)
    except (OSError, TypeError, yaml.YAMLError) as exc:
        return [f"manifest unreadable: {exc}"]

    for target in (*REQUIRED_SOURCES, *declared_targets(manifest)):
        if not (root / target).exists():
            errors.append(f"missing manifest/source target: {target}")

    phase = manifest.get("project", {}).get("phase_label")
    build_status = root / "docs/BUILD_STATUS.md"
    if not isinstance(phase, str) or not phase.strip():
        errors.append("manifest project.phase_label is empty")
    elif phase not in build_status.read_text(encoding="utf-8"):
        errors.append(f"BUILD_STATUS does not identify manifest phase: {phase}")

    handoff = (root / "docs/HANDOFF.md").read_text(encoding="utf-8")
    next_task = re.search(r"## Exact next task\s+(.+?)(?:\n## |\Z)", handoff, re.DOTALL)
    if not next_task or not next_task.group(1).strip():
        errors.append("HANDOFF has no exact next task")

    evidence = (root / "docs/EVIDENCE.md").read_text(encoding="utf-8")
    latest = re.search(
        r"## Latest verification run\s+(.+?)(?:\n## |\Z)", evidence, re.DOTALL
    )
    if not latest or not latest.group(1).strip():
        errors.append("EVIDENCE has no latest verification run")

    decision_dir = root / str(manifest.get("decisions", {}).get("directory", ""))
    if decision_dir.exists() and not any(
        decision_dir.glob("[0-9][0-9][0-9][0-9]-*.md")
    ):
        errors.append("decision directory contains no numbered ADR")

    errors.extend(check_local_links(root))
    return sorted(set(errors))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(root)
    if errors:
        print("Continuity validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Continuity validation passed: manifest, sources, handoff, evidence, ADRs, and links."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

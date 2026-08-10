from __future__ import annotations

import shutil
from pathlib import Path

from scripts.validate_continuity import check_local_links, validate_repository

ROOT = Path(__file__).resolve().parents[3]


def test_current_repository_continuity_is_valid() -> None:
    assert validate_repository(ROOT) == []


def test_broken_local_link_is_detected(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "INDEX.md").write_text("[Missing](DOES_NOT_EXIST.md)", encoding="utf-8")
    assert "broken link" in check_local_links(tmp_path)[0]


def copy_continuity_tree(destination: Path) -> Path:
    destination.mkdir()
    for directory in ("docs", "checklists", "spec", ".agents", "quality"):
        shutil.copytree(ROOT / directory, destination / directory)
    (destination / "scripts").mkdir()
    shutil.copy2(
        ROOT / "scripts" / "validate_quality.py",
        destination / "scripts" / "validate_quality.py",
    )
    for filename in ("AGENTS.md", "PROJECT_MANIFEST.yaml"):
        shutil.copy2(ROOT / filename, destination / filename)
    return destination


def test_missing_manifest_target_is_detected(tmp_path: Path) -> None:
    root = copy_continuity_tree(tmp_path / "missing")
    (root / "docs" / "ARCHITECTURE.md").unlink()
    assert any("ARCHITECTURE.md" in error for error in validate_repository(root))


def test_wrong_build_phase_is_detected(tmp_path: Path) -> None:
    root = copy_continuity_tree(tmp_path / "phase")
    status = root / "docs" / "BUILD_STATUS.md"
    status.write_text(
        status.read_text(encoding="utf-8").replace("Foundation v0.1", "Unknown phase"),
        encoding="utf-8",
    )
    assert any(
        "BUILD_STATUS does not identify manifest phase" in error
        for error in validate_repository(root)
    )


def test_missing_quality_manifest_target_is_detected(tmp_path: Path) -> None:
    root = copy_continuity_tree(tmp_path / "quality")
    (root / "quality" / "README.md").unlink()
    assert any("quality/README.md" in error for error in validate_repository(root))


def test_missing_latest_evidence_is_detected(tmp_path: Path) -> None:
    root = copy_continuity_tree(tmp_path / "evidence")
    evidence = root / "docs" / "EVIDENCE.md"
    evidence.write_text("# Evidence\n\nNo recorded verification.\n", encoding="utf-8")
    assert "EVIDENCE has no latest verification run" in validate_repository(root)

from __future__ import annotations

from pathlib import Path

from scripts.validate_repository_safety import path_error, validate_paths


def test_repository_safety_accepts_sources_examples_and_synthetic_configuration(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env.example").write_text(
        "POSTGRES_PASSWORD=personal_os_local_only\n", encoding="utf-8"
    )
    source = tmp_path / "service.py"
    source.write_text("provider_mode = 'mock'\n", encoding="utf-8")

    assert validate_paths(tmp_path, [".env.example", "service.py"]) == []


def test_repository_safety_rejects_local_runtime_and_credential_paths() -> None:
    for unsafe in (
        ".env",
        ".env.local",
        ".venv/pyvenv.cfg",
        "backend/personal_os.db",
        "node_modules/package/index.js",
        "logs/backend.log",
        ".idea/workspace.xml",
        "credentials.json",
    ):
        assert path_error(unsafe) is not None


def test_repository_safety_detects_high_confidence_secret_without_echoing_value(
    tmp_path: Path,
) -> None:
    secret = "AKIA" + "A" * 16
    candidate = tmp_path / "settings.txt"
    candidate.write_text(f"key={secret}\n", encoding="utf-8")

    errors = validate_paths(tmp_path, ["settings.txt"])

    assert len(errors) == 1
    assert "possible AWS access key" in errors[0]
    assert secret not in errors[0]


def test_repository_safety_ignores_binary_files(tmp_path: Path) -> None:
    (tmp_path / "fixture.bin").write_bytes(b"\x00AKIA" + b"A" * 16)

    assert validate_paths(tmp_path, ["fixture.bin"]) == []

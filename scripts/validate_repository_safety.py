from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class SecretPattern:
    name: str
    pattern: re.Pattern[str]


SECRET_PATTERNS = (
    SecretPattern(
        "private key material", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
    ),
    SecretPattern("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    SecretPattern("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    SecretPattern("OpenAI-style secret key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    SecretPattern("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    SecretPattern(
        "Stripe live key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b")
    ),
    SecretPattern("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
)

PROHIBITED_DIRECTORIES = {
    ".audit-cache",
    ".cache",
    ".hypothesis",
    ".idea",
    ".mypy_cache",
    ".npm",
    ".pnpm-store",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".vscode",
    ".yarn",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "logs",
    "node_modules",
    "outputs",
    "pgdata",
    "playwright-report",
    "postgres-data",
    "temp",
    "test-results",
    "tmp",
    "venv",
    "work",
}

PROHIBITED_SUFFIXES = {
    ".asc",
    ".code-workspace",
    ".db",
    ".gpg",
    ".jks",
    ".key",
    ".keystore",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".pid",
    ".pyc",
    ".pyo",
    ".sock",
    ".sqlite",
    ".sqlite3",
    ".swp",
    ".swo",
}

PROHIBITED_NAMES = {
    ".ds_store",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials.json",
    "desktop.ini",
    "thumbs.db",
}


def repository_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git candidate enumeration failed: {message}")
    return [
        item.decode("utf-8", errors="strict")
        for item in completed.stdout.split(b"\0")
        if item
    ]


def path_error(relative_path: str) -> str | None:
    path = PurePosixPath(relative_path.replace("\\", "/"))
    folded_parts = tuple(part.casefold() for part in path.parts)
    name = path.name.casefold()
    if any(part in PROHIBITED_DIRECTORIES for part in folded_parts):
        return "generated, runtime, dependency, cache, IDE, or temporary path"
    if name == ".env" or (name.startswith(".env.") and not name.endswith(".example")):
        return "local environment file"
    if name in PROHIBITED_NAMES:
        return "credential-prone or machine-specific file"
    if any(name.endswith(suffix) for suffix in PROHIBITED_SUFFIXES):
        return "credential, local database, log, process, cache, or editor artifact"
    return None


def validate_paths(root: Path, relative_paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    resolved_root = root.resolve()
    for relative_path in sorted(set(relative_paths)):
        unsafe_reason = path_error(relative_path)
        if unsafe_reason is not None:
            errors.append(
                f"{relative_path}: prohibited repository path ({unsafe_reason})"
            )
            continue

        candidate = (resolved_root / relative_path).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            errors.append(f"{relative_path}: path escapes repository root")
            continue
        if not candidate.is_file():
            continue
        data = candidate.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="replace")
        for secret in SECRET_PATTERNS:
            match = secret.pattern.search(text)
            if match is None:
                continue
            line = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"{relative_path}:{line}: possible {secret.name}; value intentionally redacted"
            )
    return errors


def validate_repository(root: Path) -> tuple[list[str], int]:
    candidates = repository_files(root)
    return validate_paths(root, candidates), len(candidates)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    try:
        errors, count = validate_repository(root)
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: repository safety validation could not run: {exc}")
        raise SystemExit(1) from exc
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Repository safety validation passed for {count} Git candidate files.")


if __name__ == "__main__":
    main()

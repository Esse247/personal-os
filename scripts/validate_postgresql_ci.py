from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    workflow_path = root / ".github/workflows/postgresql.yml"
    package_path = root / "package.json"
    compose_path = root / "docker-compose.yml"
    if not workflow_path.is_file():
        return ["missing .github/workflows/postgresql.yml"]

    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    package = json.loads(package_path.read_text(encoding="utf-8"))
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
    job = jobs.get("postgresql-verification", {}) if isinstance(jobs, dict) else {}
    services = job.get("services", {}) if isinstance(job, dict) else {}
    postgres = services.get("postgres", {}) if isinstance(services, dict) else {}
    require(
        postgres.get("image") == "postgres:17-alpine",
        "CI must pin postgres:17-alpine",
        errors,
    )
    postgres_environment = postgres.get("env", {}) if isinstance(postgres, dict) else {}
    require(
        postgres_environment.get("POSTGRES_PASSWORD") == "personal_os_local_only",
        "CI PostgreSQL must use the documented synthetic password",
        errors,
    )
    steps = job.get("steps", []) if isinstance(job, dict) else []
    run_text = "\n".join(
        str(step.get("run", "")) for step in steps if isinstance(step, dict)
    )
    require(
        "npm run verify:postgresql" in run_text,
        "CI must execute verify:postgresql",
        errors,
    )
    require(
        "npm run verify" in run_text,
        "CI must execute the Foundation regression",
        errors,
    )
    environment = job.get("env", {}) if isinstance(job, dict) else {}
    test_url = str(environment.get("PERSONAL_OS_POSTGRES_TEST_URL", ""))
    upgrade_url = str(environment.get("PERSONAL_OS_POSTGRES_UPGRADE_URL", ""))
    admin_url = str(environment.get("PERSONAL_OS_POSTGRES_ADMIN_URL", ""))
    require(
        "postgresql+psycopg://personal_os:personal_os_local_only@127.0.0.1:5432/personal_os_verify"
        == test_url,
        "CI test URL must target the local disposable personal_os_verify database",
        errors,
    )
    require(
        "postgresql+psycopg://personal_os:personal_os_local_only@127.0.0.1:5432/personal_os_upgrade_verify"
        == upgrade_url,
        "CI upgrade URL must target the local disposable personal_os_upgrade_verify database",
        errors,
    )
    require(
        admin_url.endswith("/postgres"), "CI admin URL must target postgres", errors
    )
    require(
        "${{ secrets" not in test_url + upgrade_url + admin_url,
        "CI must not require real secrets",
        errors,
    )

    scripts: dict[str, Any] = package.get("scripts", {})
    for name in (
        "verify:postgresql",
        "test:postgresql",
        "test:dialect-boundaries",
        "validate:postgresql-ci",
    ):
        require(name in scripts, f"package.json is missing script {name}", errors)
    require(
        "scripts/verify_postgresql.py" in str(scripts.get("verify:postgresql", "")),
        "verify:postgresql must use the clean bootstrap verifier",
        errors,
    )
    backend_environment = compose["services"]["backend"]["environment"]
    require(
        backend_environment.get("PERSONAL_OS_AUTO_INITIALIZE") == "false",
        "Compose PostgreSQL runtime must disable create_all auto-initialize",
        errors,
    )
    return errors


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("PostgreSQL CI contract validation passed.")


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

import yaml

from personal_os.capabilities import CAPABILITIES

ROOT = Path(__file__).resolve().parents[3]


def test_compose_defines_local_postgres_api_and_dashboard_without_live_mode() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert set(services) == {"postgres", "backend", "frontend"}
    assert services["postgres"]["ports"] == ["127.0.0.1:5432:5432"]
    assert services["backend"]["ports"] == ["127.0.0.1:8000:8000"]
    assert services["frontend"]["ports"] == ["127.0.0.1:4173:8080"]
    assert services["backend"]["environment"]["PERSONAL_OS_PROVIDER_MODE"] == "mock"
    assert services["backend"]["environment"]["PERSONAL_OS_AUTO_INITIALIZE"] == "false"
    assert "postgresql+psycopg" in services["backend"]["environment"]["PERSONAL_OS_DATABASE_URL"]


def test_runtime_capabilities_match_machine_readable_source_of_truth() -> None:
    specification = yaml.safe_load(
        (ROOT / "spec" / "capabilities.yaml").read_text(encoding="utf-8")
    )
    expected = {
        name: {"status": value["status"], "mode": value["mode"]}
        for name, value in specification["capabilities"].items()
    }
    assert expected == CAPABILITIES

from __future__ import annotations

import ast
from pathlib import Path

from personal_os.ports import providers, repositories

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "personal_os"
FORBIDDEN_CORE_IMPORTS = (
    "fastapi",
    "sqlalchemy",
    "personal_os.adapters",
    "personal_os.interfaces",
)


def imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_domain_and_application_dependencies_point_inward() -> None:
    violations: list[str] = []
    for layer in ("domain", "application"):
        for path in (PACKAGE_ROOT / layer).glob("*.py"):
            for imported in imports_for(path):
                if imported.startswith(FORBIDDEN_CORE_IMPORTS):
                    violations.append(f"{path.name}: {imported}")
    assert violations == []


def test_required_provider_and_repository_ports_exist() -> None:
    expected = {
        "ModelProvider",
        "CalendarProvider",
        "NotificationProvider",
        "EmailProvider",
        "BankingProvider",
        "WearableProvider",
        "LocationProvider",
        "VoiceProvider",
        "SearchProvider",
        "FileStorageProvider",
        "ToolProvider",
    }
    assert expected <= set(vars(providers))
    assert "UnitOfWork" in vars(repositories)
    assert "update" not in vars(repositories.AuditRepository)
    assert "delete" not in vars(repositories.AuditRepository)


def test_no_vendor_name_or_network_client_leaks_into_core() -> None:
    forbidden_terms = ("openai", "anthropic", "deepseek", "requests.", "httpx.")
    violations: list[str] = []
    for layer in ("domain", "application", "ports"):
        for path in (PACKAGE_ROOT / layer).glob("*.py"):
            lowered = path.read_text(encoding="utf-8").casefold()
            if any(term in lowered for term in forbidden_terms):
                violations.append(str(path))
    assert violations == []


def test_mock_adapters_have_no_network_client_or_live_fallback() -> None:
    mock_source = (PACKAGE_ROOT / "adapters" / "providers" / "mock.py").read_text(encoding="utf-8")
    forbidden_imports = ("import requests", "import httpx", "import urllib", "import socket")
    assert not any(term in mock_source for term in forbidden_imports)

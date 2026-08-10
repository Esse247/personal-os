from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.engine import make_url

from personal_os.domain.errors import ProhibitedCapabilityError

DEMO_USER_ID = "user-alex-synthetic"
OTHER_USER_ID = "user-riley-synthetic"
DEMO_HOUSEHOLD_ID = "household-lantern-synthetic"


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    provider_mode: str = "mock"
    database_url: str = "sqlite:///./backend/personal_os.db"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    development_user_id: str = DEMO_USER_ID
    auto_initialize: bool = True

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            environment=os.getenv("PERSONAL_OS_ENV", "development"),
            provider_mode=os.getenv("PERSONAL_OS_PROVIDER_MODE", "mock"),
            database_url=os.getenv(
                "PERSONAL_OS_DATABASE_URL", "sqlite:///./backend/personal_os.db"
            ),
            bind_host=os.getenv("PERSONAL_OS_BIND_HOST", "127.0.0.1"),
            bind_port=int(os.getenv("PERSONAL_OS_BIND_PORT", "8000")),
        )

    def validate_foundation_mode(self) -> None:
        if self.environment not in {"development", "test", "local"}:
            raise ProhibitedCapabilityError(
                "Foundation v0.1 permits only development, test, or local environments"
            )
        if self.provider_mode != "mock":
            raise ProhibitedCapabilityError("Foundation v0.1 permits only mock providers")
        if self.bind_host not in {"127.0.0.1", "localhost", "testserver"}:
            raise ProhibitedCapabilityError("Foundation v0.1 must bind to localhost")
        credential_variables = (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLIENT_SECRET",
            "MICROSOFT_CLIENT_SECRET",
            "PLAID_CLIENT_ID",
            "PLAID_SECRET",
            "STRIPE_SECRET_KEY",
            "SENDGRID_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "PERSONAL_OS_POSTGRES_PASSWORD",
        )
        if any(os.getenv(name) for name in credential_variables):
            raise ProhibitedCapabilityError(
                "Foundation v0.1 refuses credential-bearing provider configuration"
            )
        try:
            database = make_url(self.database_url)
        except Exception as exc:
            raise ProhibitedCapabilityError("database URL is invalid") from exc
        if database.get_backend_name() == "sqlite":
            if database.host not in {None, "", "localhost"}:
                raise ProhibitedCapabilityError("Foundation SQLite must be local")
            return
        if database.get_backend_name() != "postgresql" or database.host not in {
            "127.0.0.1",
            "localhost",
            "postgres",
        }:
            raise ProhibitedCapabilityError("Foundation database must be local SQLite/PostgreSQL")
        if database.username != "personal_os" or database.password not in {
            None,
            "personal_os_local_only",
        }:
            raise ProhibitedCapabilityError(
                "Foundation PostgreSQL accepts only the documented synthetic local account"
            )

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from scripts.verify_postgresql import EXPECTED_DATABASE, validated_url
from sqlalchemy import Engine, text

from personal_os.adapters.persistence.database import create_database_engine


def _postgresql_url() -> str:
    raw = os.getenv("PERSONAL_OS_DATABASE_URL") or os.getenv("PERSONAL_OS_POSTGRES_TEST_URL")
    if not raw:
        pytest.exit(
            "real PostgreSQL URL is required; SQLite substitution is prohibited",
            returncode=2,
        )
    return validated_url(raw, expected_database=EXPECTED_DATABASE).render_as_string(
        hide_password=False
    )


@pytest.fixture(scope="session")
def postgresql_engine() -> Iterator[Engine]:
    engine = create_database_engine(_postgresql_url())
    if engine.dialect.name != "postgresql":
        pytest.exit("PostgreSQL acceptance tests require PostgreSQL", returncode=2)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_database()")).scalar_one() == (
            EXPECTED_DATABASE
        )
    yield engine
    engine.dispose()

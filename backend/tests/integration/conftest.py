from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from personal_os.adapters.persistence.database import create_database_engine
from personal_os.config import Settings
from personal_os.interfaces.http.app import create_app


@pytest.fixture
def engine() -> Engine:
    return create_database_engine("sqlite+pysqlite:///:memory:")


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    app = create_app(Settings(database_url="sqlite+pysqlite:///:memory:"), engine=engine)
    with TestClient(app) as value:
        yield value

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from personal_os.adapters.persistence.models import Base

POSTGRESQL_SCHEMA_HEAD = "0008_operator_receipts"


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    kwargs: dict[str, object] = {"echo": echo}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    elif database_url.startswith("postgresql"):
        kwargs["connect_args"] = {"options": "-c timezone=UTC"}
        kwargs["pool_pre_ping"] = True
    return create_engine(database_url, **kwargs)


def initialize_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        raise RuntimeError("PostgreSQL schema bootstrap requires Alembic migrations")
    Base.metadata.create_all(engine)


def assert_postgresql_schema_current(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        return
    try:
        with engine.connect() as connection:
            actual = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    except SQLAlchemyError as exc:
        raise RuntimeError("PostgreSQL schema is unavailable or not migrated") from exc
    if actual != POSTGRESQL_SCHEMA_HEAD:
        raise RuntimeError(f"PostgreSQL schema is at {actual}, expected {POSTGRESQL_SCHEMA_HEAD}")

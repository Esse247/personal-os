from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from personal_os.adapters.persistence.models import Base


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    kwargs: dict[str, object] = {"echo": echo}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def initialize_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)

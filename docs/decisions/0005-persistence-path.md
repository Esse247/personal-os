# ADR 0005: Local SQLite with PostgreSQL target

- **Status:** Accepted for Foundation v0.1
- **Date:** 2026-08-10

## Decision

Use SQLite as the default zero-service local demonstration database through SQLAlchemy, with portable Alembic migrations and a PostgreSQL service in Docker Compose. Treat PostgreSQL as the durable deployment target; do not claim it is verified until its migration/integration commands run successfully.

## Consequences

Contributors can run the demo without Docker. SQLite concurrency, constraint, and timezone differences are a known limitation and block production use. PostgreSQL-specific integration evidence is required before a pilot.

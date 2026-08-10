# ADR 0002: Technology and repository stack

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

Use a monorepo with React + strict TypeScript + Vite for the responsive web client; Python 3.12 + FastAPI + Pydantic for HTTP contracts; SQLAlchemy + Alembic for persistence/migrations; pytest, Ruff, a Python type checker, ESLint, TypeScript, Vitest, and build/demo scripts for verification. Docker Compose documents a PostgreSQL reproducibility path.

## Rationale

The stack is broadly supported, cross-platform, testable, provider-neutral, and appropriately boring. FastAPI’s OpenAPI output is the HTTP contract source; a generated frontend client is deferred until the API stabilizes.

## Consequences

Both language ecosystems must be installed and locked. Framework types remain outside domain code. Docker availability is optional for the zero-service demo but required before PostgreSQL-specific release claims.

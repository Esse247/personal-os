# ADR 0003: Inward dependency boundaries

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

Dependencies point from interfaces/adapters/platform toward application, ports, and domain. Domain imports only the standard library and shared value types. Application may depend on domain and abstract ports, never FastAPI, SQLAlchemy, concrete adapters, or provider SDKs.

Cross-module references are opaque typed IDs. There are no generic repositories, generic status patches, or provider-native values in core code.

## Consequences

Static architecture tests enforce imports. Some mapping code is intentional. Models/providers can propose typed data but cannot access repositories or issue commands.

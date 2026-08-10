# ADR 0010: Local development identity only

- **Status:** Accepted for Foundation v0.1
- **Date:** 2026-08-10

## Decision

Use one server-derived synthetic development principal for the localhost demonstration. Do not trust user/role/household identifiers supplied by the client. Bind to `127.0.0.1` and label the identity mode visibly.

## Consequences

This is not authentication and cannot support deployment, remote access, or real data. Production identity, session, recovery, CSRF, and reauthentication design are required before any non-local environment.

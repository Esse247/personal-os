# ADR 0001: Modular monolith

- **Status:** Accepted
- **Date:** 2026-08-10

## Context

The final vision spans many domains, but Foundation v0.1 needs strong boundaries and a small operable system, not distributed operations.

## Decision

Use one deployable backend modular monolith, one web frontend, and one relational database. API and worker are separate entry points over shared domain/application modules. Modules own their state and expose typed commands, queries, events, and ports.

## Consequences

Transactions and local setup stay simple; boundaries remain testable. No microservices, broker, Redis, Kubernetes, or independent module deployment is introduced. A future split requires measured operational or ownership pressure and a superseding ADR.

from __future__ import annotations


class DomainError(Exception):
    """Base error with a stable machine-readable code."""

    code = "domain_error"


class ValidationError(DomainError):
    code = "validation_error"


class InvalidTransitionError(DomainError):
    code = "invalid_transition"


class AuthorizationError(DomainError):
    code = "not_found"


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class ProhibitedCapabilityError(DomainError):
    code = "prohibited_capability"

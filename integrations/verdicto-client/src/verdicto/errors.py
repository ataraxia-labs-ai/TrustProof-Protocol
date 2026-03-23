"""Typed exceptions for the Verdicto API client."""

from __future__ import annotations


class VerdictoError(Exception):
    """Base exception for all Verdicto API errors."""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN",
        status_code: int = 0,
        request_id: str | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(f"[{code}] {message}")


class AuthenticationError(VerdictoError):
    """Invalid or missing API key (401)."""


class RateLimitError(VerdictoError):
    """Rate limit exceeded (429). Check retry_after_sec."""

    def __init__(self, message: str, retry_after_sec: float = 0, **kwargs) -> None:
        self.retry_after_sec = retry_after_sec
        super().__init__(message, code="RATE_LIMITED", **kwargs)


class ReplayDetectedError(VerdictoError):
    """Agent pass replay detected (409)."""


class IdempotencyConflictError(VerdictoError):
    """Same idempotency key with different body (409)."""


class ValidationError(VerdictoError):
    """Request validation failed (400/422)."""


class NotFoundError(VerdictoError):
    """Resource not found (404)."""


class ServerError(VerdictoError):
    """Verdicto server error (5xx)."""

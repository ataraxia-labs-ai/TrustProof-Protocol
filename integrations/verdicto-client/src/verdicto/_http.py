"""Shared HTTP logic for sync and async Verdicto clients."""

from __future__ import annotations

import uuid
from typing import Any

from .errors import (
    AuthenticationError,
    IdempotencyConflictError,
    NotFoundError,
    RateLimitError,
    ReplayDetectedError,
    ServerError,
    ValidationError,
    VerdictoError,
)

VERSION = "0.1.0"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 2
USER_AGENT = f"verdicto-python/{VERSION}"


def build_headers(
    api_key: str,
    idempotency_key: str | None = None,
) -> dict[str, str]:
    """Build request headers."""
    headers: dict[str, str] = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def new_idempotency_key() -> str:
    """Generate a new idempotency key."""
    return str(uuid.uuid4())


def _extract_error_info(body: Any) -> tuple[str, str, str | None]:
    """Extract (code, message, request_id) from an error response body."""
    if not isinstance(body, dict):
        return "UNKNOWN", str(body), None

    request_id = body.get("request_id")

    # {error: {code, message}}
    err = body.get("error")
    if isinstance(err, dict):
        return (
            err.get("code", "UNKNOWN"),
            err.get("message", "Unknown error"),
            err.get("request_id", request_id),
        )

    # {detail: {code, message}}
    detail = body.get("detail")
    if isinstance(detail, dict):
        return (
            detail.get("code", "UNKNOWN"),
            detail.get("message", "Unknown error"),
            detail.get("request_id", request_id),
        )

    # {code, message} at top level
    code = body.get("code", "UNKNOWN")
    message = body.get("message") or body.get("detail") or "Unknown error"
    return code, str(message), request_id


def map_error(status_code: int, body: Any) -> VerdictoError:
    """Map an HTTP error response to a typed exception."""
    code, message, request_id = _extract_error_info(body)

    if status_code == 401:
        return AuthenticationError(
            message, code=code, status_code=401, request_id=request_id
        )

    if status_code == 404:
        return NotFoundError(
            message, code=code, status_code=404, request_id=request_id
        )

    if status_code == 409:
        if "replay" in code.lower() or "replay" in message.lower():
            return ReplayDetectedError(
                message, code=code, status_code=409, request_id=request_id
            )
        return IdempotencyConflictError(
            message, code=code, status_code=409, request_id=request_id
        )

    if status_code == 429:
        retry_after = 0.0
        if isinstance(body, dict):
            retry_after = float(
                body.get("retry_after_sec", 0)
                or (body.get("detail", {}) or {}).get("retry_after_sec", 0)
            )
        return RateLimitError(
            message, retry_after_sec=retry_after, status_code=429, request_id=request_id
        )

    if status_code in (400, 422):
        return ValidationError(
            message, code=code, status_code=status_code, request_id=request_id
        )

    if status_code >= 500:
        return ServerError(
            message, code=code, status_code=status_code, request_id=request_id
        )

    return VerdictoError(
        message, code=code, status_code=status_code, request_id=request_id
    )


def should_retry(status_code: int) -> bool:
    """Whether this status code is retryable."""
    return status_code in (429, 503)


def retry_delay(status_code: int, body: Any, attempt: int) -> float:
    """Compute retry delay in seconds."""
    if status_code == 429 and isinstance(body, dict):
        retry_after = body.get("retry_after_sec") or (
            (body.get("detail") or {}).get("retry_after_sec")
        )
        if retry_after:
            return float(retry_after)
    return min(2 ** attempt, 8)

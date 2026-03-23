"""Verdicto — Python client for the Verdicto trust infrastructure API."""

from verdicto.async_client import AsyncVerdictoClient
from verdicto.client import VerdictoClient
from verdicto.errors import (
    AuthenticationError,
    IdempotencyConflictError,
    NotFoundError,
    RateLimitError,
    ReplayDetectedError,
    ServerError,
    ValidationError,
    VerdictoError,
)
from verdicto.types import (
    AgentPass,
    Case,
    CasesList,
    ProofVerifyResult,
    RotateKeyResult,
    StepUpSession,
    VerifyResult,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "VerdictoClient",
    "AsyncVerdictoClient",
    "AgentPass",
    "VerifyResult",
    "ProofVerifyResult",
    "Case",
    "CasesList",
    "StepUpSession",
    "RotateKeyResult",
    "VerdictoError",
    "AuthenticationError",
    "RateLimitError",
    "ReplayDetectedError",
    "IdempotencyConflictError",
    "ValidationError",
    "NotFoundError",
    "ServerError",
]

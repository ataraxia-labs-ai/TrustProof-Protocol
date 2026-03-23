"""Response and request types for the Verdicto API client.

All types use frozen dataclasses for immutability and match the actual
API response shapes from apps/api/app/main.py and route handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class AgentPass:
    """Issued agent pass from POST /v1/agent/pass/issue."""

    agent_pass: str
    request_id: str = ""


@dataclass(frozen=True)
class VerifyResult:
    """Result from POST /v1/verify/agent."""

    ok: bool
    tenant_id: str
    decision: Literal["allow", "deny", "step_up"]
    confidence: float
    reason_codes: list[str]
    policy_v: str
    request_id: str
    verification_id: str
    proof_jwt: str | None = None
    step_up_url: str | None = None
    step_up_expires_at: str | None = None


@dataclass(frozen=True)
class ProofVerifyResult:
    """Result from POST /v1/proofs/verify."""

    ok: bool
    verification_id: str | None = None
    decision: str | None = None
    reason_codes: list[str] = field(default_factory=list)
    issued_at: str | None = None
    request_id: str = ""


@dataclass(frozen=True)
class Case:
    """A verification case summary from GET /v1/cases."""

    id: str
    decision: str | None = None
    confidence: float | None = None
    reason_codes: list[str] = field(default_factory=list)
    created_at: str | None = None
    subject_id: str | None = None
    requested_action: str | None = None
    amount_cents: int | None = None
    currency: str | None = None
    merchant_id: str | None = None
    proof_jwt: str | None = None
    request_id: str | None = None
    policy_v: str | None = None


@dataclass(frozen=True)
class CasesList:
    """Paginated list from GET /v1/cases."""

    ok: bool
    tenant_id: str
    cases: list[Case]
    limit: int
    offset: int


@dataclass(frozen=True)
class StepUpSession:
    """Step-up session from POST /v1/step-up/{token}/approve or /deny."""

    ok: bool
    status: str
    verification_id: str
    proof_jwt: str | None = None
    decision: str | None = None


@dataclass(frozen=True)
class RotateKeyResult:
    """Result from POST /v1/keys/rotate."""

    ok: bool
    tenant_id: str
    key: str
    key_prefix: str
    name: str
    deactivated_previous: bool
    created_at: str = ""
    request_id: str = ""

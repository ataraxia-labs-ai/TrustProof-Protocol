"""Type definitions for the TrustProof protocol (v0.2).

All types use TypedDict so they remain compatible with the dict-based
generate/verify/chain API while providing static type checking.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class Subject(TypedDict):
    """Entity performing the action."""

    type: Literal["human", "agent"]
    id: str


class Resource(TypedDict):
    """Target of the action."""

    type: str
    id: str


class PolicyConstraints(TypedDict, total=False):
    """Constraints on the policy."""

    max_amount_cents: int
    currency_allowlist: list[str]
    merchant_allowlist: list[str]


class Policy(TypedDict):
    """Policy snapshot at decision time."""

    policy_v: str
    scopes: list[str]
    constraints: PolicyConstraints


class Result(TypedDict):
    """Decision outcome."""

    decision: Literal["allow", "deny", "step_up"]
    reason_codes: list[str]


class Hashes(TypedDict):
    """Cryptographic hashes of canonical input/output."""

    input_hash: str
    output_hash: str


class Chain(TypedDict):
    """Tamper-evident chain linkage."""

    prev_hash: str
    entry_hash: str


class ProtocolRefs(TypedDict, total=False):
    """Cross-protocol references (v0.2).

    Links a TrustProof to artifacts in external trust/commerce protocols.
    """

    verifiable_intent_id: str
    ap2_mandate_id: str
    ap2_mandate_type: Literal["intent", "cart", "payment"]
    a2a_task_id: str
    acp_checkout_id: str
    x402_payment_hash: str
    mcp_tool_call_id: str
    upstream_proof: str


class VCProfile(TypedDict, total=False):
    """W3C Verifiable Credential profile (v0.2).

    Maps TrustProof claims to the VC Data Model 2.0.
    """

    vc_version: str
    credential_type: list[str]
    issuer_did: str
    subject_did: str
    delegation_did: str


class TrustProofClaims(TypedDict, total=False):
    """Complete TrustProof claims envelope.

    Required fields: subject, action, resource, policy, result, hashes,
    timestamp, jti, chain.  Optional v0.2 fields: protocol_refs, vc_profile.
    """

    # Required (v0.1)
    subject: Subject
    action: str
    resource: Resource
    policy: Policy
    result: Result
    hashes: Hashes
    timestamp: str
    jti: str
    chain: Chain

    # Optional (v0.2)
    protocol_refs: ProtocolRefs
    vc_profile: VCProfile


class ErrorInfo(TypedDict, total=False):
    """Structured error from verify/verify_chain."""

    code: str
    message: str
    details: Any
    index: int


class VerifyResult(TypedDict):
    """Result from verify()."""

    ok: bool
    errors: list[ErrorInfo]
    claims: dict[str, Any]


class ChainResult(TypedDict):
    """Result from verify_chain()."""

    ok: bool
    errors: list[ErrorInfo]

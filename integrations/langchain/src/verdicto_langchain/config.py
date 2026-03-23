"""Configuration types for verdicto-langchain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


@dataclass
class VerdictoConfig:
    """Configuration for the VerdictoCallbackHandler.

    All fields have sensible defaults. For local/dev, no arguments are needed —
    a keypair is auto-generated. For production, provide your own private_key.
    """

    agent_id: str = "langchain-agent"
    """Subject ID for proofs (identifies the agent)."""

    private_key: Ed25519PrivateKey | None = None
    """Ed25519 private key for signing. Auto-generated if None."""

    public_key: Ed25519PublicKey | None = None
    """Ed25519 public key for verification. Derived from private_key if None."""

    policy_scopes: list[str] = field(default_factory=lambda: ["langchain.tool_call"])
    """Default policy scopes for generated proofs."""

    trace_llm_calls: bool = False
    """Generate proofs for LLM calls (verbose — off by default)."""

    trace_chain_steps: bool = True
    """Generate proofs for chain-level steps."""

    protocol_refs: dict[str, Any] | None = None
    """v0.2 cross-protocol references to include in all proofs."""

    vc_profile: dict[str, Any] | None = None
    """v0.2 W3C VC profile to include in all proofs."""

    # ── Verdicto API connection (optional — enables dashboard visibility) ──

    verdicto_api_url: str | None = None
    """Verdicto API URL (e.g. 'http://127.0.0.1:8000'). Enables API mode."""

    verdicto_api_key: str | None = None
    """Verdicto API key (e.g. 'vk_...'). Required when api_url is set."""

    agent_pass_scopes: list[str] = field(
        default_factory=lambda: ["langchain.tool_call", "langchain.chain_step"]
    )
    """Scopes for the auto-issued Agent Pass."""

    agent_pass_ttl_seconds: int = 900
    """TTL for the auto-issued Agent Pass."""

    agent_pass_max_amount_cents: int | None = None
    """Max amount constraint for the Agent Pass."""

    agent_pass_currency_allowlist: list[str] = field(default_factory=lambda: ["USD"])
    """Currency allowlist for the Agent Pass."""

    agent_pass_merchant_allowlist: list[str] = field(default_factory=list)
    """Merchant allowlist for the Agent Pass."""

    api_send_async: bool = True
    """Send API verifications in background threads (non-blocking)."""

    api_fail_silently: bool = True
    """If API call fails, log warning but don't crash the agent."""

    @property
    def api_enabled(self) -> bool:
        """True if both API URL and key are configured."""
        return bool(self.verdicto_api_url and self.verdicto_api_key)


def ensure_keypair(config: VerdictoConfig) -> tuple[str, str]:
    """Return (private_pem, public_pem), generating if needed."""
    if config.private_key is None:
        config.private_key = Ed25519PrivateKey.generate()

    if config.public_key is None:
        config.public_key = config.private_key.public_key()

    private_pem = config.private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    public_pem = config.public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return private_pem, public_pem

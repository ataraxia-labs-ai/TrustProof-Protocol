"""Configuration for verdicto-autoresearch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


@dataclass
class AutoresearchConfig:
    """Configuration for TrustProof generation in experiment loops."""

    researcher_id: str = "autoresearch-agent"
    """Who/what is running experiments."""

    principal_id: str | None = None
    """Human who authorized the research (KYH binding)."""

    session_id: str | None = None
    """Research session identifier."""

    approved_scopes: list[str] = field(default_factory=lambda: [
        "autoresearch.experiment",
        "autoresearch.code_modification",
        "autoresearch.evaluation",
    ])

    max_experiments: int | None = None
    """Max experiments before requiring re-authorization."""

    allowed_file_modifications: list[str] = field(default_factory=lambda: ["train.py"])

    forbidden_patterns: list[str] = field(default_factory=list)

    metric_name: str = "val_bpb"
    metric_direction: str = "lower"

    private_key: Ed25519PrivateKey | None = None
    public_key: Ed25519PublicKey | None = None

    track_git: bool = True
    repo_path: str | None = None

    verdicto_api_url: str | None = None
    verdicto_api_key: str | None = None

    @property
    def api_enabled(self) -> bool:
        return bool(self.verdicto_api_url and self.verdicto_api_key)

    def get_policy_snapshot(self) -> dict[str, Any]:
        """Build policy dict for proof claims."""
        constraints: dict[str, Any] = {}
        if self.max_experiments is not None:
            constraints["max_experiments"] = self.max_experiments
        return {
            "policy_v": "v0",
            "scopes": self.approved_scopes,
            "constraints": constraints,
        }


def ensure_keypair(config: AutoresearchConfig) -> tuple[str, str]:
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

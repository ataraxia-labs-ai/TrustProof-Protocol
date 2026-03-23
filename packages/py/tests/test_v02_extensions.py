from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trustproof import generate, verify  # noqa: E402


def _load_allow_claims() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    allow_path = repo_root / "spec" / "examples" / "allow.json"
    return json.loads(allow_path.read_text(encoding="utf-8"))


def _generate_pem_keypair() -> tuple[str, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def test_v02_extensions_round_trip() -> None:
    """Generate and verify a JWT with v0.2 envelope extensions (protocol_refs, vc_profile).

    Ensures that arbitrary extra fields survive the generate -> verify round-trip
    and are present in the decoded claims.
    """
    claims = _load_allow_claims()

    # Add v0.2 envelope extension fields matching the v006 vector structure
    claims["protocol_refs"] = {
        "ap2_mandate_id": "mandate_cart_abc123",
        "ap2_mandate_type": "cart",
        "verifiable_intent_id": "vi_mc_def456",
        "mcp_tool_call_id": "mcp_call_789",
    }
    claims["vc_profile"] = {
        "vc_version": "2.0",
        "credential_type": ["VerifiableCredential", "TrustProofCredential"],
        "issuer_did": "did:web:verdicto.dev",
        "subject_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
        "delegation_did": "did:key:z6MkpTHR8VNs5zAqPSCsa7HRaGKm3FCbgfPYRzFbNhBsqd2H",
    }

    private_pem, public_pem = _generate_pem_keypair()

    token = generate(claims, private_pem)
    result = verify(token, public_pem)

    assert result["ok"] is True
    assert result["errors"] == []

    decoded_claims = result["claims"]
    assert isinstance(decoded_claims, dict)

    # Verify all 9 required fields are present
    for field in (
        "subject", "action", "resource", "policy",
        "result", "hashes", "timestamp", "jti", "chain",
    ):
        assert field in decoded_claims, f"Missing required field: {field}"

    # Verify v0.2 extension fields survived the round-trip
    assert "protocol_refs" in decoded_claims
    assert decoded_claims["protocol_refs"]["ap2_mandate_id"] == "mandate_cart_abc123"
    assert decoded_claims["protocol_refs"]["ap2_mandate_type"] == "cart"
    assert decoded_claims["protocol_refs"]["verifiable_intent_id"] == "vi_mc_def456"
    assert decoded_claims["protocol_refs"]["mcp_tool_call_id"] == "mcp_call_789"

    assert "vc_profile" in decoded_claims
    assert decoded_claims["vc_profile"]["vc_version"] == "2.0"
    assert decoded_claims["vc_profile"]["credential_type"] == [
        "VerifiableCredential",
        "TrustProofCredential",
    ]
    assert decoded_claims["vc_profile"]["issuer_did"] == "did:web:verdicto.dev"
    assert decoded_claims["vc_profile"]["subject_did"] == (
        "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
    )
    assert decoded_claims["vc_profile"]["delegation_did"] == (
        "did:key:z6MkpTHR8VNs5zAqPSCsa7HRaGKm3FCbgfPYRzFbNhBsqd2H"
    )

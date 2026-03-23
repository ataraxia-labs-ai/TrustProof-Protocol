"""Tests for Proof Mesh — multi-issuer chain verification.

All tests use real Ed25519 crypto. No mocks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trustproof import append, generate
from trustproof.mesh import (
    Issuer,
    IssuerRegistry,
    IssuerTrust,
    MeshVerifier,
)


def _make_keypair() -> tuple[str, str]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def _base_claims(action: str = "test.action", jti: str = "test") -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    allow_path = repo_root / "spec" / "examples" / "allow.json"
    claims = json.loads(allow_path.read_text())
    claims["action"] = action
    claims["jti"] = jti
    return claims


# ── Registry Tests ──────────────────────────────────────────────────


def test_issuer_registry_register_and_get() -> None:
    _, pub = _make_keypair()
    registry = IssuerRegistry()
    issuer = Issuer(issuer_id="test:issuer", public_key_pem=pub, display_name="Test")
    registry.register(issuer)

    found = registry.get("test:issuer")
    assert found is not None
    assert found.issuer_id == "test:issuer"
    assert found.public_key_pem == pub


def test_issuer_registry_get_missing() -> None:
    registry = IssuerRegistry()
    assert registry.get("nonexistent") is None


def test_issuer_registry_resolve_from_jwt() -> None:
    priv, pub = _make_keypair()
    registry = IssuerRegistry()
    registry.register(Issuer("alpha", pub, "Alpha"))

    claims = _base_claims(jti="resolve_test")
    proof = append(None, claims, priv, kid="alpha")

    issuer_id, issuer = registry.resolve_from_jwt(proof)
    assert issuer_id == "alpha"
    assert issuer is not None
    assert issuer.display_name == "Alpha"


# ── Single Issuer Chain ────────────────────────────────────────────


def test_single_issuer_chain() -> None:
    priv, pub = _make_keypair()
    registry = IssuerRegistry()
    registry.register(Issuer("alpha", pub, "Alpha", IssuerTrust.VERIFIED))

    p1 = append(None, _base_claims(action="step1", jti="j1"), priv, kid="alpha")
    p2 = append(p1, _base_claims(action="step2", jti="j2"), priv, kid="alpha")
    p3 = append(p2, _base_claims(action="step3", jti="j3"), priv, kid="alpha")

    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([p1, p2, p3])

    assert result.valid is True
    assert result.chain_length == 3
    assert result.issuers_involved == ["alpha"]
    assert result.cross_platform_hops == 0
    assert result.trust_summary["alpha"] == "verified"
    assert len(result.errors) == 0


# ── Multi Issuer Chain (CORE TEST) ─────────────────────────────────


def test_multi_issuer_chain() -> None:
    priv_a, pub_a = _make_keypair()
    priv_b, pub_b = _make_keypair()

    registry = IssuerRegistry()
    registry.register(Issuer("alpha", pub_a, "Alpha Corp", IssuerTrust.VERIFIED))
    registry.register(Issuer("beta", pub_b, "Beta Agent", IssuerTrust.SELF_DECLARED))

    # Issuer Alpha signs proof 1
    p1 = append(None, _base_claims(action="delegate", jti="m1"), priv_a, kid="alpha")
    # Issuer Alpha signs proof 2 (chain linked to p1)
    p2 = append(p1, _base_claims(action="search", jti="m2"), priv_a, kid="alpha")
    # Issuer Beta signs proof 3 (chain linked to p2 — CROSS-ISSUER!)
    p3 = append(p2, _base_claims(action="compare", jti="m3"), priv_b, kid="beta")
    # Issuer Alpha signs proof 4 (chain linked to p3 — back to Alpha)
    p4 = append(p3, _base_claims(action="complete", jti="m4"), priv_a, kid="alpha")

    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([p1, p2, p3, p4])

    assert result.valid is True
    assert result.chain_length == 4
    assert sorted(result.issuers_involved) == ["alpha", "beta"]
    assert result.cross_platform_hops == 2  # alpha→beta, beta→alpha
    assert result.trust_summary["alpha"] == "verified"
    assert result.trust_summary["beta"] == "self_declared"
    assert len(result.errors) == 0


# ── Unknown Issuer ──────────────────────────────────────────────────


def test_unknown_issuer_warns() -> None:
    priv, pub = _make_keypair()
    registry = IssuerRegistry()
    # Intentionally NOT registering the issuer

    p1 = append(None, _base_claims(jti="u1"), priv, kid="unknown_issuer")

    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([p1])

    # Unknown issuer: can't verify signature → not valid
    assert result.valid is False
    assert "unknown_issuer" in result.issuers_involved
    assert any("unknown_issuer" in w for w in result.warnings) or any("unknown_issuer" in e for e in result.errors)


# ── Cross Reference Tracking ───────────────────────────────────────


def test_cross_reference_upstream_proof() -> None:
    priv, pub = _make_keypair()
    registry = IssuerRegistry()
    registry.register(Issuer("alpha", pub, "Alpha"))

    claims = _base_claims(jti="xref1")
    claims["protocol_refs"] = {"upstream_proof": "abc123def456" * 5 + "abcd"}
    p1 = append(None, claims, priv, kid="alpha")

    verifier = MeshVerifier(registry)
    link = verifier.verify_single(p1)

    assert link.signature_valid is True
    assert len(link.cross_refs) == 1


# ── Tamper Detection in Mesh ───────────────────────────────────────


def test_tamper_detection_in_mesh() -> None:
    priv_a, pub_a = _make_keypair()
    priv_b, pub_b = _make_keypair()

    registry = IssuerRegistry()
    registry.register(Issuer("alpha", pub_a, "Alpha"))
    registry.register(Issuer("beta", pub_b, "Beta"))

    p1 = append(None, _base_claims(jti="t1"), priv_a, kid="alpha")
    p2 = append(p1, _base_claims(jti="t2"), priv_b, kid="beta")

    # Tamper with p1's payload
    parts = p1.split(".")
    payload = bytearray(parts[1].encode())
    payload[len(payload) // 2] = ord("X") if payload[len(payload) // 2] != ord("X") else ord("Y")
    tampered = f"{parts[0]}.{payload.decode()}.{parts[2]}"

    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([tampered, p2])

    assert result.valid is False
    assert len(result.errors) > 0


# ── Trust Level Reporting ───────────────────────────────────────────


def test_trust_level_reporting() -> None:
    priv_a, pub_a = _make_keypair()
    priv_b, pub_b = _make_keypair()

    registry = IssuerRegistry()
    registry.register(Issuer("verified_co", pub_a, "Verified Corp", IssuerTrust.VERIFIED))
    registry.register(Issuer("self_co", pub_b, "Self Corp", IssuerTrust.SELF_DECLARED))

    p1 = append(None, _base_claims(jti="tr1"), priv_a, kid="verified_co")
    p2 = append(p1, _base_claims(jti="tr2"), priv_b, kid="self_co")

    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([p1, p2])

    assert result.trust_summary["verified_co"] == "verified"
    assert result.trust_summary["self_co"] == "self_declared"
    assert any("self-declared" in w for w in result.warnings)


# ── Edge Cases ──────────────────────────────────────────────────────


def test_empty_chain() -> None:
    registry = IssuerRegistry()
    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([])
    assert result.valid is True
    assert result.chain_length == 0


def test_single_proof() -> None:
    priv, pub = _make_keypair()
    registry = IssuerRegistry()
    registry.register(Issuer("solo", pub, "Solo"))

    p1 = append(None, _base_claims(jti="s1"), priv, kid="solo")

    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([p1])

    assert result.valid is True
    assert result.chain_length == 1
    assert result.cross_platform_hops == 0


def test_verify_single_method() -> None:
    priv, pub = _make_keypair()
    registry = IssuerRegistry()
    registry.register(Issuer("test", pub, "Test"))

    p1 = append(None, _base_claims(jti="vs1"), priv, kid="test")

    verifier = MeshVerifier(registry)
    link = verifier.verify_single(p1)

    assert link.signature_valid is True
    assert link.issuer_id == "test"
    assert link.issuer is not None

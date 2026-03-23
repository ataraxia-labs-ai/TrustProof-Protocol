from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trustproof import append, generate, verify, verify_chain  # noqa: E402


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


def test_generate_and_verify_happy_path() -> None:
    claims = _load_allow_claims()
    private_pem, public_pem = _generate_pem_keypair()

    token = generate(claims, private_pem)
    result = verify(token, public_pem)

    assert result["ok"] is True
    assert result["errors"] == []
    assert isinstance(result.get("claims"), dict)


def test_invalid_signature() -> None:
    claims = _load_allow_claims()
    private_pem_a, _public_pem_a = _generate_pem_keypair()
    _private_pem_b, public_pem_b = _generate_pem_keypair()

    token = generate(claims, private_pem_a)
    result = verify(token, public_pem_b)

    assert result["ok"] is False
    assert any(err.get("code") == "INVALID_SIGNATURE" for err in result["errors"])


def test_chain_append_and_verify_chain() -> None:
    """Generate → append → append → verify_chain passes."""
    base = _load_allow_claims()
    private_pem, public_pem = _generate_pem_keypair()

    def _claims(jti: str) -> dict:
        c = json.loads(json.dumps(base))
        c["jti"] = jti
        return c

    proof1 = append(None, _claims("chain_test_1"), private_pem)
    proof2 = append(proof1, _claims("chain_test_2"), private_pem)
    proof3 = append(proof2, _claims("chain_test_3"), private_pem)

    result = verify_chain([proof1, proof2, proof3], public_pem)
    assert result["ok"] is True
    assert result["errors"] == []


def test_tamper_single_byte_fails_verify() -> None:
    """Modify a byte in JWT payload → verify fails."""
    claims = _load_allow_claims()
    private_pem, public_pem = _generate_pem_keypair()

    token = generate(claims, private_pem)
    parts = token.split(".")
    # Tamper with the payload (middle section) — more reliable than signature
    payload = bytearray(parts[1].encode())
    mid = len(payload) // 2
    payload[mid] = ord("A") if payload[mid] != ord("A") else ord("B")
    tampered = f"{parts[0]}.{payload.decode()}.{parts[2]}"

    result = verify(tampered, public_pem)
    assert result["ok"] is False


def test_chain_tamper_breaks_verify_chain() -> None:
    """Modify one proof in a chain → verify_chain fails."""
    base = _load_allow_claims()
    private_pem, public_pem = _generate_pem_keypair()

    def _claims(jti: str) -> dict:
        c = json.loads(json.dumps(base))
        c["jti"] = jti
        return c

    proof1 = append(None, _claims("tamper_1"), private_pem)
    proof2 = append(proof1, _claims("tamper_2"), private_pem)

    # Tamper with proof1's payload
    parts = proof1.split(".")
    payload = bytearray(parts[1].encode())
    payload[-1] = ord("X") if payload[-1] != ord("X") else ord("Y")
    tampered = f"{parts[0]}.{payload.decode()}.{parts[2]}"

    result = verify_chain([tampered, proof2], public_pem)
    assert result["ok"] is False

from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from trustproof import generate  # noqa: E402
from trustproof.__main__ import main  # noqa: E402


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def test_main_inspect_with_argv(monkeypatch, capsys) -> None:
    header = {"alg": "none", "typ": "JWT"}
    payload = {"subject": {"id": "user_test"}, "action": "payout.initiate"}

    token = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}."
        "sig"
    )

    monkeypatch.setattr(sys, "argv", ["trustproof", "inspect", token])

    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"action": "payout.initiate"' in captured.out


def _load_allow_claims() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    return json.loads((repo_root / "spec" / "examples" / "allow.json").read_text())


def _make_keypair() -> tuple[str, str]:
    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return priv_pem, pub_pem


def test_cli_inspect_subprocess() -> None:
    """Test inspect via subprocess (python -m trustproof inspect)."""
    claims = _load_allow_claims()
    priv_pem, _ = _make_keypair()
    token = generate(claims, priv_pem)

    result = subprocess.run(
        [sys.executable, "-m", "trustproof", "inspect", token, "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["action"] == "payout.initiate"


def test_cli_verify_subprocess() -> None:
    """Test verify via subprocess (python -m trustproof verify --pubkey)."""
    claims = _load_allow_claims()
    priv_pem, pub_pem = _make_keypair()
    token = generate(claims, priv_pem)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
        f.write(pub_pem)
        pub_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, "-m", "trustproof", "verify", token, "--pubkey", pub_path, "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["ok"] is True
    finally:
        Path(pub_path).unlink(missing_ok=True)


def test_cli_version_subprocess() -> None:
    """Test version via subprocess."""
    result = subprocess.run(
        [sys.executable, "-m", "trustproof", "version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "trustproof 0.2.0" in result.stdout

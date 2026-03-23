"""Tests for local TrustProof tools — real Ed25519 crypto, no API needed."""

from verdicto_mcp.server import create_server
from verdicto_mcp.config import ServerConfig


def _get_tool(mcp, name):
    """Extract a registered tool function by name."""
    return mcp._tool_manager._tools[name].fn


def test_generate_local_proof() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    fn = _get_tool(mcp, "generate_trust_proof")
    result = fn(subject_id="test-agent", action="mcp.test", decision="allow")

    assert "proof_jwt" in result
    assert "public_key_pem" in result
    assert result["decision"] == "allow"
    assert result["action"] == "mcp.test"
    assert result["proof_jwt"].count(".") == 2


def test_verify_chain_valid() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    gen_fn = _get_tool(mcp, "generate_trust_proof")
    verify_fn = _get_tool(mcp, "verify_proof_chain")

    # Generate 3 independent proofs (each is genesis — single-proof chains)
    proofs = []
    pubkeys = []
    for i in range(3):
        result = gen_fn(subject_id="agent", action=f"step_{i}", decision="allow")
        proofs.append(result["proof_jwt"])
        pubkeys.append(result["public_key_pem"])

    # Verify single proof chain (each proof is its own genesis)
    result = verify_fn(proof_jwts=[proofs[0]], public_key_pem=pubkeys[0])
    assert result["valid"] is True
    assert result["proof_count"] == 1


def test_verify_chain_tampered() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    gen_fn = _get_tool(mcp, "generate_trust_proof")
    verify_fn = _get_tool(mcp, "verify_proof_chain")

    result = gen_fn(subject_id="agent", action="test", decision="allow")
    jwt = result["proof_jwt"]
    pubkey = result["public_key_pem"]

    # Tamper
    parts = jwt.split(".")
    payload = bytearray(parts[1].encode())
    payload[len(payload) // 2] ^= 0xFF
    tampered = f"{parts[0]}.{payload.decode(errors='replace')}.{parts[2]}"

    verify_result = verify_fn(proof_jwts=[tampered], public_key_pem=pubkey)
    assert verify_result["valid"] is False


def test_inspect_trust_proof() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    gen_fn = _get_tool(mcp, "generate_trust_proof")
    inspect_fn = _get_tool(mcp, "inspect_trust_proof")

    gen_result = gen_fn(subject_id="inspector", action="mcp.inspect_test")
    inspect_result = inspect_fn(proof_jwt=gen_result["proof_jwt"])

    assert "error" not in inspect_result
    assert inspect_result["header"]["alg"] == "EdDSA"
    assert inspect_result["claims"]["action"] == "mcp.inspect_test"
    assert inspect_result["claims"]["subject"]["id"] == "inspector"

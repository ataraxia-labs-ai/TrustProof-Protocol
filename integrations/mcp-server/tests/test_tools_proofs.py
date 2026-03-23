"""Tests for proof inspection tools."""

from verdicto_mcp.server import create_server
from verdicto_mcp.config import ServerConfig


def _get_tool(mcp, name):
    return mcp._tool_manager._tools[name].fn


def test_inspect_valid_jwt() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    gen_fn = _get_tool(mcp, "generate_trust_proof")
    inspect_fn = _get_tool(mcp, "inspect_trust_proof")

    gen_result = gen_fn(subject_id="proof-test", action="mcp.proof_test")
    result = inspect_fn(proof_jwt=gen_result["proof_jwt"])

    assert "error" not in result
    assert result["header"]["alg"] == "EdDSA"
    assert result["claims"]["decision"] == "allow"


def test_inspect_invalid_jwt() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    fn = _get_tool(mcp, "inspect_trust_proof")
    result = fn(proof_jwt="not.a.jwt")
    assert "error" in result


def test_verify_proof_without_api() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    fn = _get_tool(mcp, "verify_trust_proof")
    result = fn(proof_jwt="eyJ.test.jwt")
    assert "error" in result

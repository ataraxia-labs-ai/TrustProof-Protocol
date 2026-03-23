"""Tests for verification tools — mock the VerdictoClient."""

from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from verdicto_mcp.server import create_server
from verdicto_mcp.config import ServerConfig


def _get_tool(mcp, name):
    return mcp._tool_manager._tools[name].fn


def test_verify_without_api_key_returns_error() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    fn = _get_tool(mcp, "verify_agent_action")
    result = fn(requested_action="checkout.purchase")
    assert "error" in result
    assert "VERDICTO_API_KEY" in result["error"]


def test_issue_agent_pass_without_api_key() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    fn = _get_tool(mcp, "issue_agent_pass")
    result = fn(sub="agent", scopes=["test"])
    assert "error" in result


def test_list_verifications_without_api_key() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    fn = _get_tool(mcp, "list_recent_verifications")
    result = fn(limit=5)
    assert "error" in result


def test_health_without_api_key() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    fn = _get_tool(mcp, "check_api_health")
    result = fn()
    assert result["ok"] is False


def test_server_creates_with_all_tools() -> None:
    mcp = create_server(ServerConfig(api_key=None))
    tool_names = list(mcp._tool_manager._tools.keys())
    expected = [
        "verify_agent_action",
        "issue_agent_pass",
        "get_audit_trail",
        "get_evidence_bundle",
        "verify_trust_proof",
        "inspect_trust_proof",
        "list_recent_verifications",
        "check_api_health",
        "generate_trust_proof",
        "verify_proof_chain",
    ]
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"
    assert len(tool_names) == 10

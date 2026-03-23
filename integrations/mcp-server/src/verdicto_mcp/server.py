"""Verdicto MCP Server — Trust infrastructure for AI agents via Model Context Protocol.

Run locally (stdio, for Claude Desktop):
    verdicto-mcp

Run as HTTP server (for remote access):
    verdicto-mcp --transport http --port 9100

Environment variables:
    VERDICTO_API_URL — Verdicto API base URL (default: http://127.0.0.1:8000)
    VERDICTO_API_KEY — API key for authenticated operations
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .config import ServerConfig
from .tools_cases import register_case_tools
from .tools_local import register_local_tools
from .tools_proofs import register_proof_tools
from .tools_verify import register_verify_tools


def create_server(config: ServerConfig | None = None) -> FastMCP:
    """Create the Verdicto MCP server with all tools registered."""
    if config is None:
        config = ServerConfig.from_env()

    mcp = FastMCP(
        name="Verdicto Trust Infrastructure",
        instructions=(
            "You have access to Verdicto trust infrastructure tools. "
            "Use these tools to verify AI agent actions, issue constrained Agent Passes, "
            "inspect and verify cryptographic Trust Proofs, and query audit trails.\n\n"
            "When a user asks you to perform a sensitive action (payment, data access, "
            "code modification), use verify_agent_action to get a signed Trust Proof "
            "before proceeding.\n\n"
            "When asked about trust, verification, or audit trails, use the appropriate "
            "Verdicto tool rather than making assumptions."
        ),
    )

    register_verify_tools(mcp, config)
    register_proof_tools(mcp, config)
    register_case_tools(mcp, config)
    register_local_tools(mcp)

    return mcp


def main() -> None:
    """Entry point for the verdicto-mcp command."""
    transport = "stdio"
    port = 9100

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--transport" and i + 1 < len(args):
            transport = args[i + 1]
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

    server = create_server()
    if transport == "http":
        server.run(transport="sse", port=port)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()

"""Case and audit query tools — require Verdicto API."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import ServerConfig


def register_case_tools(mcp: FastMCP, config: ServerConfig) -> None:

    @mcp.tool()
    def list_recent_verifications(limit: int = 10) -> dict:
        """List recent trust verification decisions.

        Shows the most recent agent action verifications with decisions,
        confidence scores, and reason codes.

        Args:
            limit: Number of cases to return (1-50)
        """
        if not config.api_configured:
            return {"error": "Verdicto API not configured. Set VERDICTO_API_KEY."}
        try:
            from verdicto import VerdictoClient
            client = VerdictoClient(api_key=config.api_key or "", base_url=config.api_url)
            result = client.list_cases(limit=min(max(limit, 1), 50))
            client.close()
            return {
                "cases": [
                    {
                        "id": c.id,
                        "decision": c.decision,
                        "confidence": c.confidence,
                        "created_at": c.created_at,
                    }
                    for c in result.cases
                ],
                "total": len(result.cases),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def check_api_health() -> dict:
        """Check if the Verdicto trust infrastructure API is healthy.

        Returns service status, database connectivity, and version info.
        """
        if not config.api_configured:
            return {"ok": False, "error": "API not configured. Set VERDICTO_API_KEY."}
        try:
            from verdicto import VerdictoClient
            client = VerdictoClient(api_key=config.api_key or "", base_url=config.api_url)
            result = client.health()
            client.close()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

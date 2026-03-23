"""Proof inspection and verification tools."""

from __future__ import annotations

import base64
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import ServerConfig


def _decode_jwt_untrusted(token: str) -> tuple[dict, dict]:
    """Decode JWT header and payload without verification."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format (expected 3 dot-separated segments)")

    def _decode_segment(seg: str) -> dict:
        padded = seg + "=" * ((4 - len(seg) % 4) % 4)
        data = base64.urlsafe_b64decode(padded)
        return json.loads(data)

    return _decode_segment(parts[0]), _decode_segment(parts[1])


def register_proof_tools(mcp: FastMCP, config: ServerConfig) -> None:

    @mcp.tool()
    def verify_trust_proof(proof_jwt: str) -> dict:
        """Cryptographically verify a Trust Proof JWT.

        Checks the Ed25519 signature and returns decoded claims.
        Uses the Verdicto API if configured, otherwise uses local verification.

        Args:
            proof_jwt: The JWT string to verify
        """
        if config.api_configured:
            try:
                from verdicto import VerdictoClient
                client = VerdictoClient(api_key=config.api_key or "", base_url=config.api_url)
                result = client.verify_proof(proof_jwt)
                client.close()
                return {
                    "valid": result.ok,
                    "verification_id": result.verification_id,
                    "decision": result.decision,
                    "reason_codes": result.reason_codes,
                    "issued_at": result.issued_at,
                }
            except Exception as e:
                return {"valid": False, "error": str(e)}

        # Fall back to local verification — needs public key
        return {
            "error": "No API configured for server-side verification. Use inspect_trust_proof to decode claims, or configure VERDICTO_API_KEY for cryptographic verification."
        }

    @mcp.tool()
    def inspect_trust_proof(proof_jwt: str) -> dict:
        """Decode and display a Trust Proof JWT without cryptographic verification.

        Shows the full claims payload: subject, action, policy, decision, hashes, chain info.
        Useful for debugging. Does NOT verify the signature.

        Args:
            proof_jwt: The JWT string to inspect
        """
        try:
            header, claims = _decode_jwt_untrusted(proof_jwt)
            chain = claims.get("chain", {})
            return {
                "header": {"alg": header.get("alg"), "typ": header.get("typ")},
                "claims": {
                    "subject": claims.get("subject"),
                    "action": claims.get("action"),
                    "resource": claims.get("resource"),
                    "decision": (claims.get("result") or {}).get("decision"),
                    "reason_codes": (claims.get("result") or {}).get("reason_codes", []),
                    "timestamp": claims.get("timestamp"),
                    "jti": claims.get("jti"),
                },
                "chain": {
                    "prev_hash": chain.get("prev_hash", "")[:16] + "...",
                    "entry_hash": chain.get("entry_hash", "")[:16] + "...",
                },
                "has_protocol_refs": "protocol_refs" in claims,
                "has_vc_profile": "vc_profile" in claims,
            }
        except Exception as e:
            return {"error": f"Failed to decode JWT: {e}"}

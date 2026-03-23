"""Local TrustProof tools — no API needed."""

from __future__ import annotations

from uuid import uuid4
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from mcp.server.fastmcp import FastMCP

from trustproof import generate, verify_chain as tp_verify_chain
from trustproof.chain import canonical_json, sha256_hex


def register_local_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def generate_trust_proof(
        subject_id: str,
        action: str,
        decision: str = "allow",
        reason_codes: list[str] | None = None,
        input_data: str | None = None,
        output_data: str | None = None,
    ) -> dict:
        """Generate a locally signed Trust Proof without the Verdicto API.

        Creates a cryptographically signed proof using a locally generated Ed25519 key.
        Useful for development, testing, or air-gapped environments.

        Args:
            subject_id: Who is performing the action
            action: What action (e.g. "autoresearch.experiment", "mcp.tool_invocation")
            decision: "allow" or "deny"
            reason_codes: Explanatory codes
            input_data: Input to hash (optional)
            output_data: Output to hash (optional)
        """
        try:
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

            input_hash = sha256_hex(canonical_json(input_data or ""))
            output_hash = sha256_hex(canonical_json(output_data or ""))

            from trustproof import append
            claims: dict = {
                "subject": {"type": "agent", "id": subject_id},
                "action": action,
                "resource": {"type": "mcp", "id": action},
                "policy": {"policy_v": "v0", "scopes": [action], "constraints": {}},
                "result": {"decision": decision, "reason_codes": reason_codes or []},
                "hashes": {"input_hash": input_hash, "output_hash": output_hash},
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "jti": str(uuid4()),
            }

            proof_jwt = append(None, claims, private_pem)
            return {
                "proof_jwt": proof_jwt,
                "public_key_pem": public_pem,
                "subject_id": subject_id,
                "action": action,
                "decision": decision,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def verify_proof_chain(proof_jwts: list[str], public_key_pem: str) -> dict:
        """Verify a chain of Trust Proofs for tamper evidence.

        Checks that every proof is correctly linked to the previous one.
        If any proof has been modified, the chain breaks.

        Args:
            proof_jwts: Ordered list of JWT strings forming the chain
            public_key_pem: PEM-encoded Ed25519 public key
        """
        try:
            result = tp_verify_chain(proof_jwts, public_key_pem)
            return {
                "valid": result["ok"],
                "proof_count": len(proof_jwts),
                "errors": result.get("errors", []),
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

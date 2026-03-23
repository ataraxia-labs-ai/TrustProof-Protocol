"""Verdicto Mesh Client — extends VerdictoClient with Proof Mesh capabilities."""
from __future__ import annotations

from typing import Any

from .client import VerdictoClient


class VerdictoMeshClient:
    """Wraps a VerdictoClient to add mesh verification via the API."""

    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:8000"):
        self._client = VerdictoClient(api_key=api_key, base_url=base_url)

    def verify_mesh_chain(self, proof_jwts: list[str]) -> dict[str, Any]:
        """Verify a mesh chain via the Verdicto API."""
        return self._client._request("POST", "/v1/mesh/verify", json={"proof_jwts": proof_jwts})

    def register_issuer(
        self,
        issuer_id: str,
        public_key_pem: str,
        display_name: str = "",
        trust_level: str = "self_declared",
    ) -> dict[str, Any]:
        """Register an external issuer in the tenant's mesh registry."""
        return self._client._request("POST", "/v1/mesh/register-issuer", json={
            "issuer_id": issuer_id,
            "public_key_pem": public_key_pem,
            "display_name": display_name,
            "trust_level": trust_level,
        })

    def list_issuers(self) -> dict[str, Any]:
        """List registered issuers for the current tenant."""
        return self._client._request("GET", "/v1/mesh/issuers")

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> VerdictoMeshClient:
        return self

    def __exit__(self, *a: Any) -> None:
        self.close()

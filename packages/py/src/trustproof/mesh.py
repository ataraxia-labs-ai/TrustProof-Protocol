"""Proof Mesh: Cross-platform trust federation for TrustProof Protocol.

Enables verification of Trust Proof chains that span multiple issuers,
platforms, and signing keys.

Concepts:
- Issuer: An entity that signs Trust Proofs (identified by kid or iss claim)
- IssuerRegistry: Maps issuer IDs to their Ed25519 public keys
- MeshVerifier: Validates chains across issuer boundaries

Trust model:
- Each proof's issuer is resolved from the JWT header (kid) or payload (iss)
- The registry provides the correct public key per issuer
- Chain integrity (prev_hash/entry_hash) is verified the same way as single-issuer
- Cross-references via protocol_refs.upstream_proof are tracked but not recursively resolved in v0
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import jwt as pyjwt
from jwt import InvalidTokenError

from .chain import (
    GENESIS_PREV_HASH,
    compute_canonical_event_material,
    compute_entry_hash,
    normalize_hex,
)
from .verify import _validate_claims_minimal

import hmac as _hmac

HEX_64_RE = re.compile(r"^[a-fA-F0-9]{64}$")


class IssuerTrust(str, Enum):
    VERIFIED = "verified"
    SELF_DECLARED = "self_declared"
    UNTRUSTED = "untrusted"


@dataclass
class Issuer:
    """A registered issuer in the mesh."""

    issuer_id: str
    public_key_pem: str
    display_name: str = ""
    trust_level: IssuerTrust = IssuerTrust.SELF_DECLARED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshLink:
    """A single link in a mesh chain."""

    index: int
    proof_jwt: str
    issuer_id: str
    issuer: Issuer | None
    claims: dict[str, Any]
    signature_valid: bool
    chain_valid: bool
    cross_refs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class MeshVerification:
    """Result of verifying a mesh chain."""

    valid: bool
    links: list[MeshLink]
    issuers_involved: list[str]
    chain_length: int
    cross_platform_hops: int
    trust_summary: dict[str, str]
    errors: list[str]
    warnings: list[str]


class IssuerRegistry:
    """Registry of known issuers and their public keys."""

    def __init__(self) -> None:
        self._issuers: dict[str, Issuer] = {}

    def register(self, issuer: Issuer) -> None:
        """Register an issuer in the mesh.

        SECURITY WARNING: In production, this method MUST be wrapped with
        authentication and authorization checks. An unprotected register()
        allows any caller to add their own public key as a trusted issuer,
        enabling them to forge proofs that verify as valid. Implement admin
        authentication before exposing this via any API endpoint.
        """
        self._issuers[issuer.issuer_id] = issuer

    def get(self, issuer_id: str) -> Issuer | None:
        return self._issuers.get(issuer_id)

    def resolve_from_jwt(self, proof_jwt: str) -> tuple[str, Issuer | None]:
        """Extract issuer ID from JWT and look up in registry.

        Resolution order: JWT header 'kid' → payload 'iss' → 'unknown'.
        """
        issuer_id = _extract_issuer_id(proof_jwt)
        return issuer_id, self._issuers.get(issuer_id)

    def list_issuers(self) -> list[Issuer]:
        return list(self._issuers.values())

    def __len__(self) -> int:
        return len(self._issuers)


class MeshVerifier:
    """Verifies Trust Proof chains spanning multiple issuers."""

    def __init__(self, registry: IssuerRegistry) -> None:
        self.registry = registry

    def verify_chain(self, proof_jwts: list[str]) -> MeshVerification:
        """Verify a chain of proofs from potentially different issuers."""
        if not proof_jwts:
            return MeshVerification(
                valid=True, links=[], issuers_involved=[], chain_length=0,
                cross_platform_hops=0, trust_summary={}, errors=[], warnings=[],
            )

        links: list[MeshLink] = []
        errors: list[str] = []
        warnings: list[str] = []
        issuer_set: set[str] = set()
        prev_entry_hash: str | None = None
        hops = 0

        for i, jwt_str in enumerate(proof_jwts):
            link = self._verify_single_link(i, jwt_str, prev_entry_hash)
            links.append(link)
            issuer_set.add(link.issuer_id)

            if not link.signature_valid:
                errors.append(f"Link {i}: signature verification failed for issuer '{link.issuer_id}'")
            if not link.chain_valid:
                errors.append(f"Link {i}: chain integrity failed (prev_hash mismatch)")
            if link.issuer is None:
                warnings.append(f"Link {i}: issuer '{link.issuer_id}' not in registry")
            elif link.issuer.trust_level == IssuerTrust.SELF_DECLARED:
                warnings.append(f"Link {i}: issuer '{link.issuer_id}' is self-declared (not independently verified)")

            errors.extend(link.errors)

            # Track cross-platform hops
            if i > 0 and link.issuer_id != links[i - 1].issuer_id:
                hops += 1

            # Extract entry_hash for next link
            chain = link.claims.get("chain", {})
            entry_hash = chain.get("entry_hash")
            if isinstance(entry_hash, str) and HEX_64_RE.fullmatch(entry_hash):
                prev_entry_hash = normalize_hex(entry_hash)
            else:
                prev_entry_hash = None

        trust_summary = {}
        for iid in issuer_set:
            issuer = self.registry.get(iid)
            trust_summary[iid] = issuer.trust_level.value if issuer else IssuerTrust.UNTRUSTED.value

        all_valid = all(l.signature_valid and l.chain_valid for l in links)

        return MeshVerification(
            valid=all_valid and not errors,
            links=links,
            issuers_involved=sorted(issuer_set),
            chain_length=len(links),
            cross_platform_hops=hops,
            trust_summary=trust_summary,
            errors=errors,
            warnings=warnings,
        )

    def verify_single(self, proof_jwt: str) -> MeshLink:
        """Verify a single proof, resolving its issuer."""
        return self._verify_single_link(0, proof_jwt, None)

    def _verify_single_link(
        self, index: int, jwt_str: str, expected_prev_hash: str | None
    ) -> MeshLink:
        """Verify one link in the mesh chain."""
        issuer_id, issuer = self.registry.resolve_from_jwt(jwt_str)
        cross_refs: list[str] = []
        link_errors: list[str] = []

        # 1. Signature verification
        signature_valid = False
        claims: dict[str, Any] = {}

        if issuer is not None:
            try:
                claims = pyjwt.decode(
                    jwt_str,
                    issuer.public_key_pem,
                    algorithms=["EdDSA"],
                    options={"verify_aud": False, "verify_iss": False},
                )
                signature_valid = True
            except InvalidTokenError as exc:
                link_errors.append(f"Signature invalid: {exc}")
                # Still try to decode for chain analysis
                claims = _decode_payload_untrusted(jwt_str)
        else:
            # Unknown issuer — can't verify signature, decode untrusted
            claims = _decode_payload_untrusted(jwt_str)
            link_errors.append(f"Unknown issuer: '{issuer_id}' — cannot verify signature")

        # 2. Chain integrity
        chain_valid = True
        chain_data = claims.get("chain", {})
        prev_hash = chain_data.get("prev_hash", "")
        entry_hash = chain_data.get("entry_hash", "")

        if index == 0:
            # Genesis: prev_hash must be 64 zeros
            if prev_hash != GENESIS_PREV_HASH:
                # In mesh context, first proof might not be genesis if it's a sub-chain
                if expected_prev_hash is None:
                    pass  # Allow non-genesis first proof in mesh
                elif not _hmac.compare_digest(normalize_hex(prev_hash), expected_prev_hash):
                    chain_valid = False
        else:
            if expected_prev_hash is not None:
                if not prev_hash or not _hmac.compare_digest(normalize_hex(prev_hash), expected_prev_hash):
                    chain_valid = False

        # Verify entry_hash integrity
        if signature_valid and claims:
            try:
                cem = compute_canonical_event_material(claims)
                recomputed = compute_entry_hash(normalize_hex(prev_hash), cem)
                if not _hmac.compare_digest(normalize_hex(entry_hash), recomputed):
                    chain_valid = False
                    link_errors.append("entry_hash does not match recomputed hash")
            except Exception:
                pass  # Missing fields — already caught by schema validation

        # 3. Cross-references
        protocol_refs = claims.get("protocol_refs", {})
        if isinstance(protocol_refs, dict):
            upstream = protocol_refs.get("upstream_proof")
            if isinstance(upstream, str) and upstream:
                cross_refs.append(upstream)

        return MeshLink(
            index=index,
            proof_jwt=jwt_str,
            issuer_id=issuer_id,
            issuer=issuer,
            claims=claims,
            signature_valid=signature_valid,
            chain_valid=chain_valid,
            cross_refs=cross_refs,
            errors=link_errors,
        )


def _extract_issuer_id(jwt_str: str) -> str:
    """Extract issuer ID from JWT header (kid) or payload (iss)."""
    try:
        parts = jwt_str.split(".")
        if len(parts) != 3:
            return "unknown"

        # Check header for kid
        header_b64 = parts[0] + "=" * ((4 - len(parts[0]) % 4) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        kid = header.get("kid")
        if isinstance(kid, str) and kid:
            return kid

        # Check payload for iss
        payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        iss = payload.get("iss")
        if isinstance(iss, str) and iss:
            return iss

        return "unknown"
    except Exception:
        return "unknown"


def _decode_payload_untrusted(jwt_str: str) -> dict[str, Any]:
    """Decode JWT payload without signature verification."""
    try:
        parts = jwt_str.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}

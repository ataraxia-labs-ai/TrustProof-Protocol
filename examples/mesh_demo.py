"""Proof Mesh Demo: Multi-issuer chain verification.

Two issuers with separate Ed25519 keys create a chain of proofs
that crosses issuer boundaries. The MeshVerifier validates the
entire chain using per-issuer key resolution.
"""
import json
import os
import sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from trustproof import append
from trustproof.mesh import MeshVerifier, IssuerRegistry, Issuer, IssuerTrust


# ── Helpers ────────────────────────────────────────────────────────


def _generate_keypair(label: str) -> tuple[str, str]:
    """Generate an Ed25519 keypair, return (private_pem, public_pem) as strings."""
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    print(f"  Generated {label} keypair")
    return private_pem, public_pem


def _section(title: str) -> None:
    width = 64
    print()
    print(f"{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _step(n: int, text: str) -> None:
    print(f"\n  [{n}] {text}")


def _kv(key: str, value: object, indent: int = 6) -> None:
    pad = " " * indent
    print(f"{pad}{key:<26} {value}")


# ── Main demo ──────────────────────────────────────────────────────


def main() -> None:
    _section("Proof Mesh Demo  --  Multi-Issuer Chain Verification")

    # ------------------------------------------------------------------
    # Step 1: Generate two Ed25519 keypairs
    # ------------------------------------------------------------------
    _step(1, "Generating Ed25519 keypairs for two issuers...")
    alpha_priv, alpha_pub = _generate_keypair("issuer_alpha")
    beta_priv, beta_pub = _generate_keypair("issuer_beta")

    # ------------------------------------------------------------------
    # Step 2: Load base claims from spec/examples/allow.json
    # ------------------------------------------------------------------
    _step(2, "Loading base claims from spec/examples/allow.json...")
    spec_path = Path(__file__).resolve().parent.parent / "spec" / "examples" / "allow.json"
    if not spec_path.exists():
        # Fallback: try relative to cwd
        spec_path = Path("spec/examples/allow.json")
    if not spec_path.exists():
        print(f"  ERROR: Cannot find allow.json at {spec_path}")
        sys.exit(1)

    with open(spec_path) as f:
        base_claims = json.load(f)
    print(f"  Loaded base claims (action={base_claims.get('action')}, jti={base_claims.get('jti')})")

    # ------------------------------------------------------------------
    # Step 3: Issuer Alpha creates proof 1 (genesis)
    # ------------------------------------------------------------------
    _step(3, "Issuer Alpha creates proof 1 (genesis, action='delegate')...")
    claims_1 = {**base_claims, "action": "delegate", "jti": "mesh_demo_p1"}
    p1 = append(None, claims_1, alpha_priv, kid="alpha")
    print(f"  Proof 1: {p1[:60]}...")

    # ------------------------------------------------------------------
    # Step 4: Issuer Alpha creates proof 2 (chained to p1)
    # ------------------------------------------------------------------
    _step(4, "Issuer Alpha creates proof 2 (chained to p1, action='search')...")
    claims_2 = {**base_claims, "action": "search", "jti": "mesh_demo_p2"}
    p2 = append(p1, claims_2, alpha_priv, kid="alpha")
    print(f"  Proof 2: {p2[:60]}...")

    # ------------------------------------------------------------------
    # Step 5: Issuer Beta creates proof 3 -- CROSS-ISSUER HOP!
    # ------------------------------------------------------------------
    _step(5, "Issuer Beta creates proof 3 (CROSS-ISSUER! chained to p2, action='compare')...")
    claims_3 = {**base_claims, "action": "compare", "jti": "mesh_demo_p3"}
    p3 = append(p2, claims_3, beta_priv, kid="beta")
    print(f"  Proof 3: {p3[:60]}...")
    print("  >>> This is a CROSS-ISSUER hop: alpha -> beta")

    # ------------------------------------------------------------------
    # Step 6: Issuer Alpha creates proof 4 (chained to p3)
    # ------------------------------------------------------------------
    _step(6, "Issuer Alpha creates proof 4 (chained to p3, action='complete')...")
    claims_4 = {**base_claims, "action": "complete", "jti": "mesh_demo_p4"}
    p4 = append(p3, claims_4, alpha_priv, kid="alpha")
    print(f"  Proof 4: {p4[:60]}...")
    print("  >>> Another CROSS-ISSUER hop: beta -> alpha")

    # ------------------------------------------------------------------
    # Step 7: Register both issuers in the registry
    # ------------------------------------------------------------------
    _step(7, "Registering both issuers in the IssuerRegistry...")
    registry = IssuerRegistry()
    registry.register(Issuer(
        issuer_id="alpha",
        public_key_pem=alpha_pub,
        display_name="Issuer Alpha (Shopping Platform)",
        trust_level=IssuerTrust.VERIFIED,
    ))
    registry.register(Issuer(
        issuer_id="beta",
        public_key_pem=beta_pub,
        display_name="Issuer Beta (Comparison Engine)",
        trust_level=IssuerTrust.SELF_DECLARED,
    ))
    print(f"  Registered {len(registry)} issuers: alpha (verified), beta (self_declared)")

    # ------------------------------------------------------------------
    # Step 8: Verify the chain using MeshVerifier
    # ------------------------------------------------------------------
    _step(8, "Verifying the full mesh chain...")
    verifier = MeshVerifier(registry)
    result = verifier.verify_chain([p1, p2, p3, p4])

    # ------------------------------------------------------------------
    # Step 9: Print results
    # ------------------------------------------------------------------
    _section("Mesh Verification Results")

    status_icon = "PASS" if result.valid else "FAIL"
    print(f"\n  Result: {status_icon}")
    print()
    _kv("valid:", result.valid)
    _kv("chain_length:", result.chain_length)
    _kv("issuers_involved:", ", ".join(result.issuers_involved))
    _kv("cross_platform_hops:", result.cross_platform_hops)

    print(f"\n  Trust Summary:")
    for issuer_id, trust in result.trust_summary.items():
        _kv(f"  {issuer_id}:", trust, indent=6)

    if result.warnings:
        print(f"\n  Warnings:")
        for w in result.warnings:
            print(f"      - {w}")

    if result.errors:
        print(f"\n  Errors:")
        for e in result.errors:
            print(f"      - {e}")

    print(f"\n  {'─' * 56}")
    print(f"  Per-Link Details:")
    print(f"  {'─' * 56}")

    for link in result.links:
        issuer_label = link.issuer.display_name if link.issuer else link.issuer_id
        sig_icon = "OK" if link.signature_valid else "FAIL"
        chain_icon = "OK" if link.chain_valid else "FAIL"
        action = link.claims.get("action", "?")

        print(f"\n      Link {link.index}:")
        _kv("issuer:", f"{link.issuer_id} ({issuer_label})", indent=10)
        _kv("action:", action, indent=10)
        _kv("signature:", sig_icon, indent=10)
        _kv("chain_integrity:", chain_icon, indent=10)
        if link.cross_refs:
            _kv("cross_refs:", ", ".join(link.cross_refs), indent=10)

    _section("Demo Complete")
    print()
    if result.valid:
        print("  All 4 proofs verified across 2 issuers with 2 cross-platform hops.")
        print("  The Proof Mesh maintained integrity across issuer boundaries.")
    else:
        print("  Verification FAILED. Check the errors above.")
    print()


if __name__ == "__main__":
    main()

# TrustProof Proof Mesh: Cross-Platform Trust Federation

## Overview

Proof Mesh enables Trust Proof chains that span multiple issuers, platforms, and signing keys. A LangChain agent's proof can chain-link to an OpenClaw agent's proof, which can chain-link to a Verdicto verification — all independently signed, all verifiable.

## Issuer Identification

Each proof's issuer is resolved from:
1. JWT header `kid` field (preferred — set via `generate(claims, key, kid="issuer_id")`)
2. JWT payload `iss` field (fallback)

The issuer ID is a free-form string. Recommended convention: `platform:identifier` (e.g., `verdicto:tenant_abc`, `openclaw:deployment_xyz`).

## IssuerRegistry

The verifier maintains a registry mapping issuer IDs to Ed25519 public keys:

```python
from trustproof.mesh import IssuerRegistry, Issuer, IssuerTrust

registry = IssuerRegistry()
registry.register(Issuer(
    issuer_id="verdicto:tenant_abc",
    public_key_pem=verdicto_pubkey,
    display_name="Acme Corp",
    trust_level=IssuerTrust.VERIFIED,
))
```

## Chain Verification Across Issuers

Chain integrity (`prev_hash` / `entry_hash`) is key-independent — it's SHA-256 hash computation that works regardless of who signed each proof. The mesh verifier:

1. For each proof, resolves the issuer from the JWT header
2. Looks up the issuer's public key in the registry
3. Verifies the Ed25519 signature with the correct key
4. Verifies `prev_hash` matches the previous proof's `entry_hash`
5. Recomputes `entry_hash` to ensure integrity

## Trust Levels

| Level | Meaning | When to use |
|-------|---------|-------------|
| `verified` | Issuer identity confirmed independently | DID resolution, organizational certificate |
| `self_declared` | Issuer provided key, not independently verified | Development, direct key exchange |
| `untrusted` | Issuer not in registry | Unknown proofs encountered in the wild |

## Cross-References

The `protocol_refs.upstream_proof` field creates cross-chain references:

```json
{
  "protocol_refs": {
    "upstream_proof": "sha256_of_upstream_jwt"
  }
}
```

This enables a DAG (directed acyclic graph) of proofs across organizational boundaries.

## Security Considerations

**Key compromise**: If an issuer's key is compromised, only proofs from that issuer are affected. Other issuers' proofs remain valid. Revoke the compromised issuer from the registry.

**Key rotation**: Issuers can rotate keys. Register new key under the same issuer ID. Old proofs remain verifiable with the old key if stored.

**Trust transitivity**: Trusting Issuer A and A trusting B does NOT automatically mean you trust B. Each issuer must be explicitly registered. This is a security feature — no implicit trust chains.

## Example

```python
from trustproof import append
from trustproof.mesh import MeshVerifier, IssuerRegistry, Issuer, IssuerTrust

# Two organizations with separate keys
registry = IssuerRegistry()
registry.register(Issuer("platform_a", pub_a, "Platform A", IssuerTrust.VERIFIED))
registry.register(Issuer("platform_b", pub_b, "Platform B", IssuerTrust.SELF_DECLARED))

# Platform A creates proofs 1-2
p1 = append(None, claims_1, priv_a, kid="platform_a")
p2 = append(p1, claims_2, priv_a, kid="platform_a")

# Platform B creates proof 3 (chain-linked to A's proof!)
p3 = append(p2, claims_3, priv_b, kid="platform_b")

# Platform A creates proof 4 (chain-linked back)
p4 = append(p3, claims_4, priv_a, kid="platform_a")

# Verify the entire cross-platform chain
verifier = MeshVerifier(registry)
result = verifier.verify_chain([p1, p2, p3, p4])
assert result.valid
assert result.cross_platform_hops == 2
```

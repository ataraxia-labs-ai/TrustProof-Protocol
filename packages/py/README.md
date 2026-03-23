# TrustProof

Signed, verifiable action receipts for humans + AI agents.

[![PyPI](https://img.shields.io/pypi/v/trustproof)](https://pypi.org/project/trustproof/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/LICENSE)

## What is a TrustProof?

A TrustProof is a cryptographically signed JWT (Ed25519/EdDSA) that binds: **who** (subject) did **what** (action) to **which resource**, under **what policy**, with **what result** — plus tamper-evident chain linking for sequential audit trails.

When an AI agent books a flight, transfers money, or modifies code — a TrustProof proves who authorized it, what constraints were in place, and that the agent acted within scope. Interoperable with W3C Verifiable Credentials, Mastercard Verifiable Intent, Google AP2, and major agent frameworks.

## Install

```bash
pip install trustproof
```

## Quick Start

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from trustproof import generate, verify

# Generate an Ed25519 keypair
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

# Build claims and sign
claims = {
    "subject": {"type": "agent", "id": "shopping-agent-v1"},
    "action": "checkout.purchase",
    "resource": {"type": "api", "id": "merchant:store:checkout"},
    "policy": {
        "policy_v": "v0",
        "scopes": ["checkout.purchase"],
        "constraints": {"max_amount_cents": 5000, "currency_allowlist": ["USD"]},
    },
    "result": {"decision": "allow", "reason_codes": []},
    "hashes": {"input_hash": "a" * 64, "output_hash": "b" * 64},
    "timestamp": "2026-03-21T12:00:00Z",
    "jti": "unique-replay-id",
    "chain": {"prev_hash": "0" * 64, "entry_hash": "c" * 64},
}
token = generate(claims, private_pem)
result = verify(token, public_pem)
assert result["ok"]
```

## Chain Linking (Tamper-Evident Audit Trail)

```python
from trustproof import append, verify_chain

proof1 = append(None, claims1, private_pem)       # genesis
proof2 = append(proof1, claims2, private_pem)      # linked
proof3 = append(proof2, claims3, private_pem)      # linked

chain_result = verify_chain([proof1, proof2, proof3], public_pem)
assert chain_result["ok"]  # any tampering breaks the chain
```

## Cross-Protocol Interop (v0.2)

```python
claims["protocol_refs"] = {
    "ap2_mandate_id": "mandate_cart_abc123",
    "verifiable_intent_id": "vi_mc_def456",
    "mcp_tool_call_id": "mcp_call_789",
}
claims["vc_profile"] = {
    "vc_version": "2.0",
    "credential_type": ["VerifiableCredential", "TrustProofCredential"],
    "issuer_did": "did:web:verdicto.dev",
}
```

## CLI

```bash
trustproof inspect "eyJhbGci..."           # decode without verification
trustproof verify "eyJhbGci..." --pubkey public.pem  # full verification
trustproof version                          # print version
trustproof schema                           # print JSON Schema
```

## Type Annotations

Ships with inline type annotations (`py.typed`):

```python
from trustproof import TrustProofClaims, VerifyResult, ProtocolRefs, VCProfile
```

## Protocol Spec

- [Full Specification](https://ataraxia-labs-ai.github.io/TrustProof-Protocol/)
- [JSON Schema](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/spec/trustproof.schema.json)
- [Golden Vectors](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/tree/main/spec/vectors)

## License

Apache-2.0

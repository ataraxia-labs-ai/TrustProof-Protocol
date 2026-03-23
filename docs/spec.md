# TrustProof Spec

## What is a TrustProof

A TrustProof is a claims envelope (JSON) signed as a JWT.  
The signed payload captures actor, action, policy context, result, integrity hashes, and chain linkage.

Primary functions:

```txt
generate(claims, privateKeyPem, opts?) -> jwt
verify(jwt, publicKeyPem, opts?) -> { ok, claims, errors[] }
append(prevJwtOrClaimsOrNull, nextClaims, privateKeyPem, opts?) -> jwt
verifyChain(jwts[], publicKeyPem, opts?) -> { ok, errors[] }
```

## Envelope Fields (v1)

- `subject`: actor identity (`type`, `id`)
- `action`: operation name (for example `payout.initiate`)
- `resource`: target (`type`, `id`)
- `policy`: policy version/scopes/constraints
- `result`: decision + reason codes
- `hashes`: `input_hash`, `output_hash`
- `timestamp`: event timestamp (ISO UTC)
- `jti`: replay identifier (required)
- `chain`: `prev_hash`, `entry_hash`

Schema:

- [`../spec/trustproof.schema.json`](../spec/trustproof.schema.json)

Examples:

- [`../spec/examples/allow.json`](../spec/examples/allow.json)
- [`../spec/examples/deny.json`](../spec/examples/deny.json)
- [`../spec/examples/step_up.json`](../spec/examples/step_up.json)

Vectors:

- [`../spec/vectors/`](../spec/vectors/)

## Canonicalization and Hash Rules

Normative definitions are in:

- [`../spec/README.md`](../spec/README.md)

In brief:

- Canonical JSON is deterministic (sorted object keys, compact separators).
- `input_hash = sha256(canonical_json(input))`
- `output_hash = sha256(canonical_json(output))`

## Chain Rules (Summary)

- `canonical_event_material = canonical_json({ subject, action, resource, policy, result, hashes, timestamp, jti })`
- `entry_hash = sha256(prev_hash_hex_string + canonical_event_material_utf8_string)`
- Genesis `prev_hash` is 64 zeros.

Reference vectors:

- [`../spec/vectors/v001_allow_basic.json`](../spec/vectors/v001_allow_basic.json)
- [`../spec/vectors/v004_chain_linking.json`](../spec/vectors/v004_chain_linking.json)
- [`../spec/vectors/v005_canonicalization_edge.json`](../spec/vectors/v005_canonicalization_edge.json)

## Validate the Spec

From repo root:

```bash
pnpm spec:validate
```

CLI verification commands:

```bash
trustproof inspect "<jwt>"
trustproof verify "<jwt>" --pubkey "<pem|b64|path>"
```

---

## Protocol References (v0.2)

The `protocol_refs` field (optional) links a TrustProof to artifacts in external trust and commerce protocols, enabling cross-protocol verification chains.

### Supported References

**Mastercard Verifiable Intent** (`verifiable_intent_id`): Links to a Mastercard Verifiable Intent record, connecting the TrustProof to a payment-layer authorization proof. The Verifiable Intent protocol (announced March 2026) provides cryptographic proof that a consumer authorized a specific purchase, reducing chargebacks and fraud. TrustProof references create an end-to-end chain: agent action → trust decision → payment authorization.

**Google AP2 Agent Payments Protocol** (`ap2_mandate_id`, `ap2_mandate_type`): Links to Google's Agent-to-Pay Protocol mandate. AP2 defines three mandate types: `intent` (user instruction to an agent), `cart` (specific purchase approval), and `payment` (payment network authorization). TrustProof bridges the gap between the AP2 mandate and the actual agent action, proving the action was authorized before the mandate was exercised.

**Stripe/OpenAI Agentic Commerce Protocol** (`acp_checkout_id`): Links to a checkout session in the Agentic Commerce Protocol. ACP handles the payment flow; TrustProof proves the trust decision that preceded it.

**Coinbase x402 Protocol** (`x402_payment_hash`): Links to an on-chain payment hash from the x402 HTTP payment protocol. Enables crypto-native agents to carry trust proofs alongside payment proofs.

**Google A2A Protocol** (`a2a_task_id`): Links to a task in Google's Agent-to-Agent protocol. When agents delegate work to other agents, the TrustProof chain extends across the delegation boundary.

**Anthropic MCP** (`mcp_tool_call_id`): Links to a specific tool invocation within an Anthropic Model Context Protocol session. Proves that a particular tool call was authorized by a trust decision.

**Proof Mesh** (`upstream_proof`): SHA-256 hash of an upstream TrustProof JWT from a different issuer or platform. Creates cross-platform attribution chains where multiple independent trust authorities contribute to a composite decision. See "Cross-Protocol Proof Mesh" below.

All `protocol_refs` fields are optional. Implementations SHOULD include only the references that are relevant to the specific action being recorded. The field allows `additionalProperties` for forward compatibility with future protocols.

---

## W3C Verifiable Credential Profile (v0.2)

The `vc_profile` field (optional) maps TrustProof claims to the [W3C Verifiable Credential Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/), enabling standard VC verifiers and wallets to understand TrustProofs.

### Field Mapping

| TrustProof Field | VC Data Model Field | Notes |
|---|---|---|
| `vc_profile.issuer_did` | `issuer` | DID of the TrustProof issuer |
| `vc_profile.subject_did` | `credentialSubject.id` | DID of the agent/actor |
| `subject.id` | `credentialSubject.agentId` | Platform-specific agent identifier |
| `action` | `credentialSubject.action` | The authorized operation |
| `result.decision` | `credentialSubject.trustDecision` | allow, deny, or step_up |
| `result.reason_codes` | `credentialSubject.reasonCodes` | Decision rationale |
| `timestamp` | `issuanceDate` | When the proof was created |
| `jti` | `id` | Unique credential identifier |
| `vc_profile.credential_type` | `type` | Always includes `VerifiableCredential` and `TrustProofCredential` |
| `vc_profile.delegation_did` | `credentialSubject.delegatedBy` | Human principal who delegated authority |
| The JWT itself | `proof` | EdDSA signature serves as the VC proof |

### DID Methods

TrustProof supports any DID method for `issuer_did`, `subject_did`, and `delegation_did`. Recommended methods:

- `did:web` — For organizations with web presence (e.g., `did:web:verdicto.dev`)
- `did:key` — For self-sovereign keys without infrastructure dependency

---

## Agent Framework Action Types (v0.2)

The `action` field remains a free-form string. For interoperability across agent frameworks, the following prefixes are recommended:

| Prefix | Framework | Example Actions |
|---|---|---|
| `checkout.` | Commerce | `checkout.purchase`, `checkout.refund` |
| `openclaw.` | OpenClaw/NemoClaw | `openclaw.claw_action`, `openclaw.tool_use`, `openclaw.file_access`, `openclaw.web_browse` |
| `langchain.` | LangChain | `langchain.tool_call`, `langchain.chain_step`, `langchain.llm_decision` |
| `crewai.` | CrewAI | `crewai.task_execution`, `crewai.delegation` |
| `autoresearch.` | autoresearch | `autoresearch.experiment`, `autoresearch.code_modification`, `autoresearch.evaluation` |
| `a2a.` | Google A2A | `a2a.agent_message`, `a2a.task_assignment` |
| `mcp.` | Anthropic MCP | `mcp.tool_invocation` |
| `payout.` | Financial | `payout.initiate`, `payout.approve` |

Custom prefixes are encouraged for domain-specific actions. Use dot notation for namespacing (e.g., `myplatform.custom_action`).

---

## Cross-Protocol Proof Mesh

The `upstream_proof` field in `protocol_refs` enables a "proof mesh" — a directed acyclic graph of TrustProofs from multiple independent issuers/platforms.

### How It Works

1. Platform A issues TrustProof `tp_a` for an agent action
2. Platform B receives `tp_a` as context, computes `sha256(tp_a_jwt)`, and stores it as `protocol_refs.upstream_proof` in its own TrustProof `tp_b`
3. An auditor can follow the chain: `tp_b.protocol_refs.upstream_proof` → hash matches `tp_a` JWT → verify `tp_a` independently

### Properties

- **No trust dependency**: Each TrustProof is independently verifiable. The upstream reference is a hash, not a signature delegation.
- **Tamper evidence**: Mutating `tp_a` after `tp_b` references it would break the hash linkage.
- **Cross-authority**: Different issuers can contribute to the same decision chain without sharing keys.

This enables audit trails that span organizational boundaries — e.g., a LangChain orchestrator issues a proof, which is referenced by a payment processor's proof, which is referenced by a merchant's fulfillment proof.

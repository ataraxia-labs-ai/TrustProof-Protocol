# TrustProof Protocol

<!-- markdownlint-disable MD033 -->

[![CI](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/%40trustproof%2Fsdk?label=%40trustproof%2Fsdk&color=3178c6)](https://www.npmjs.com/package/@trustproof/sdk)
[![PyPI](https://img.shields.io/pypi/v/trustproof?label=trustproof&color=3776ab)](https://pypi.org/project/trustproof/)
[![Spec Validated](https://img.shields.io/badge/spec-validated_(9_vectors)-brightgreen)](#quickstart)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![W3C CG](https://img.shields.io/badge/W3C-AI_Agent_Protocol_CG-purple)](https://www.w3.org/community/agentprotocol/)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-black)](https://ataraxia-labs-ai.github.io/TrustProof-Protocol/)

TrustProof Protocol defines **signed action receipts** — compact Ed25519/EdDSA JWTs that bind a subject, policy snapshot, action, hashed inputs/outputs, timestamp, jti, and tamper-evident chain. Interoperable with W3C Verifiable Credentials, Mastercard Verifiable Intent, Google AP2, and all major agent frameworks.

- **Protocol (OSS):** Schema + canonicalization + hashing + chain rules + golden vectors + SDKs + CLI
- **Enterprise layer (Verdicto):** KYH/KYA identity, policy engine, hosted verification, dashboards, webhooks, step-up UX, multi-tenant keys, SLAs

---

## What's New in v0.2

- **`protocol_refs`** — Link TrustProofs to external protocol artifacts: Mastercard Verifiable Intent, Google AP2 mandates, Stripe ACP sessions, Coinbase x402 payments, Google A2A tasks, Anthropic MCP tool calls, and upstream TrustProofs from other platforms (Proof Mesh)
- **`vc_profile`** — Map TrustProof claims to W3C Verifiable Credential Data Model 2.0 for interoperability with VC verifiers and wallets
- **Action type prefixes** — Recommended namespaced types for OpenClaw, LangChain, CrewAI, autoresearch, A2A, and MCP
- **Proof Mesh** — Multi-issuer chain verification: validate trust chains spanning multiple platforms, signing keys, and issuers
- **Golden vector `v006`** — Cross-protocol proof with VC profile validation
- **Timing-safe comparison** — All chain verification uses `hmac.compare_digest` (Python) to prevent side-channel attacks
- All new fields are **optional**. v0.1 proofs remain fully valid.

---

## Interop Protocols

TrustProof `protocol_refs` links to any agentic commerce protocol:

| Protocol | Field | Organization |
| --- | --- | --- |
| Verifiable Intent | `verifiable_intent_id` | Mastercard |
| AP2 Mandates | `ap2_mandate_id` | Google |
| A2A Tasks | `a2a_task_id` | Google |
| Agentic Commerce | `acp_checkout_id` | Stripe / OpenAI |
| x402 Payments | `x402_payment_hash` | Coinbase |
| MCP Tool Calls | `mcp_tool_call_id` | Anthropic |
| Upstream Proofs | `upstream_proof` | TrustProof Mesh |

---

## Quickstart

```bash
pnpm install
pnpm spec:validate
pnpm --filter @trustproof/sdk build
pnpm --filter @trustproof/sdk test
cd packages/py && python -m pytest -q && cd -
```

Generate and verify a proof:

```bash
node --input-type=module -e "
import {generateKeyPairSync} from 'node:crypto';
import fs from 'node:fs';
import {generate} from './packages/js/dist/index.js';
const c = JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8'));
const {privateKey, publicKey} = generateKeyPairSync('ed25519');
const priv = privateKey.export({format:'pem',type:'pkcs8'}).toString();
const pub = publicKey.export({format:'pem',type:'spki'}).toString();
const jwt = await generate(c, priv);
fs.writeFileSync('/tmp/tp.jwt', jwt);
fs.writeFileSync('/tmp/tp.pub.pem', pub);"

node packages/js/dist/cli.js inspect "$(cat /tmp/tp.jwt)"
node packages/js/dist/cli.js verify "$(cat /tmp/tp.jwt)" --pubkey /tmp/tp.pub.pem
```

## Playground (StackBlitz)

Run generate/verify/chain in-browser — no install required:

[Open in StackBlitz](https://stackblitz.com/github/ataraxia-labs-ai/TrustProof-Protocol/tree/main/examples/stackblitz)

---

## What it is / What it isn't

**What it is:**

- Stable claims envelope (JSON Schema)
- Deterministic canonicalization + hashing
- Tamper-evident chain rule
- Golden vectors to prevent SDK drift
- SDKs + CLI to generate/verify/inspect

**What it isn't:**

- Not KYC/KYB
- Not an IdP or auth provider
- Not hosted verification (that's [Verdicto](https://verdicto.dev))

---

## Verifier CLI

```bash
# TypeScript
node packages/js/dist/cli.js inspect "<jwt>"
node packages/js/dist/cli.js verify "<jwt>" --pubkey "<pem|b64|path>"

# Python
cd packages/py && python -m trustproof inspect "<jwt>"
cd packages/py && python -m trustproof verify "<jwt>" --pubkey "<pem|b64|path>"
```

---

## Test Suite

| Suite | Tests | Status |
| --- | --- | --- |
| TrustProof JS SDK | 43 | ✅ Pass |
| TrustProof Python SDK | 29 | ✅ Pass |
| **Total** | **72** | **✅ All Pass** |

Spec validation (separate from unit tests):

```text
PASS schema: spec/examples/allow.json
PASS schema: spec/examples/deny.json
PASS schema: spec/examples/step_up.json
PASS vector: spec/vectors/v001_allow_basic.json
PASS vector: spec/vectors/v002_deny_basic.json
PASS vector: spec/vectors/v003_stepup_basic.json
PASS vector: spec/vectors/v004_chain_linking.json
PASS vector: spec/vectors/v005_canonicalization_edge.json
PASS vector: spec/vectors/v006_vc_profile.json
```

---

## Protocol vs Verdicto Enterprise

| Scope | Includes |
| --- | --- |
| Protocol (OSS) | Schema, canonicalization rules, hash rules, chain rules, golden vectors, JS/Python SDKs, CLI verify/inspect |
| Enterprise (Verdicto) | Key management at scale, hosted verification, dashboards/logs, policy engine, webhooks, step-up UX, multi-tenant operations, SLA/compliance workflows |

Enterprise capabilities map to protocol primitives and are out of scope for the protocol definition.

---

## Repo Layout

```text
├── packages/
│   ├── js/          # @trustproof/sdk (TypeScript — generate/verify/chain + CLI)
│   └── py/          # trustproof (Python — generate/verify/chain + CLI)
├── spec/
│   ├── trustproof.schema.json
│   ├── examples/    # allow.json, deny.json, step_up.json
│   └── vectors/     # v001–v006 golden test vectors
├── integrations/    # LangChain, OpenClaw/NemoClaw, MCP, Autoresearch, OpenAI Agents
├── examples/        # Integration demos, StackBlitz playground
├── docs/            # Spec notes, security, demo runbook, decisions
└── .github/workflows/  # CI for JS, Python, and vector validation
```

---

## Protocol Artifacts

- Schema: [`spec/trustproof.schema.json`](spec/trustproof.schema.json)
- Examples: [`spec/examples/`](spec/examples/)
- Vectors: [`spec/vectors/`](spec/vectors/)

---

## Documentation

- [Protocol spec](docs/spec.md)
- [Security notes](docs/security.md)
- [Demo runbook](docs/demo_runbook.md)
- [Why now](docs/why-now.md)
- [LangChain integration](docs/integrations/langchain.md)
- [OpenAI Agents integration](docs/integrations/openai_agents.md)
- [Adoption guide](docs/adoption.md)
- [Docs site](https://ataraxia-labs-ai.github.io/TrustProof-Protocol/)

---

## Security & Correctness

- `pnpm spec:validate` enforces schema and golden vector consistency on every commit
- Mutate one byte in a signed JWT → verification fails (`INVALID_SIGNATURE` / `INVALID_PROOF`)
- Golden vectors lock canonicalization/hashing/chain behavior across both language SDKs
- Timing-safe hash comparison throughout the Python SDK (`hmac.compare_digest`)
- Protocol proofs use hashes/digests — raw PII payload storage is not required

---

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](../CONTRIBUTING.md).

Priority areas:

- New agent framework integrations (CrewAI, AutoGen, etc.)
- Additional `protocol_refs` bridge implementations
- W3C Verifiable Credentials interop testing
- Golden vector contributions

---

## License

Apache-2.0. Part of the [Ataraxia Labs](https://github.com/ataraxia-labs-ai) open-source ecosystem.

---

**Ataraxia Labs** · San Juan, Puerto Rico · [verdicto.dev](https://verdicto.dev) · [W3C AI Agent Protocol CG](https://www.w3.org/community/agentprotocol/) · [Docs](https://ataraxia-labs-ai.github.io/TrustProof-Protocol/)

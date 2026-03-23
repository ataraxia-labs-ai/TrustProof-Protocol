# Why Now

## Shift: Chat to Actions

Agents are moving from answering questions to executing real operations:

- initiate payouts
- approve internal workflows
- trigger infrastructure changes
- execute tool chains autonomously

Action systems need verifiable receipts, not only conversational transcripts.

## Logs Are Not Enough

Traditional logs are useful for debugging, but weak for portable trust:

- format varies by platform
- tamper detection is inconsistent
- replay and chain context are usually external
- third parties cannot reliably verify without full platform access

For high-risk operations, logs alone are insufficient for independent verification.

## Protocol Approach

TrustProof uses signed action receipts with deterministic verification:

- deterministic envelope schema
- canonicalization + hashing rules
- replay identifier (`jti`)
- tamper-evident chain (`prev_hash` / `entry_hash`)
- language parity via golden vectors

Any verifier with the public key can independently check signature and integrity.

## What This Enables

- Fintech payouts:
  prove how `allow` vs `step_up` decisions were produced.
- Enterprise approvals:
  carry signed evidence across systems, teams, and auditors.
- Agentic operations:
  chain tool actions with tamper-evident linkage for incident review.

## Practical Outcome

TrustProof keeps verification portable across execution platforms and organizations.

## The March 2026 Convergence

The agentic commerce ecosystem reached an inflection point in Q1 2026:

**Mastercard Verifiable Intent (March 5, 2026)**: Mastercard launched cryptographic purchase receipts — proof that a human authorized a specific transaction. This solves payment fraud for agent commerce but leaves a gap: who authorized the agent to act in the first place?

**Google AP2 Agent Payments Protocol (60+ partners)**: Google's Agent-to-Pay Protocol defines how agents request, approve, and execute payments with 60+ launch partners. AP2 handles payment authorization; it does not handle the trust decision that precedes payment.

**Coinbase Agentic Wallets (50M+ transactions)**: Coinbase's agent-native wallet infrastructure processes tens of millions of on-chain transactions. The x402 protocol handles crypto payments, but agent authorization remains application-specific.

**Nvidia NemoClaw / OpenClaw**: Nvidia's open-source agent sandboxing framework (NemoClaw, now OpenClaw) provides runtime guardrails — file access, network calls, tool invocation. OpenClaw handles what an agent *can* do. TrustProof proves what an agent *was allowed to do* and records the outcome.

**Karpathy's autoresearch (42K stars)**: Andrej Karpathy's autonomous research agent demonstrated that complex, multi-step agent workflows need more than logging — they need cryptographic audit trails that survive across sessions and organizations.

### Where TrustProof v0.2 Fits

AP2 handles payment authorization. Verifiable Intent handles purchase proof. NemoClaw handles agent sandboxing. TrustProof handles everything else — the 99% of agent actions that are not payments.

TrustProof v0.2 is the universal trust layer that connects these protocols:

- `protocol_refs.verifiable_intent_id` → links to Mastercard's payment proof
- `protocol_refs.ap2_mandate_id` → links to Google's payment mandate
- `protocol_refs.x402_payment_hash` → links to Coinbase's on-chain proof
- `protocol_refs.mcp_tool_call_id` → links to Anthropic's tool invocations
- `protocol_refs.upstream_proof` → links to other TrustProofs across platforms

The result: a single, verifiable receipt that proves an agent was authorized to act, what it did, and how that action connects to payment authorizations, tool calls, and other protocol artifacts across the entire agent commerce stack.

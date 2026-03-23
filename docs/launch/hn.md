# Show HN Draft

## Title

Show HN: TrustProof Protocol — signed action receipts for AI agents (Ed25519 JWT + tamper-evident chain)

## Body

Agents are moving from chat responses to real-world actions (payouts, approvals, tool execution). In that model, logs are useful but not sufficient as portable evidence. We wanted a minimal protocol artifact that can be verified offline and shared across systems.

TrustProof Protocol defines signed action receipts: claims envelopes signed as Ed25519 JWTs with deterministic canonicalization/hash rules and optional tamper-evident chaining. The repo includes schema, examples, golden vectors, JS/Python SDKs, and CLI verification commands.

Try it locally (no API keys):

```bash
pnpm install
pnpm spec:validate
pnpm --filter @trustproof/sdk example:payout-stepup
pnpm --filter @trustproof/sdk example:agent-actions
```

Links:

- Repo: https://github.com/ataraxia-labs-ai/TrustProof-Protocol
- Docs (GitHub Pages): https://ataraxia-labs-ai.github.io/TrustProof-Protocol/
- Demo runbook: https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/docs/demo_runbook.md

Feedback welcome on:

- naming (`signed action receipts`, field names)
- required/optional spec fields
- chain rule (`entry_hash = sha256(prev_hash + canonical_event_material)`)
- integration surface (LangChain/OpenAI Agents hooks)

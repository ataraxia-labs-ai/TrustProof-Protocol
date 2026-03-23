# X Thread Draft (10 Tweets)

## 1/10

AI agents need receipts, not just logs.  
TrustProof Protocol is OSS for **signed action receipts** (Ed25519 JWT + tamper-evident chain).  
Repo: https://github.com/ataraxia-labs-ai/TrustProof-Protocol  
[screenshot: README + protocol definition]

## 2/10

Protocol invariants are executable, not implied.  
Run:

```bash
pnpm spec:validate
```

You should see schema + vector passes.

## 3/10

Golden vectors pin canonicalization/hash/chain behavior across implementations.  
Verifiable claim: same vectors validate in JS + Python test suites.  
[screenshot: PASS vector lines]

## 4/10

Tamper evidence demo: mutate one byte in a signed JWT, verification fails deterministically (`❌ Not Verified`).  
Not “best effort logging,” actual signature + integrity checks.

## 5/10

Run payout step-up flow (offline):

```bash
pnpm --filter @trustproof/sdk example:payout-stepup
```

Outputs land in `examples/output/payout_stepup/` with proofs + summary.

## 6/10

Run agent tool-action flow:

```bash
pnpm --filter @trustproof/sdk example:agent-actions
```

Includes chain verification + tamper failure path.

## 7/10

CLI verifier UX is direct:

```bash
node packages/js/dist/cli.js verify "<jwt>" --pubkey "<pem|path|b64>"
node packages/js/dist/cli.js inspect "<jwt>"
```

Valid proof prints `✅ Verified`.

## 8/10

LangChain integration is thin: wrap tool invocation -> emit proof JWT.  
Command:

```bash
pnpm --filter @trustproof/sdk example:langchain
```

## 9/10

OpenAI Agents adapter is SDK-agnostic: action/tool hooks -> proof chain.  
Command:

```bash
pnpm --filter @trustproof/sdk example:openai-agents
```

## 10/10

Docs + runbook:

- https://ataraxia-labs-ai.github.io/TrustProof-Protocol/
- https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/docs/demo_runbook.md

If this is useful, star the repo and share feedback on spec fields, chain rule, and integrations.

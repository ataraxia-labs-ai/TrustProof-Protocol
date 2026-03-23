# TrustProof Protocol: signed action receipts for AI agents

Agents are no longer only generating text. They are initiating payouts, calling tools, approving changes, and triggering workflows. As soon as agents execute actions, teams need evidence that can survive beyond one platform’s log format.

TrustProof Protocol is an OSS protocol for **signed action receipts**. A receipt is a claims envelope signed as an Ed25519 JWT, with deterministic hashing rules and optional tamper-evident chaining.

This post explains the protocol in practical terms, shows why vectors matter, and gives runnable commands you can execute locally without API keys.

## Why agents need receipts

For action systems, logs are necessary but often not sufficient:

- Log formats vary by vendor and pipeline.
- Integrity guarantees differ by stack.
- Third-party verification is hard without internal access.
- Replay/tamper assumptions are frequently implicit.

If an action is high-impact (for example a payout or production operation), teams need portable verification artifacts, not only internal observability events.

That is the gap TrustProof targets.

## What is a signed action receipt

A TrustProof receipt is:

- a JSON claims envelope
- signed as JWT/JWS using Ed25519 (`alg=EdDSA`)
- verifiable offline with a public key

The envelope binds:

- `subject` (who acted)
- `action` + `resource` (what happened)
- `policy` snapshot (decision context)
- `result` (allow/deny/step_up + reason codes)
- `hashes` (`input_hash`, `output_hash`)
- `timestamp`, `jti` (replay identity), `chain` (tamper-evident linkage)

Reference schema:

- https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/spec/trustproof.schema.json

## Spec + golden vectors (why it matters)

The protocol defines canonicalization, hashing, and chain rules. Those rules are enforced by golden vectors in the repo.

Why this matters:

- Cross-language implementations can drift in subtle ways (key ordering, whitespace, encoding, hash material shape).
- Vectors make those differences explicit and testable.
- CI can fail fast when a “small” change breaks deterministic behavior.

Run spec validation:

```bash
pnpm spec:validate
```

You should see schema and vector pass lines ending in:

`All spec validations passed.`

Reference docs:

- Protocol docs (Pages): https://ataraxia-labs-ai.github.io/TrustProof-Protocol/
- Spec notes: https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/docs/spec.md
- Vector definitions: https://github.com/ataraxia-labs-ai/TrustProof-Protocol/tree/main/spec/vectors

## Quickstart

Clone and run:

```bash
git clone https://github.com/ataraxia-labs-ai/TrustProof-Protocol.git
cd TrustProof-Protocol
pnpm install
pnpm spec:validate
pnpm --filter @trustproof/sdk build
pnpm --filter @trustproof/sdk test
cd packages/py && python -m pytest -q && cd -
```

No API keys are required for these flows.

## Example flows

### 1) Payout step-up flow

```bash
pnpm --filter @trustproof/sdk example:payout-stepup
```

This generates receipts for:

- low-risk payout => `allow`
- high-risk payout => `step_up`
- follow-up `payout.step_up.approve` => chained `allow`

Artifacts are written under:

- `examples/output/payout_stepup/proofs.json`
- `examples/output/payout_stepup/summary.txt`

### 2) Agent actions flow

```bash
pnpm --filter @trustproof/sdk example:agent-actions
```

This simulates two tool calls (`payout.quote`, `payout.initiate`), verifies chain linkage, and runs a tamper check.

Artifacts are written under:

- `examples/output/agent_actions/proofs.json`
- `examples/output/agent_actions/summary.txt`

## CLI verifier UX

The protocol includes a CLI verifier and inspector.

Generate a local demo JWT + public key:

```bash
node --input-type=module -e "import {generateKeyPairSync} from 'node:crypto'; import fs from 'node:fs'; import {generate} from './packages/js/dist/index.js'; const claims=JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8')); const {privateKey,publicKey}=generateKeyPairSync('ed25519'); const priv=privateKey.export({format:'pem',type:'pkcs8'}).toString(); const pub=publicKey.export({format:'pem',type:'spki'}).toString(); const jwt=await generate(claims,priv); fs.mkdirSync('./examples/output/demo',{recursive:true}); fs.writeFileSync('./examples/output/demo/demo.jwt',jwt); fs.writeFileSync('./examples/output/demo/demo.pub.pem',pub);"
```

Verify and inspect:

```bash
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
node packages/js/dist/cli.js inspect "$(cat examples/output/demo/demo.jwt)"
```

Expected:

- valid receipt => `✅ Verified`
- inspect => decoded claims JSON

Tamper check:

```bash
node -e "const fs=require('fs'); const t=fs.readFileSync('examples/output/demo/demo.jwt','utf8').trim(); const p=t.split('.'); const s=p[2]; const i=Math.min(10,s.length-1); const r=s[i]==='a'?'b':'a'; p[2]=s.slice(0,i)+r+s.slice(i+1); fs.writeFileSync('examples/output/demo/demo.tampered.jwt',p.join('.'));"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.tampered.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

Expected:

- `❌ Not Verified`
- `INVALID_SIGNATURE`

## What’s next

Protocol scope today is clear: schema, vectors, deterministic verification rules, SDKs, and CLI.

Natural next layers on top of protocol primitives:

- webhook delivery of receipt events
- enterprise verifier deployment patterns
- stronger replay/idempotency integrations
- step-up UX patterns for human approval loops

If you want to review or adopt it, start from the runbook:

- https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/docs/demo_runbook.md

And protocol docs:

- https://ataraxia-labs-ai.github.io/TrustProof-Protocol/

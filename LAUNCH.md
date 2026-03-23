# TrustProof Protocol Launch Plan

## Launch Goal

Ship TrustProof Protocol as an OSS standard for signed action receipts: Ed25519-signed JWT artifacts with deterministic verification and tamper-evident chain linkage.

Desired outcome:

- Builders can run the protocol end-to-end in under 5 minutes.
- Security/infra reviewers can validate concrete proof points from commands and vectors.

## Target Audiences

- AI/agent builders integrating action-level verification
- Security engineers defining audit and replay controls
- Fintech/risk teams handling payout/approval decisions
- Platform teams building policy + tooling around agent actions

## Assets Checklist

- [x] Root docs and quickstart: [`README.md`](README.md)
- [x] Spec + schema + vectors:
  - [`docs/spec.md`](docs/spec.md)
  - [`spec/trustproof.schema.json`](spec/trustproof.schema.json)
  - [`spec/vectors/`](spec/vectors/)
- [x] Security notes: [`docs/security.md`](docs/security.md)
- [x] Demo runbook: [`docs/demo_runbook.md`](docs/demo_runbook.md)
- [x] Demo video script: [`docs/demo_video_script.md`](docs/demo_video_script.md)
- [x] Integration docs:
  - [`docs/integrations/langchain.md`](docs/integrations/langchain.md)
  - [`docs/integrations/openai_agents.md`](docs/integrations/openai_agents.md)
- [x] StackBlitz playground:
  - https://stackblitz.com/github/ataraxia-labs-ai/TrustProof-Protocol/tree/main/examples/stackblitz
- [x] GitHub Pages docs:
  - https://ataraxia-labs-ai.github.io/TrustProof-Protocol/

## Release Steps

1. Confirm pre-launch checks:
   - `pnpm spec:validate`
   - `pnpm --filter @trustproof/sdk build`
   - `pnpm --filter @trustproof/sdk example:payout-stepup`
   - `pnpm --filter @trustproof/sdk example:agent-actions`
2. Update release references:
   - Ensure [`CHANGELOG.md`](CHANGELOG.md) has current release notes.
   - Ensure [`README.md`](README.md) and [`docs/demo_runbook.md`](docs/demo_runbook.md) match runnable commands.
3. Tag release:
   - `git tag -a v0.1.0 -m "TrustProof Protocol v0.1.0"`
   - `git push origin v0.1.0`
4. Publish GitHub Release:
   - Title: `v0.1.0`
   - Notes source: [`CHANGELOG.md`](CHANGELOG.md) + launch proof points below.
5. Post launch content in schedule order.

## Posting Schedule

1. X thread (first)
2. Show HN
3. Dev.to post
4. LinkedIn post (optional short adaptation)

## Proof Points

- Spec + vectors are executable:
  - `pnpm spec:validate` => schema and vectors pass.
- Canonicalization/hash/chain behavior is locked by golden vectors.
- Tamper evidence is demonstrable:
  - mutate one byte in JWT => verify fails (`❌ Not Verified` / `INVALID_SIGNATURE`).
- CLI verifier UX is concrete:
  - `verify` prints `✅ Verified` for valid proofs.
  - `inspect` shows decoded claims payload.
- Example flows are runnable offline:
  - `example:payout-stepup` and `example:agent-actions` write artifacts to `examples/output/`.

## FAQ

### Why a protocol instead of a platform log format?

Protocol artifacts are portable and independently verifiable with public keys, schema, and vectors.

### Why JWT?

JWT/JWS gives a standard compact signed envelope format with broad ecosystem support.

### How do I verify offline?

Use the public key + verifier:

- `node packages/js/dist/cli.js verify "<jwt>" --pubkey "<pem|path|b64>"`
- or Python CLI equivalent.

### How does enterprise map to OSS protocol?

Enterprise capabilities (hosted verification, key management at scale, policy engine, dashboards, SLA/compliance) map to protocol primitives and are out of scope for the protocol specification itself.

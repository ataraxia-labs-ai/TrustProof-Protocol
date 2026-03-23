# TrustProof Pilot Pack

This guide is for running a focused pilot with TrustProof Protocol in a production-like workflow.

## 1) Who This Pilot Is For

Use this pilot if you need verifiable receipts for action execution, especially:

- fintech payout actions
- high-risk approval workflows
- agent tool-call actions with audit requirements

## 2) What Gets Integrated

At minimum, integrate two points:

1. At action completion: call `generate(...)` (or `append(...)` for chained flows) to issue a proof JWT.
2. At control/audit boundary: call `verify(...)` (and `verifyChain(...)` where applicable).

Store proof artifacts in your existing event/audit store (or a dedicated proof table).

## 3) Pilot Data Model (Recommended Fields)

Log these fields per action receipt:

- `proof_jwt`
- `subject.type`, `subject.id`
- `action`
- `resource.type`, `resource.id`
- `result.decision`
- `jti`
- `timestamp`
- `chain.prev_hash`
- `chain.entry_hash`

Optional metrics fields:

- `verify_ok`
- `verify_error_codes[]`
- `replay_detected` (if replay store is enabled)

## 4) Operational Plan

### Scope (start narrow)

- Start with one action type only (example: `payout.initiate`).
- Use fixed policy constraints for pilot consistency.

### Success Metrics

Track at least:

- verification success rate (`verify_ok / total proofs`)
- `step_up` rate for scoped actions
- replay hits (`jti` duplicates) and resolution time

### Rollout Stages

1. Shadow mode:
   - Generate/store proofs.
   - Verify asynchronously.
   - Do not block requests on verify failures yet.
2. Enforced mode:
   - Gate downstream processing on `verify_ok`.
   - Optionally require valid chain linkage for multi-step flows.

## 5) Enterprise Mapping (Verdicto, Neutral)

Protocol scope (OSS):

- schema + vectors
- canonicalization/hash/chain rules
- SDK generate/verify/append/verifyChain
- local CLI verification

Maps to Verdicto (out of scope for protocol core):

- hosted verifier operations
- policy engine orchestration
- dashboards and log export pipelines
- webhook delivery surface
- multi-tenant key lifecycle tooling
- step-up user experience flows

## 6) Security Notes for Pilot

### Key management and rotation

- Use Ed25519 keys.
- Include `kid` in JWT header when rotating.
- Keep old public keys available until proof retention/expiry window closes.

### Replay handling

- `jti` is required.
- Maintain a replay store keyed by `(tenant, action, jti)` with TTL.
- Set TTL to cover retry windows and audit expectations.

### Size limits and data minimization

- Enforce max payload/proof size at ingestion and verification boundaries.
- Prefer logging hashes + metadata, not raw sensitive input/output.
- Avoid storing direct PII in claims unless operationally required.

## 7) Pilot Execution Commands (Local Baseline)

Run from clean clone:

```bash
pnpm install
pnpm spec:validate
pnpm --filter @trustproof/sdk build
pnpm --filter @trustproof/sdk example:payout-stepup
pnpm --filter @trustproof/sdk example:agent-actions
cd packages/py && python -m pytest -q
```

Reference docs:

- Runbook: [docs/demo_runbook.md](./demo_runbook.md)
- Spec guide: [docs/spec.md](./spec.md)
- Protocol docs: <https://ataraxia-labs-ai.github.io/TrustProof-Protocol/>

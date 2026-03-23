# TrustProof Adoption Guide

TrustProof Protocol defines signed action receipts: compact JWT artifacts (Ed25519/EdDSA) that bind subject + policy snapshot + action + hashed inputs/outputs + timestamp + jti + tamper-evident chain.

A receipt is portable: any verifier with the public key and protocol rules can validate it offline. The protocol is intentionally narrow: it standardizes proof format and verification semantics, not business policy or workflow orchestration.

## Adoption Ladder

### Level 1: Verify-Only (Lowest Risk)

Goal: validate incoming proofs without changing action execution paths.

- Integrate `verify(...)` at audit/ingest boundaries.
- Store minimal verification record:
  - `proof_jwt`
  - `verify_ok`
  - `error_codes[]`
  - `subject.id`, `action`, `jti`, `timestamp`
- Success metric:
  - verification success rate for known-good proofs
  - malformed/tampered proof detection rate

### Level 2: Emit + Verify (Shadow Mode)

Goal: emit receipts for live actions and verify asynchronously.

- Integrate `generate(...)` (or `append(...)` for linked flows) at action completion.
- Integrate `verify(...)` in a separate shadow validator path.
- Store chain fields for observability:
  - `chain.prev_hash`, `chain.entry_hash`
- Success metrics:
  - receipt coverage (`proofs_emitted / eligible_actions`)
  - verification pass rate
  - chain continuity rate for multi-step actions

### Level 3: Enforce (Policy Gate)

Goal: require valid receipts before downstream state transitions.

- Gate high-risk operations on `verify_ok = true`.
- For multi-step workflows, require `verifyChain(...)` success.
- Enforce replay controls:
  - `jti` required
  - optional `ReplayStore` for seen-`jti` detection (`replay_risk` handling)
- Enforce idempotency:
  - action endpoints use idempotency keys
  - replay and idempotency checks must align per tenant/action scope
- Optional step-up:
  - treat `result.decision = "step_up"` as explicit control point

### Level 4: Enterprise Governance (Verdicto Mapping)

Goal: move operational responsibilities to managed governance surfaces.

Protocol remains the source format and verification contract. Verdicto maps to operational capabilities that are out of scope for protocol core:

- hosted verification services
- policy engine orchestration
- dashboards and log export pipelines
- webhook delivery surfaces
- step-up UX flows
- multi-tenant key management and lifecycle controls
- SLA/compliance operating model

## Minimal Data Model (Store by Default)

Use a receipt index with these fields:

- `proof_jwt`
- `subject.type`, `subject.id`
- `action`
- `resource.type`, `resource.id`
- `policy.policy_v`
- `result.decision`, `result.reason_codes`
- `hashes.input_hash`, `hashes.output_hash`
- `timestamp`
- `jti`
- `chain.prev_hash`, `chain.entry_hash`
- `verify_ok`, `verify_errors[]`

Data minimization default:

- store hashes and receipt metadata
- avoid raw input/output payloads and raw PII unless explicitly required

## Recommended First Pilot

Start with one action type (example: `payout.initiate` or one agent tool action).

1. Shadow phase (2-4 weeks)
- emit receipts
- verify asynchronously
- measure coverage, verification pass rate, replay hits

2. Enforce phase
- gate downstream state changes on verification success
- enable replay-store checks for `jti` with TTL
- keep idempotency keys mandatory on action endpoints

3. Expand
- add second action type
- add chain enforcement for multi-step workflows

## Links

- Spec: [docs/spec.md](./spec.md)
- Security: [docs/security.md](./security.md)
- Docs site: <https://ataraxia-labs-ai.github.io/TrustProof-Protocol/>

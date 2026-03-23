# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-21

### Added
- `protocol_refs` field for cross-protocol linking (Verifiable Intent, AP2, ACP, x402, A2A, MCP, Proof Mesh)
- `vc_profile` field for W3C Verifiable Credential Data Model 2.0 compatibility
- Recommended action type prefixes for OpenClaw, LangChain, CrewAI, autoresearch, A2A, MCP
- Golden vector `v006_vc_profile.json` testing cross-protocol proof with VC profile
- Cross-protocol example: `spec/examples/cross_protocol.json`
- Documentation: Protocol References, VC Profile mapping, Agent Framework Action Types, Proof Mesh
- Updated `why-now.md` with March 2026 market context (Verifiable Intent, AP2, NemoClaw, autoresearch)

### Changed
- None (backwards-compatible additions only)

### Breaking
- None (all new fields are optional, v0.1 proofs remain valid)

## [0.1.0] - 2026-02-25
### Added
- Spec v1 claims envelope schema at `spec/trustproof.schema.json`.
- Spec examples (`allow`, `deny`, `step_up`) and golden vectors in `spec/vectors/`.
- Spec validator workflow via `pnpm spec:validate`.
- JS SDK core for `generate`, `verify`, `append`, and `verifyChain`.
- Python SDK parity for `generate`, `verify`, `append`, and `verify_chain`.
- Node and Python CLI v0 commands for `verify` and `inspect`.
- Reproducible example suites:
  - `pnpm --filter @trustproof/sdk example:payout-stepup`
  - `pnpm --filter @trustproof/sdk example:agent-actions`

### Security
- Tamper-evident chain verification in JS and Python workflows.
- Deterministic canonicalization + hashing rules backed by cross-language vectors.

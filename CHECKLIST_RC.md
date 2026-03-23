# TrustProof Protocol v0.1.0 Release Candidate Checklist

This checklist prepares a release candidate and verifies reproducibility from a clean clone.
It does not publish tags or releases.

## 1) Pre-flight

- [ ] Working tree is clean: `git status --short`
- [ ] CI is green on target commit (push + pull_request workflows)
- [ ] Version files are `0.1.0`:
  - [ ] `packages/js/package.json`
  - [ ] `packages/py/pyproject.toml`
  - [ ] `package.json` (root, if used)
- [ ] `CHANGELOG.md` includes `[0.1.0]` with date `2026-02-25` and release highlights
- [ ] Docs site reachable: <https://ataraxia-labs-ai.github.io/TrustProof-Protocol/>

## 2) Clean-Clone Verification (Executable)

```bash
git clone https://github.com/ataraxia-labs-ai/TrustProof-Protocol.git
cd TrustProof-Protocol
pnpm install
```

Expected key output (short): dependency install succeeds.

## 3) Protocol Contract Checks (Schema + Vectors)

```bash
pnpm spec:validate
```

Expected key output (short):

- `PASS schema: ...`
- `PASS vector: ...`
- `All spec validations passed.`

## 4) SDK Checks

JS build:

```bash
pnpm --filter @trustproof/sdk build
```

JS tests:

```bash
pnpm --filter @trustproof/sdk test
```

Python tests:

```bash
cd packages/py && python -m pytest -q
cd ../..
```

Expected key output (short): build/test suites succeed.

## 5) Examples Checks

```bash
pnpm --filter @trustproof/sdk example:payout-stepup
pnpm --filter @trustproof/sdk example:agent-actions
```

Expected key output (short):

- `✅ Verified ...`
- `✅ Tamper => OK (failed as expected)`

Expected files created:

- `examples/output/payout_stepup/proofs.json`
- `examples/output/payout_stepup/summary.txt`
- `examples/output/agent_actions/proofs.json`
- `examples/output/agent_actions/summary.txt`

## 6) Verifier UX Checks (CLI)

### 6.1 Generate demo JWT + public key (local only)

```bash
node --input-type=module -e "import {generateKeyPairSync} from 'node:crypto'; import fs from 'node:fs'; import {generate} from './packages/js/dist/index.js'; const claims=JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8')); const {privateKey,publicKey}=generateKeyPairSync('ed25519'); const priv=privateKey.export({format:'pem',type:'pkcs8'}).toString(); const pub=publicKey.export({format:'pem',type:'spki'}).toString(); const jwt=await generate(claims,priv); fs.mkdirSync('./examples/output/demo',{recursive:true}); fs.writeFileSync('./examples/output/demo/demo.jwt',jwt); fs.writeFileSync('./examples/output/demo/demo.pub.pem',pub);"
```

### 6.2 Verify + inspect

```bash
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
node packages/js/dist/cli.js inspect "$(cat examples/output/demo/demo.jwt)"
```

Expected key output (short):

- verify starts with `✅ Verified`
- inspect prints decoded claims JSON

### 6.3 Tamper one byte and verify fails

```bash
node -e "const fs=require('fs'); const t=fs.readFileSync('examples/output/demo/demo.jwt','utf8').trim(); const p=t.split('.'); const s=p[2]; const i=Math.min(10,s.length-1); const r=s[i]==='a'?'b':'a'; p[2]=s.slice(0,i)+r+s.slice(i+1); fs.writeFileSync('examples/output/demo/demo.tampered.jwt',p.join('.'));"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.tampered.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

Expected key output (short):

- verify starts with `❌ Not Verified`
- error includes `INVALID_SIGNATURE`

## 7) Docs Checks (Manual)

- [ ] `README.md` quickstart commands run as written
- [ ] `docs/demo_runbook.md` commands and expected outputs are accurate
- [ ] `docs/spec.md` links resolve (`../spec/trustproof.schema.json`, `../spec/examples/`, `../spec/vectors/`)
- [ ] `docs/security.md` aligns with current API names (`generate`, `verify`, `append`, `verifyChain`)
- [ ] Pages docs index resolves: <https://ataraxia-labs-ai.github.io/TrustProof-Protocol/>

## 8) Release Steps (Document Only, Do Not Run in This PR)

### Tag commands

```bash
git tag -a v0.1.0 -m "TrustProof Protocol v0.1.0"
git push origin v0.1.0
```

### GitHub Release Draft Template

```md
## TrustProof Protocol v0.1.0

Signed action receipts protocol release (Ed25519 JWT + deterministic hash/chain rules).

### Included
- Spec v1 schema + examples + golden vectors
- JS/Python SDK parity for generate/verify/append/verifyChain
- CLI verify/inspect UX
- Reproducible examples: payout step-up + agent actions

### Verification Commands
- `pnpm install`
- `pnpm spec:validate`
- `pnpm --filter @trustproof/sdk build`
- `pnpm --filter @trustproof/sdk test`
- `pnpm --filter @trustproof/sdk example:payout-stepup`
- `pnpm --filter @trustproof/sdk example:agent-actions`
- `cd packages/py && python -m pytest -q`
```

## 9) Go / No-Go Criteria

Go only if all are true:

- [ ] Clean-clone commands succeed without local edits
- [ ] Protocol contract checks pass (`pnpm spec:validate`)
- [ ] JS build + tests pass
- [ ] Python tests pass
- [ ] CLI verifier shows `✅ Verified` for known-good token
- [ ] Tampered token check returns `❌ Not Verified`
- [ ] Example outputs are generated under `examples/output/`
- [ ] Version/changelog state matches `v0.1.0`

No-Go if any protocol contract, verification, tamper, or reproducibility check fails.

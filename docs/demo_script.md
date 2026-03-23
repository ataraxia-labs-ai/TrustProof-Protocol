# TrustProof Demo Script (Final)

This script is aligned to [docs/demo_runbook.md](./demo_runbook.md) and uses only local/offline commands.

## Version A (90 seconds)

### Goal
Show three proof points quickly:
1) spec/vectors contract is green, 2) verifier UX returns `✅ Verified`, 3) tampering fails verification.

### On-screen flow
- Terminal split: left = commands, right = outputs.
- Keep `examples/output/` visible in editor sidebar.

### Sequence

1. Hook (0:00-0:05)
- Talk: "TrustProof defines signed action receipts for actions, not just logs."

2. Spec + vectors (0:05-0:20)

```bash
pnpm spec:validate
```

Expected output cue:
- `PASS schema: ...`
- `PASS vector: ...`

3. Build + examples (0:20-0:45)

```bash
pnpm --filter @trustproof/sdk build
pnpm --filter @trustproof/sdk example:payout-stepup
pnpm --filter @trustproof/sdk example:agent-actions
```

Then show:

```bash
cat examples/output/agent_actions/summary.txt
```

Expected output cue:
- `✅ Verified chain ...`
- `✅ Tamper => OK (failed as expected)`

4. Verifier UX (0:45-1:15)

Generate demo JWT + public key:

```bash
node --input-type=module -e "import {generateKeyPairSync} from 'node:crypto'; import fs from 'node:fs'; import {generate} from './packages/js/dist/index.js'; const claims=JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8')); const {privateKey,publicKey}=generateKeyPairSync('ed25519'); const priv=privateKey.export({format:'pem',type:'pkcs8'}).toString(); const pub=publicKey.export({format:'pem',type:'spki'}).toString(); const jwt=await generate(claims,priv); fs.mkdirSync('./examples/output/demo',{recursive:true}); fs.writeFileSync('./examples/output/demo/demo.jwt',jwt); fs.writeFileSync('./examples/output/demo/demo.pub.pem',pub);"
```

Verify + inspect:

```bash
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
node packages/js/dist/cli.js inspect "$(cat examples/output/demo/demo.jwt)"
```

Expected output cue:
- verify starts with `✅ Verified`

5. Tamper check (1:15-1:25)

```bash
node -e "const fs=require('fs'); const t=fs.readFileSync('examples/output/demo/demo.jwt','utf8').trim(); const p=t.split('.'); const s=p[2]; const i=Math.min(10,s.length-1); const r=s[i]==='a'?'b':'a'; p[2]=s.slice(0,i)+r+s.slice(i+1); fs.writeFileSync('examples/output/demo/demo.tampered.jwt',p.join('.'));"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.tampered.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

Expected output cue:
- starts with `❌ Not Verified`

6. Close (1:25-1:30)
- Talk: "Vectors pass, valid proofs verify, and one-byte tampering fails."

---

## Version B (2–3 minutes)

### Goal
Show contract validation, proof generation, chain verification, tamper evidence, and Python parity.

### Segment 1: Contract first (0:00-0:35)

```bash
pnpm spec:validate
```

Talk:
- "Schema + vectors are the protocol contract."

Expected output cue:
- pass for examples and vectors

### Segment 2: Build and run examples (0:35-1:20)

```bash
pnpm --filter @trustproof/sdk build
pnpm --filter @trustproof/sdk example:payout-stepup
pnpm --filter @trustproof/sdk example:agent-actions
```

Show:

```bash
cat examples/output/payout_stepup/summary.txt
cat examples/output/agent_actions/summary.txt
```

Talk:
- "Payout shows allow + step_up receipts."
- "Agent actions show chain linking and tamper failure."

### Segment 3: CLI verify/inspect UX (1:20-2:05)

```bash
node --input-type=module -e "import {generateKeyPairSync} from 'node:crypto'; import fs from 'node:fs'; import {generate} from './packages/js/dist/index.js'; const claims=JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8')); const {privateKey,publicKey}=generateKeyPairSync('ed25519'); const priv=privateKey.export({format:'pem',type:'pkcs8'}).toString(); const pub=publicKey.export({format:'pem',type:'spki'}).toString(); const jwt=await generate(claims,priv); fs.mkdirSync('./examples/output/demo',{recursive:true}); fs.writeFileSync('./examples/output/demo/demo.jwt',jwt); fs.writeFileSync('./examples/output/demo/demo.pub.pem',pub);"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
node packages/js/dist/cli.js inspect "$(cat examples/output/demo/demo.jwt)"
```

Expected output cue:
- `✅ Verified`
- decoded claims JSON

### Segment 4: Tamper + Python parity (2:05-2:45)

```bash
node -e "const fs=require('fs'); const t=fs.readFileSync('examples/output/demo/demo.jwt','utf8').trim(); const p=t.split('.'); const s=p[2]; const i=Math.min(10,s.length-1); const r=s[i]==='a'?'b':'a'; p[2]=s.slice(0,i)+r+s.slice(i+1); fs.writeFileSync('examples/output/demo/demo.tampered.jwt',p.join('.'));"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.tampered.jwt)" --pubkey examples/output/demo/demo.pub.pem
cd packages/py && python -m pytest -q
```

Expected output cue:
- `❌ Not Verified` on tampered token
- Python tests pass

### Close (2:45-3:00)
- Show docs site: <https://ataraxia-labs-ai.github.io/TrustProof-Protocol/>
- Talk: "Feedback requested on fields, chain semantics, and integration coverage."

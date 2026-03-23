# TrustProof Demo Video Script

## Version 1 (90 seconds)

### Hook (0:00-0:05)

AI agents need receipts.

### Beat 1: Spec + vectors (0:05-0:25)

Narration:

"TrustProof is a protocol for signed action receipts.  
First, I validate schema and golden vectors."

Command:

```bash
pnpm spec:validate
```

On screen:

- `PASS schema ...`
- `PASS vector ...`
- `All spec validations passed.`

### Beat 2: Generate proof + verify (0:25-0:55)

Narration:

"Now I generate a proof locally and verify it offline with a public key."

Commands:

```bash
pnpm --filter @trustproof/sdk build
node --input-type=module -e "import {generateKeyPairSync} from 'node:crypto'; import fs from 'node:fs'; import {generate} from './packages/js/dist/index.js'; const claims=JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8')); const {privateKey,publicKey}=generateKeyPairSync('ed25519'); const priv=privateKey.export({format:'pem',type:'pkcs8'}).toString(); const pub=publicKey.export({format:'pem',type:'spki'}).toString(); const jwt=await generate(claims,priv); fs.mkdirSync('./examples/output/demo',{recursive:true}); fs.writeFileSync('./examples/output/demo/demo.jwt',jwt); fs.writeFileSync('./examples/output/demo/demo.pub.pem',pub);"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

On screen:

- `✅ Verified`

### Beat 3: Chain + tamper failure (0:55-1:20)

Narration:

"Next, chain verification and tamper detection."

Commands:

```bash
pnpm --filter @trustproof/sdk example:agent-actions
node -e "const fs=require('fs'); const t=fs.readFileSync('examples/output/demo/demo.jwt','utf8').trim(); const p=t.split('.'); const s=p[2]; const i=Math.min(10,s.length-1); const r=s[i]==='a'?'b':'a'; p[2]=s.slice(0,i)+r+s.slice(i+1); fs.writeFileSync('examples/output/demo/demo.tampered.jwt',p.join('.'));"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.tampered.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

On screen:

- `✅ Tamper => OK (failed as expected)` (from example)
- `❌ Not Verified` (from tampered token verification)

### Close (1:20-1:30)

Narration:

"Next steps are webhooks, enterprise verifier deployment, and step-up UX on top of the same protocol.  
Repo: github.com/ataraxia-labs-ai/TrustProof-Protocol."

---

## Version 2 (2-3 minutes)

### Hook (0:00-0:05)

AI agents need receipts.

### Intro (0:05-0:25)

Narration:

"TrustProof defines signed action receipts: JWT proofs that bind subject, action, policy snapshot, hashed I/O, and chain linkage.  
Everything shown here runs locally with no API keys."

### Beat 1: Spec + vectors (0:25-0:55)

Narration:

"Start with protocol invariants: schema and vectors."

Command:

```bash
pnpm spec:validate
```

Talking points:

- deterministic canonicalization
- stable hash/chain rules
- vectors enforce cross-language parity

### Beat 2: Generate + verify (0:55-1:35)

Narration:

"Generate a signed receipt, then verify offline with the public key."

Commands:

```bash
pnpm --filter @trustproof/sdk build
node --input-type=module -e "import {generateKeyPairSync} from 'node:crypto'; import fs from 'node:fs'; import {generate} from './packages/js/dist/index.js'; const claims=JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8')); const {privateKey,publicKey}=generateKeyPairSync('ed25519'); const priv=privateKey.export({format:'pem',type:'pkcs8'}).toString(); const pub=publicKey.export({format:'pem',type:'spki'}).toString(); const jwt=await generate(claims,priv); fs.mkdirSync('./examples/output/demo',{recursive:true}); fs.writeFileSync('./examples/output/demo/demo.jwt',jwt); fs.writeFileSync('./examples/output/demo/demo.pub.pem',pub);"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
node packages/js/dist/cli.js inspect "$(cat examples/output/demo/demo.jwt)"
```

Talking points:

- verifier returns structured results
- inspect decodes claims for audit/debug

### Beat 3: Chain + tamper evidence (1:35-2:20)

Narration:

"Now show chained receipts and tamper failure."

Commands:

```bash
pnpm --filter @trustproof/sdk example:payout-stepup
pnpm --filter @trustproof/sdk example:agent-actions
node -e "const fs=require('fs'); const t=fs.readFileSync('examples/output/demo/demo.jwt','utf8').trim(); const p=t.split('.'); const s=p[2]; const i=Math.min(10,s.length-1); const r=s[i]==='a'?'b':'a'; p[2]=s.slice(0,i)+r+s.slice(i+1); fs.writeFileSync('examples/output/demo/demo.tampered.jwt',p.join('.'));"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.tampered.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

Talking points:

- chained proofs verify deterministically
- mutating one byte breaks signature verification

### Optional parity add-on (2:20-2:40)

Command:

```bash
python -m pip install -e "packages/py[dev]"
cd packages/py && python -m pytest -q && cd -
python -m trustproof verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

### Close (2:40-3:00)

Narration:

"TrustProof is protocol-first: schema, vectors, and offline verification.  
Next: webhook integrations, enterprise verifier deployment, and step-up UX.  
Repository link is in the description."

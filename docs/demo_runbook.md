# TrustProof Demo Runbook

## 1) Goal

This demo proves three concrete properties: (1) action outcomes are emitted as signed action receipts (JWT claims envelopes), (2) chain linkage is tamper-evident, and (3) verification works offline with only a public key and protocol rules (schema + vectors), without external API keys.

## 2) Prereqs

- Node.js 20+
- pnpm
- Python 3.12+

## 3) Clean Setup

```bash
git clone https://github.com/ataraxia-labs-ai/TrustProof-Protocol.git
cd TrustProof-Protocol
pnpm install
```

Optional Python virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

## 4) Step-by-step Commands

### 4.1 Validate spec + vectors

```bash
pnpm spec:validate
```

Expected (short):

- `PASS schema: ...`
- `PASS vector: ...`
- `All spec validations passed.`

### 4.2 Build SDK

```bash
pnpm --filter @trustproof/sdk build
```

Expected (short):

- `Build success`

### 4.3 Run example suite

```bash
pnpm --filter @trustproof/sdk example:payout-stepup
pnpm --filter @trustproof/sdk example:agent-actions
```

Expected (short):

- `✅ Verified ...`
- `✅ Tamper => OK (failed as expected)`
- Output files written under:
  - `examples/output/payout_stepup/`
  - `examples/output/agent_actions/`

### 4.4 CLI verify UX

Generate demo JWT + pubkey (no API keys):

```bash
node --input-type=module -e "import {generateKeyPairSync} from 'node:crypto'; import fs from 'node:fs'; import {generate} from './packages/js/dist/index.js'; const claims=JSON.parse(fs.readFileSync('./spec/examples/allow.json','utf8')); const {privateKey,publicKey}=generateKeyPairSync('ed25519'); const priv=privateKey.export({format:'pem',type:'pkcs8'}).toString(); const pub=publicKey.export({format:'pem',type:'spki'}).toString(); const jwt=await generate(claims,priv); fs.mkdirSync('./examples/output/demo',{recursive:true}); fs.writeFileSync('./examples/output/demo/demo.jwt',jwt); fs.writeFileSync('./examples/output/demo/demo.pub.pem',pub);"
```

Verify + inspect:

```bash
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
node packages/js/dist/cli.js inspect "$(cat examples/output/demo/demo.jwt)"
```

Equivalent command shape when the JS bin is on PATH:

```bash
trustproof verify "<jwt>" --pubkey "<pk>"
trustproof inspect "<jwt>"
```

Expected (short):

- Verify prints `✅ Verified ...`
- Inspect prints decoded claims JSON

### 4.5 Tamper check

Mutate one character in the signature segment:

```bash
node -e "const fs=require('fs'); const t=fs.readFileSync('examples/output/demo/demo.jwt','utf8').trim(); const p=t.split('.'); const s=p[2]; const i=Math.min(10,s.length-1); const r=s[i]==='a'?'b':'a'; p[2]=s.slice(0,i)+r+s.slice(i+1); fs.writeFileSync('examples/output/demo/demo.tampered.jwt',p.join('.'));"
node packages/js/dist/cli.js verify "$(cat examples/output/demo/demo.tampered.jwt)" --pubkey examples/output/demo/demo.pub.pem
```

Expected (short):

- `❌ Not Verified`
- error includes `INVALID_SIGNATURE`

### 4.6 Python parity (recommended)

Install Python package + run tests + verify the same JWT:

```bash
python -m pip install -e "packages/py[dev]"
cd packages/py && python -m pytest -q && cd -
python -m trustproof verify "$(cat examples/output/demo/demo.jwt)" --pubkey examples/output/demo/demo.pub.pem
python -m trustproof inspect "$(cat examples/output/demo/demo.jwt)"
```

Expected (short):

- pytest passes
- Python verify prints `✅ Verified ...`
- Python inspect prints claims JSON

## 5) Screen Flow (for recording)

- Use split terminal:
  - Left pane: commands
  - Right pane: outputs
- Show in order:
  1. `pnpm spec:validate`
  2. example suite commands
  3. CLI verify + inspect
  4. tamper failure
- Optional browser tab:
  - `https://ataraxia-labs-ai.github.io/TrustProof-Protocol/`
  - briefly open `spec/README` and vectors reference

## 6) Troubleshooting

- `pnpm: command not found`
  - install pnpm (`npm i -g pnpm`) and rerun `pnpm install`
- Python dependency issues
  - ensure Python 3.12+, then run `python -m pip install -e "packages/py[dev]"`
- `trustproof` command not found in shell PATH
  - use:
    - `node packages/js/dist/cli.js verify ...`
    - `node packages/js/dist/cli.js inspect ...`

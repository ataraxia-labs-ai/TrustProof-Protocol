# verdicto-openclaw

Cryptographic audit trails for OpenClaw agents. Every tool call, browser action, and API request gets a signed, tamper-evident TrustProof.

[![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/LICENSE)

## Why?

OpenClaw lets your AI agent browse the web, run code, access files, and interact with services. But when something goes wrong — or when a regulator asks — can you prove exactly what the agent did, who authorized it, and what constraints were in place?

**verdicto-openclaw** generates a TrustProof for every action. Proofs are cryptographically signed (Ed25519), chain-linked for tamper evidence, and optionally persisted to the Verdicto dashboard for real-time monitoring.

## Install

```bash
cp -r verdicto-openclaw ~/.openclaw/extensions/verdicto-trustproof
cd ~/.openclaw/extensions/verdicto-trustproof && npm install && npm run build
```

## Configure

Add to your `openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "verdicto-trustproof": {
        "enabled": true,
        "config": {
          "agentId": "my-openclaw-agent",
          "traceTools": true,
          "traceBrowser": true
        }
      }
    }
  }
}
```

## What Happens

Every time your agent uses a tool:

```
[verdicto] TrustProof generated: openclaw.tool_call.web_search (chain: 5 proofs, integrity: VALID)
```

The agent can query its own trust state:

```
Agent: "Check my trust chain integrity before proceeding."
→ trustproof_verify_chain: { valid: true, proof_count: 12, errors: [] }
```

## Agent-Facing Tools

The plugin registers three tools the agent can use:

| Tool | Description |
|---|---|
| `trustproof_status` | Current chain summary (count, latest action) |
| `trustproof_verify_chain` | Verify entire chain integrity |
| `trustproof_export` | Export chain as JSON/JWT array |

## Dashboard Integration (Optional)

Connect to the Verdicto API for real-time monitoring:

```json
{
  "config": {
    "verdictoApiUrl": "http://127.0.0.1:8000",
    "verdictoApiKey": "vk_..."
  }
}
```

Open `http://localhost:3000/cases` to see agent actions with full evidence, proofs, and audit trails.

## Action Types

| Action | When |
|---|---|
| `openclaw.tool_call.<name>` | Any tool invocation |
| `openclaw.web_browse.<type>` | Browser navigation, clicks, etc. |
| `openclaw.file_access` | File system operations |
| `openclaw.api_call` | Outbound API requests |

## Part of TrustProof Protocol

This plugin uses the open [TrustProof Protocol](https://github.com/ataraxia-labs-ai/TrustProof-Protocol) (Apache-2.0). Proofs are independently verifiable by anyone with the public key — no Verdicto account required.

## License

Apache-2.0

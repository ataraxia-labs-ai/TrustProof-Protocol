# Basic Setup

## Install

```bash
# Copy to your OpenClaw extensions directory
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

## What You'll See

Every tool call produces a log entry:

```
[verdicto] TrustProof generated: openclaw.tool_call.web_search (chain: 1 proofs)
[verdicto] TrustProof generated: openclaw.tool_call.code_execute (chain: 2 proofs)
[verdicto] TrustProof generated: openclaw.web_browse.navigate (chain: 3 proofs)
```

At session end:

```
[verdicto] Session ended: 3 proofs, chain integrity: VALID
```

## Optional: Dashboard

Add API credentials to see proofs in the Verdicto web console:

```json
{
  "config": {
    "verdictoApiUrl": "http://127.0.0.1:8000",
    "verdictoApiKey": "vk_..."
  }
}
```

Then visit `http://localhost:3000/cases` to see each agent action with evidence,
proof JWTs, and tamper-evident audit trails.

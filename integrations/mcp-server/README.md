# verdicto-mcp

Trust infrastructure for AI agents via the Model Context Protocol.

Connect Claude, ChatGPT, or any MCP-compatible agent to Verdicto's trust verification, proof generation, and audit trail capabilities.

[![PyPI](https://img.shields.io/pypi/v/verdicto-mcp)](https://pypi.org/project/verdicto-mcp/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/LICENSE)

## Install

```bash
pip install verdicto-mcp
```

## Use with Claude Desktop

Add to Claude Desktop config (Settings > Developer > MCP Servers):

```json
{
  "mcpServers": {
    "verdicto": {
      "command": "verdicto-mcp",
      "env": {
        "VERDICTO_API_URL": "http://127.0.0.1:8000",
        "VERDICTO_API_KEY": "your_key"
      }
    }
  }
}
```

Now Claude can verify actions before executing them:

> "Before transferring $500, verify this action with Verdicto."
> Claude calls `verify_agent_action` -> gets allow/deny with signed proof

## Available Tools (10)

| Tool | Description | Requires API |
|---|---|:---:|
| `verify_agent_action` | Verify an action against trust policy | Yes |
| `issue_agent_pass` | Issue a constrained Agent Pass | Yes |
| `verify_trust_proof` | Cryptographically verify a proof JWT | Optional |
| `inspect_trust_proof` | Decode proof claims (no verification) | No |
| `generate_trust_proof` | Generate a locally signed proof | No |
| `verify_proof_chain` | Verify tamper-evident proof chain | No |
| `get_audit_trail` | Get verification audit trail | Yes |
| `get_evidence_bundle` | Export compliance evidence bundle | Yes |
| `list_recent_verifications` | List recent decisions | Yes |
| `check_api_health` | Check API status | Yes |

## Run as HTTP Server

```bash
VERDICTO_API_KEY=vk_... verdicto-mcp --transport http --port 9100
```

Then use from the Anthropic Messages API:

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Verify this purchase..."}],
    mcp_servers=[{"type": "url", "url": "http://localhost:9100/mcp/", "name": "verdicto"}],
)
```

## Local-Only Mode

4 tools work without any API connection — useful for development:

```bash
verdicto-mcp  # No env vars needed for local tools
```

## Part of TrustProof Protocol

Open standard: [github.com/ataraxia-labs-ai/TrustProof-Protocol](https://github.com/ataraxia-labs-ai/TrustProof-Protocol)

## License

Apache-2.0

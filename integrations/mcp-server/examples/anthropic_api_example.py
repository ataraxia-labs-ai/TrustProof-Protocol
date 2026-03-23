"""Use Verdicto MCP server from the Anthropic Messages API.

Prerequisites:
  1. Start Verdicto API: pnpm --filter @verdicto/api dev
  2. Start MCP server: verdicto-mcp --transport http --port 9100
  3. Set ANTHROPIC_API_KEY and VERDICTO_API_KEY env vars
"""

import os

try:
    import anthropic
except ImportError:
    print("Install anthropic SDK: pip install anthropic")
    raise SystemExit(1)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": (
                "I need to make a $25 purchase from merchant demo_store. "
                "Please verify this action first using Verdicto, then tell me the result."
            ),
        }
    ],
    mcp_servers=[
        {
            "type": "url",
            "url": "http://localhost:9100/mcp/",
            "name": "verdicto",
        }
    ],
    extra_headers={"anthropic-beta": "mcp-client-2025-04-04"},
)

for block in response.content:
    if hasattr(block, "text"):
        print(block.text)

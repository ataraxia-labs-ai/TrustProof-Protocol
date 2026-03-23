# verdicto-langchain

Cryptographic audit trails for LangChain agents. Every tool call signed. Every chain step verified. Every proof tamper-evident.

[![PyPI](https://img.shields.io/pypi/v/verdicto-langchain)](https://pypi.org/project/verdicto-langchain/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](https://github.com/ataraxia-labs-ai/TrustProof-Protocol/blob/main/LICENSE)

## Install

```bash
pip install verdicto-langchain
```

## Add to any agent (3 lines)

```python
from verdicto_langchain import VerdictoCallbackHandler

handler = VerdictoCallbackHandler(agent_id="my-agent")
result = agent.invoke({"input": "..."}, config={"callbacks": [handler]})
proofs = handler.get_proof_chain()  # list of signed JWTs
```

## Why?

When your LangChain agent books a flight, transfers money, or modifies code — can you prove who authorized it? What constraints were in place? That the agent acted within scope?

**verdicto-langchain** generates a [TrustProof](https://github.com/ataraxia-labs-ai/TrustProof-Protocol) for every action. Proofs are chained with tamper-evident linking (Ed25519/EdDSA). If any proof is modified, the entire chain breaks — providing an immutable audit trail from the first tool call to the last.

## What gets a proof?

| Event | Action Type | Default |
|---|---|---|
| Tool call (start + end) | `langchain.tool_call.<name>` | On |
| Tool error | `langchain.tool_call.<name>` (decision: deny) | On |
| Chain step | `langchain.chain_step.<name>` | On |
| LLM call | `langchain.llm_decision` | Off |

## Chain Verification

```python
handler = VerdictoCallbackHandler()
# ... run agent ...

# Verify the entire chain
result = handler.verify_chain()
assert result["ok"]  # True if no tampering detected

# Export for external audit
bundle = handler.export_bundle()
```

## Configuration

```python
from verdicto_langchain import VerdictoCallbackHandler, VerdictoConfig

config = VerdictoConfig(
    agent_id="shopping-agent-v2",
    trace_llm_calls=True,           # include LLM-level proofs
    trace_chain_steps=False,         # skip chain-level proofs
    policy_scopes=["checkout.purchase", "checkout.refund"],
    protocol_refs={                  # v0.2 cross-protocol linking
        "ap2_mandate_id": "mandate_cart_abc123",
    },
)
handler = VerdictoCallbackHandler(config=config)
```

## Cross-Protocol References (v0.2)

Link proofs to external protocol artifacts:

```python
config = VerdictoConfig(
    protocol_refs={
        "ap2_mandate_id": "mandate_cart_abc123",      # Google AP2
        "verifiable_intent_id": "vi_mc_def456",       # Mastercard
        "mcp_tool_call_id": "mcp_call_789",           # Anthropic MCP
    },
    vc_profile={
        "vc_version": "2.0",
        "issuer_did": "did:web:verdicto.dev",
        "subject_did": "did:key:z6Mk...",
    },
)
```

## Works With

- Any LangChain agent (tool calling, ReAct, custom)
- Any LLM (OpenAI, Anthropic, Google, local models)
- Part of the [TrustProof Protocol](https://github.com/ataraxia-labs-ai/TrustProof-Protocol) — an open standard for AI agent verification

## License

Apache-2.0

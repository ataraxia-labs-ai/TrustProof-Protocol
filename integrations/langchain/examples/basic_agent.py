"""Add verifiable trust proofs to any LangChain agent in 3 lines.

Every tool call gets a signed, chained TrustProof (Ed25519/EdDSA).
No API key, no server — pure local crypto.

Requirements: pip install verdicto-langchain langchain langchain-openai
"""

from verdicto_langchain import VerdictoCallbackHandler

# This is all you add — 1 line to create the handler
handler = VerdictoCallbackHandler(agent_id="shopping-agent-v1")

# Simulate tool calls (in a real app, LangChain invokes these callbacks)
import uuid

rid = uuid.uuid4()
handler.on_tool_start({"name": "search_products"}, "running shoes under $50", run_id=rid)
handler.on_tool_end("Nike Air Max 90 - $120, Adidas Ultraboost - $45", run_id=rid)

rid2 = uuid.uuid4()
handler.on_tool_start({"name": "checkout"}, "Adidas Ultraboost, qty=1", run_id=rid2)
handler.on_tool_end("Order confirmed: #ORD-12345", run_id=rid2)

# Inspect the proof chain
for i, proof in enumerate(handler.get_proof_chain()):
    print(f"Proof {i + 1}: {proof[:60]}...")

# Verify the entire chain is tamper-evident
verification = handler.verify_chain()
print(f"\nChain integrity: {'VALID' if verification['ok'] else 'BROKEN'}")
print(f"Proofs generated: {len(handler.get_proof_chain())}")

"""FULL DEMO: LangChain Agent -> TrustProofs -> Verdicto Dashboard

This script demonstrates the complete Verdicto trust infrastructure:
1. Issues an Agent Pass with policy constraints
2. Runs LangChain agent tool calls with TrustProof generation
3. Each tool call appears as a verification case in the dashboard
4. Proofs are cryptographically signed and tamper-evident chain linked

Prerequisites:
  - Start API: pnpm --filter @verdicto/api dev
  - Start web: pnpm --filter @verdicto/web dev
  - Get API key: curl -sS -X POST http://127.0.0.1:8000/v1/keys/rotate | jq -r '.key'
  - Set: export VERDICTO_API_KEY="vk_..."

Then open http://localhost:3000/cases and watch verifications appear in real-time.
"""

import os
import time
import uuid

from verdicto_langchain import VerdictoCallbackHandler, VerdictoConfig

API_KEY = os.getenv("VERDICTO_API_KEY", "YOUR_KEY_HERE")

config = VerdictoConfig(
    agent_id="demo-shopping-agent",
    verdicto_api_url="http://127.0.0.1:8000",
    verdicto_api_key=API_KEY,
    agent_pass_scopes=["checkout.purchase", "langchain.tool_call"],
    agent_pass_max_amount_cents=5000,
    agent_pass_currency_allowlist=["USD"],
    agent_pass_merchant_allowlist=["m_demo_1"],
    api_send_async=False,
)

with VerdictoCallbackHandler(config=config) as handler:
    print("=" * 60)
    print("VERDICTO FULL DEMO")
    print("=" * 60)
    print()
    print("[Scenario] Normal shopping flow")
    print("-" * 40)

    steps = [
        ("search_products", "running shoes under $50",
         "Found: Nike Air Max ($45), Adidas Ultraboost ($48)"),
        ("add_to_cart", "Nike Air Max size 10, qty 1",
         "Added to cart. Subtotal: $45.00"),
        ("checkout", "Process payment $45.00 USD, merchant m_demo_1",
         "Payment processed. Order #ORD-2026-001 confirmed."),
    ]

    for name, inp, out in steps:
        rid = uuid.uuid4()
        handler.on_tool_start({"name": name}, inp, run_id=rid)
        handler.on_tool_end(out, run_id=rid)
        time.sleep(0.3)
        print(f"  {name}: done")

    print(f"\nLocal proofs generated: {len(handler.get_proof_chain())}")
    chain = handler.verify_chain()
    print(f"Chain integrity: {'VALID' if chain['ok'] else 'BROKEN'}")
    print()
    print("[Done] Open http://localhost:3000/cases to see verifications")
    print("       Click any case -> Evidence, Trust Proof, Audit Trail tabs")

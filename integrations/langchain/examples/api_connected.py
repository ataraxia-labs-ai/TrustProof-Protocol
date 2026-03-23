"""LangChain agent with TrustProofs visible in the Verdicto dashboard.

Run this with the API running locally:
  pnpm --filter @verdicto/api dev
  python examples/api_connected.py
  # Open http://localhost:3000/cases to see proofs in the dashboard
"""

import os
import uuid

from verdicto_langchain import VerdictoCallbackHandler, VerdictoConfig

API_KEY = os.getenv("VERDICTO_API_KEY", "YOUR_API_KEY_HERE")

config = VerdictoConfig(
    agent_id="langchain-shopping-agent-v1",
    verdicto_api_url="http://127.0.0.1:8000",
    verdicto_api_key=API_KEY,
    agent_pass_scopes=["checkout.purchase", "langchain.tool_call"],
    agent_pass_max_amount_cents=10000,
    agent_pass_currency_allowlist=["USD"],
    agent_pass_merchant_allowlist=["m_demo_1"],
    api_send_async=False,
)

with VerdictoCallbackHandler(config=config) as handler:
    print("Running agent tool calls...")

    for name, inp, out in [
        ("search_products", "Find running shoes under $100", "Found: Nike Air Max 90 ($95), Adidas Ultraboost ($120)"),
        ("check_inventory", "Check Nike Air Max 90 size 10", "In stock: 23 units available"),
        ("process_checkout", "Purchase Nike Air Max 90 size 10", "Order confirmed: #ORD-98765, charged $95.00"),
    ]:
        rid = uuid.uuid4()
        handler.on_tool_start({"name": name}, inp, run_id=rid)
        handler.on_tool_end(out, run_id=rid)

    chain_result = handler.verify_chain()
    print(f"\nLocal proof chain: {len(handler.get_proof_chain())} proofs")
    print(f"Chain integrity: {'VALID' if chain_result['ok'] else 'BROKEN'}")

    if handler._api_bridge and handler._api_bridge.enabled:
        print(f"\nDashboard: Open http://localhost:3000/cases to see these verifications")
    else:
        print("\nNote: Set VERDICTO_API_KEY to enable dashboard visibility.")

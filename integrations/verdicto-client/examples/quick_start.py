"""Verify an AI agent action in 5 lines."""
import os
from verdicto import VerdictoClient

API_KEY = os.environ.get("VERDICTO_API_KEY", "YOUR_API_KEY")
BASE_URL = os.environ.get("VERDICTO_API_BASE_URL", "http://127.0.0.1:8000")

client = VerdictoClient(api_key=API_KEY, base_url=BASE_URL)

# Issue an Agent Pass with policy constraints
agent_pass = client.issue_agent_pass(
    sub="shopping-agent-v1",
    ttl_seconds=900,
    scopes=["checkout.purchase"],
    max_amount_cents=5000,
    currency_allowlist=["USD"],
    merchant_allowlist=["m_demo_1"],
)
print(f"Agent Pass issued: {agent_pass.agent_pass[:40]}...")

# Verify an action against the policy
result = client.verify_agent(
    agent_pass=agent_pass.agent_pass,
    requested_action="checkout.purchase",
    amount_cents=1500,
    currency="USD",
    merchant_id="m_demo_1",
    subject_id="user_456",
)

print(f"Decision: {result.decision}")
print(f"Confidence: {result.confidence}")
print(f"Verification ID: {result.verification_id}")
if result.proof_jwt:
    print(f"Proof JWT: {result.proof_jwt[:50]}...")

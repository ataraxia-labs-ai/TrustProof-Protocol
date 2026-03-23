"""Step-up verification flow: trigger velocity limits and approve step-up.

Demonstrates how rapid verifications can trigger a step_up decision,
then shows how to extract the token and approve the challenge.
"""
import os
import sys
from urllib.parse import urlparse

from verdicto import VerdictoClient, VerdictoError

API_KEY = os.environ.get("VERDICTO_API_KEY", "YOUR_API_KEY")
BASE_URL = os.environ.get("VERDICTO_API_BASE_URL", "http://127.0.0.1:8000")


def extract_step_up_token(step_up_url: str) -> str:
    """Extract the step-up token from the URL path.

    Expected format: /v1/step-up/{token}/approve
    or a full URL: http://...//v1/step-up/{token}/approve
    """
    path = urlparse(step_up_url).path
    parts = [p for p in path.strip("/").split("/") if p]
    # Find the segment after "step-up"
    for i, part in enumerate(parts):
        if part == "step-up" and i + 1 < len(parts):
            return parts[i + 1]
    raise ValueError(f"Cannot extract step-up token from URL: {step_up_url}")


def main() -> None:
    with VerdictoClient(api_key=API_KEY, base_url=BASE_URL) as client:
        # ── 1. Issue an Agent Pass ───────────────────────────────────
        print("1. Issuing Agent Pass...")
        agent_pass = client.issue_agent_pass(
            sub="trading-agent-v2",
            ttl_seconds=300,
            scopes=["checkout.purchase"],
            max_amount_cents=10000,
            currency_allowlist=["USD"],
            merchant_allowlist=["m_demo_1"],
        )
        print(f"   Pass issued: {agent_pass.agent_pass[:40]}...")

        # ── 2. Rapid verifications to trigger velocity step-up ───────
        print("\n2. Sending rapid verifications to trigger velocity check...")
        step_up_result = None

        for i in range(1, 11):
            result = client.verify_agent(
                agent_pass=agent_pass.agent_pass,
                requested_action="checkout.purchase",
                amount_cents=500 * i,
                currency="USD",
                merchant_id="m_demo_1",
                subject_id="user_789",
            )
            status = f"   [{i:>2}/10] amount=${5 * i:>3} -> {result.decision}"
            if result.step_up_url:
                status += f"  (step-up required)"
            print(status)

            if result.decision == "step_up":
                step_up_result = result
                break

        if not step_up_result or not step_up_result.step_up_url:
            print("\n   No step-up was triggered. This can happen if:")
            print("   - Velocity limits are not configured")
            print("   - The threshold was not reached in 10 attempts")
            print("   Try adjusting policy thresholds or increasing attempts.")
            return

        # ── 3. Extract step-up token from URL ────────────────────────
        print(f"\n3. Step-up triggered!")
        print(f"   URL: {step_up_result.step_up_url}")
        print(f"   Expires: {step_up_result.step_up_expires_at}")
        print(f"   Verification ID: {step_up_result.verification_id}")

        token = extract_step_up_token(step_up_result.step_up_url)
        print(f"   Extracted token: {token}")

        # ── 4. Approve the step-up challenge ─────────────────────────
        print("\n4. Approving step-up challenge...")
        approval = client.approve_step_up(token)
        print(f"   Status: {approval.status}")
        print(f"   Decision: {approval.decision}")
        print(f"   Verification ID: {approval.verification_id}")
        if approval.proof_jwt:
            print(f"   Proof JWT: {approval.proof_jwt[:50]}...")

        # ── 5. Verify the result ─────────────────────────────────────
        print("\n5. Checking final state...")
        if approval.proof_jwt:
            proof_check = client.verify_proof(approval.proof_jwt)
            print(f"   Proof valid: {proof_check.ok}")
            print(f"   Decision confirmed: {proof_check.decision}")
        else:
            print("   No proof JWT returned -- checking audit trail instead.")
            audit = client.get_audit_trail(approval.verification_id)
            print(f"   Audit trail: {list(audit.keys())}")

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except VerdictoError as exc:
        print(f"Fatal Verdicto error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)

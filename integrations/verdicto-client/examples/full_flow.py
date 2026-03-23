"""Complete Verdicto flow: issue, verify, deny, proof, bundle, and cases.

Demonstrates the full lifecycle of an agent verification including
error handling with typed exceptions.
"""
import os
import sys

from verdicto import (
    VerdictoClient,
    VerdictoError,
    AuthenticationError,
    RateLimitError,
    ReplayDetectedError,
)

API_KEY = os.environ.get("VERDICTO_API_KEY", "YOUR_API_KEY")
BASE_URL = os.environ.get("VERDICTO_API_BASE_URL", "http://127.0.0.1:8000")


def main() -> None:
    with VerdictoClient(api_key=API_KEY, base_url=BASE_URL) as client:
        # ── 1. Issue an Agent Pass ───────────────────────────────────
        print("1. Issuing Agent Pass...")
        agent_pass = client.issue_agent_pass(
            sub="shopping-agent-v1",
            ttl_seconds=900,
            scopes=["checkout.purchase"],
            max_amount_cents=5000,
            currency_allowlist=["USD"],
            merchant_allowlist=["m_demo_1"],
        )
        print(f"   Pass: {agent_pass.agent_pass[:40]}...")
        print(f"   Request ID: {agent_pass.request_id}")

        # ── 2. Verify an allowed action ──────────────────────────────
        print("\n2. Verifying $15 purchase (under $50 cap)...")
        result = client.verify_agent(
            agent_pass=agent_pass.agent_pass,
            requested_action="checkout.purchase",
            amount_cents=1500,
            currency="USD",
            merchant_id="m_demo_1",
            subject_id="user_456",
        )
        print(f"   Decision: {result.decision}")
        print(f"   Confidence: {result.confidence}")
        print(f"   Reason codes: {result.reason_codes}")
        proof_jwt = result.proof_jwt

        # ── 3. Verify an over-cap action (expect deny) ──────────────
        print("\n3. Verifying $99 purchase (over $50 cap)...")
        try:
            over_cap = client.verify_agent(
                agent_pass=agent_pass.agent_pass,
                requested_action="checkout.purchase",
                amount_cents=9900,
                currency="USD",
                merchant_id="m_demo_1",
                subject_id="user_456",
            )
            print(f"   Decision: {over_cap.decision}")
            print(f"   Reason codes: {over_cap.reason_codes}")
        except VerdictoError as exc:
            print(f"   Denied with error: {exc}")

        # ── 4. Verify the proof JWT ──────────────────────────────────
        if proof_jwt:
            print("\n4. Verifying Trust Proof JWT...")
            proof_result = client.verify_proof(proof_jwt)
            print(f"   Valid: {proof_result.ok}")
            print(f"   Verification ID: {proof_result.verification_id}")
            print(f"   Decision: {proof_result.decision}")

            # ── 5. Get proof bundle ──────────────────────────────────
            print("\n5. Fetching evidence bundle...")
            bundle = client.get_proof_bundle(result.verification_id)
            print(f"   Bundle keys: {list(bundle.keys())}")
        else:
            print("\n4-5. Skipping proof steps (no proof_jwt returned).")

        # ── 6. List cases ────────────────────────────────────────────
        print("\n6. Listing recent cases...")
        cases_list = client.list_cases(limit=5)
        print(f"   Total cases returned: {len(cases_list.cases)}")
        for case in cases_list.cases[:3]:
            print(f"   - {case.id}: {case.decision} ({case.requested_action})")

        # ── 7. Error handling examples ───────────────────────────────
        print("\n7. Error handling demo:")

        # AuthenticationError
        try:
            bad_client = VerdictoClient(api_key="invalid_key", base_url=BASE_URL)
            bad_client.health()
        except AuthenticationError as exc:
            print(f"   AuthenticationError: {exc.message} (status={exc.status_code})")
        except VerdictoError:
            print("   (server did not return 401 for bad key in health check)")

        # RateLimitError
        try:
            # Simulated -- in production this triggers after many rapid calls
            raise RateLimitError("Rate limit exceeded", retry_after_sec=2.0)
        except RateLimitError as exc:
            print(f"   RateLimitError: retry after {exc.retry_after_sec}s")

        # ReplayDetectedError
        try:
            raise ReplayDetectedError(
                "Agent pass already consumed", code="REPLAY_DETECTED", status_code=409
            )
        except ReplayDetectedError as exc:
            print(f"   ReplayDetectedError: {exc.message}")

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except VerdictoError as exc:
        print(f"Fatal Verdicto error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)

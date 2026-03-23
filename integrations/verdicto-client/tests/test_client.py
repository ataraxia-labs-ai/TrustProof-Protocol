"""Tests for the synchronous VerdictoClient using respx (httpx mocking)."""

from __future__ import annotations

import httpx
import pytest
import respx

from verdicto import (
    AgentPass,
    AuthenticationError,
    IdempotencyConflictError,
    NotFoundError,
    RateLimitError,
    ReplayDetectedError,
    RotateKeyResult,
    ServerError,
    StepUpSession,
    ValidationError,
    VerdictoClient,
    VerdictoError,
    VerifyResult,
)

BASE_URL = "https://api.test"
API_KEY = "vk_test_key"


def _client() -> VerdictoClient:
    return VerdictoClient(api_key=API_KEY, base_url=BASE_URL)


# ── 1. issue_agent_pass ──────────────────────────────────────────────────────


@respx.mock
def test_issue_agent_pass():
    respx.post(f"{BASE_URL}/v1/agent/pass/issue").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "agent_pass": "eyJ...",
                "request_id": "req_1",
            },
        )
    )

    client = _client()
    result = client.issue_agent_pass(
        sub="user_1",
        ttl_seconds=900,
        scopes=["checkout.purchase"],
        currency_allowlist=["USD"],
        merchant_allowlist=["m_demo_1"],
    )

    assert isinstance(result, AgentPass)
    assert result.agent_pass == "eyJ..."
    assert result.request_id == "req_1"


# ── 2. verify_agent — allow ─────────────────────────────────────────────────


@respx.mock
def test_verify_agent_allow():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "tenant_id": "t_1",
                "decision": "allow",
                "confidence": 0.95,
                "reason_codes": [],
                "policy_v": "v0",
                "request_id": "req_2",
                "verification_id": "ver_1",
                "proof_jwt": "eyJ.proof.sig",
            },
        )
    )

    client = _client()
    result = client.verify_agent(
        agent_pass="eyJ...",
        requested_action="checkout.purchase",
        amount_cents=1500,
        currency="USD",
        merchant_id="m_demo_1",
    )

    assert isinstance(result, VerifyResult)
    assert result.decision == "allow"
    assert result.confidence == 0.95
    assert result.proof_jwt == "eyJ.proof.sig"
    assert result.verification_id == "ver_1"


# ── 3. verify_agent — deny ──────────────────────────────────────────────────


@respx.mock
def test_verify_agent_deny():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "tenant_id": "t_1",
                "decision": "deny",
                "confidence": 0.80,
                "reason_codes": ["amount_exceeded"],
                "policy_v": "v0",
                "request_id": "req_2b",
                "verification_id": "ver_2",
                "proof_jwt": "eyJ.deny.sig",
            },
        )
    )

    client = _client()
    result = client.verify_agent(
        agent_pass="eyJ...",
        requested_action="checkout.purchase",
        amount_cents=100_000,
        currency="USD",
        merchant_id="m_demo_1",
    )

    assert result.decision == "deny"
    assert "amount_exceeded" in result.reason_codes


# ── 4. verify_agent — step_up ────────────────────────────────────────────────


@respx.mock
def test_verify_agent_step_up():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "tenant_id": "t_1",
                "decision": "step_up",
                "confidence": 0.50,
                "reason_codes": [],
                "policy_v": "v0",
                "request_id": "req_2c",
                "verification_id": "ver_3",
                "proof_jwt": None,
                "step_up_url": "https://example.com/step-up/tok_123",
                "step_up_expires_at": "2026-03-21T15:00:00Z",
            },
        )
    )

    client = _client()
    result = client.verify_agent(
        agent_pass="eyJ...",
        requested_action="checkout.purchase",
        amount_cents=5000,
        currency="USD",
        merchant_id="m_demo_1",
    )

    assert result.decision == "step_up"
    assert result.step_up_url == "https://example.com/step-up/tok_123"
    assert result.step_up_expires_at == "2026-03-21T15:00:00Z"
    assert result.proof_jwt is None


# ── 5. verify_proof ──────────────────────────────────────────────────────────


@respx.mock
def test_verify_proof():
    respx.post(f"{BASE_URL}/v1/proofs/verify").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "verification_id": "ver_1",
                "decision": "allow",
                "reason_codes": [],
                "issued_at": "2026-03-21T12:00:00Z",
                "request_id": "req_3",
            },
        )
    )

    client = _client()
    result = client.verify_proof("eyJ.proof.sig")

    assert result.ok is True
    assert result.verification_id == "ver_1"
    assert result.decision == "allow"
    assert result.request_id == "req_3"


# ── 6. get_proof_bundle ──────────────────────────────────────────────────────


@respx.mock
def test_get_proof_bundle():
    respx.get(f"{BASE_URL}/v1/proofs/ver_1/bundle").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "bundle": {"verification_id": "ver_1"},
                "request_id": "req_4",
            },
        )
    )

    client = _client()
    result = client.get_proof_bundle("ver_1")

    assert isinstance(result, dict)
    assert result["ok"] is True
    assert result["bundle"]["verification_id"] == "ver_1"


# ── 7. list_cases ────────────────────────────────────────────────────────────


@respx.mock
def test_list_cases():
    respx.get(f"{BASE_URL}/v1/cases").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "tenant_id": "t_1",
                "cases": [
                    {"id": "ver_1", "decision": "allow", "confidence": 0.95}
                ],
                "limit": 50,
                "offset": 0,
            },
        )
    )

    client = _client()
    result = client.list_cases()

    from verdicto import CasesList

    assert isinstance(result, CasesList)
    assert len(result.cases) == 1
    assert result.cases[0].id == "ver_1"
    assert result.cases[0].decision == "allow"


# ── 8. retry_delivery ────────────────────────────────────────────────────────


@respx.mock
def test_retry_delivery():
    respx.post(f"{BASE_URL}/v1/webhooks/deliveries/del_1/retry").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "delivery_id": "del_1",
                "status": "pending",
            },
        )
    )

    client = _client()
    result = client.retry_delivery("del_1")

    assert isinstance(result, dict)
    assert result["ok"] is True
    assert result["delivery_id"] == "del_1"
    assert result["status"] == "pending"


# ── 9. approve_step_up ───────────────────────────────────────────────────────


@respx.mock
def test_approve_step_up():
    respx.post(f"{BASE_URL}/v1/step-up/tok_123/approve").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "session": {
                    "status": "approved",
                    "verification_id": "ver_1",
                    "proof_jwt": "eyJ...",
                    "decision": "allow",
                },
            },
        )
    )

    client = _client()
    result = client.approve_step_up("tok_123")

    assert isinstance(result, StepUpSession)
    assert result.status == "approved"
    assert result.verification_id == "ver_1"
    assert result.proof_jwt == "eyJ..."
    assert result.decision == "allow"


# ── 10. rotate_key ───────────────────────────────────────────────────────────


@respx.mock
def test_rotate_key():
    respx.post(f"{BASE_URL}/v1/keys/rotate").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "tenant_id": "t_1",
                "key": "vk_admin_new_key",
                "key_prefix": "vk_admin_...",
                "name": "rotated",
                "deactivated_previous": True,
                "created_at": "2026-03-21T12:00:00Z",
                "request_id": "req_5",
            },
        )
    )

    client = _client()
    result = client.rotate_key()

    assert isinstance(result, RotateKeyResult)
    assert result.key == "vk_admin_new_key"
    assert result.key_prefix == "vk_admin_..."
    assert result.deactivated_previous is True
    assert result.tenant_id == "t_1"


# ── 11. health ────────────────────────────────────────────────────────────────


@respx.mock
def test_health():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "service": "verdicto-api", "db": "ok"},
        )
    )

    client = _client()
    result = client.health()

    assert isinstance(result, dict)
    assert result["ok"] is True
    assert result["service"] == "verdicto-api"


# ── 12. auth_error ────────────────────────────────────────────────────────────


@respx.mock
def test_auth_error():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(
            401,
            json={
                "error": {
                    "code": "AUTH_INVALID",
                    "message": "Invalid API key.",
                }
            },
        )
    )

    client = _client()
    with pytest.raises(AuthenticationError) as exc_info:
        client.health()

    assert exc_info.value.code == "AUTH_INVALID"
    assert exc_info.value.status_code == 401


# ── 13. rate_limit ────────────────────────────────────────────────────────────


@respx.mock
def test_rate_limit():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(
            429,
            json={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests.",
                },
                "retry_after_sec": 5,
            },
        )
    )

    client = _client()
    with pytest.raises(RateLimitError) as exc_info:
        client.health()

    assert exc_info.value.retry_after_sec == 5


# ── 14. replay_detected ──────────────────────────────────────────────────────


@respx.mock
def test_replay_detected():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(
            409,
            json={
                "error": {
                    "code": "REPLAY_DETECTED",
                    "message": "Agent pass already used.",
                }
            },
        )
    )

    client = _client()
    with pytest.raises(ReplayDetectedError) as exc_info:
        client.verify_agent(agent_pass="eyJ...")

    assert exc_info.value.code == "REPLAY_DETECTED"


# ── 15. idempotency_conflict ─────────────────────────────────────────────────


@respx.mock
def test_idempotency_conflict():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(
            409,
            json={
                "error": {
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": "Different body.",
                }
            },
        )
    )

    client = _client()
    with pytest.raises(IdempotencyConflictError) as exc_info:
        client.verify_agent(agent_pass="eyJ...", idempotency_key="ik_1")

    assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"


# ── 16. validation_error ─────────────────────────────────────────────────────


@respx.mock
def test_validation_error():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(
            422,
            json={"detail": "Validation failed."},
        )
    )

    client = _client()
    with pytest.raises(ValidationError):
        client.verify_agent(agent_pass="eyJ...")


# ── 17. not_found ─────────────────────────────────────────────────────────────


@respx.mock
def test_not_found():
    respx.get(f"{BASE_URL}/v1/cases/nonexistent").mock(
        return_value=httpx.Response(
            404,
            json={
                "detail": {
                    "code": "CASE_NOT_FOUND",
                    "message": "Case not found.",
                }
            },
        )
    )

    client = _client()
    with pytest.raises(NotFoundError) as exc_info:
        client.get_case("nonexistent")

    assert exc_info.value.code == "CASE_NOT_FOUND"


# ── 18. server_error ─────────────────────────────────────────────────────────


@respx.mock
def test_server_error():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(
            500,
            json={
                "error": {
                    "code": "INTERNAL",
                    "message": "Server error.",
                }
            },
        )
    )

    client = _client()
    with pytest.raises(ServerError) as exc_info:
        client.health()

    assert exc_info.value.code == "INTERNAL"
    assert exc_info.value.status_code == 500


# ── 19. auto_idempotency_key ─────────────────────────────────────────────────


@respx.mock
def test_auto_idempotency_key():
    route = respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "tenant_id": "t_1",
                "decision": "allow",
                "confidence": 0.95,
                "reason_codes": [],
                "policy_v": "v0",
                "request_id": "req_auto",
                "verification_id": "ver_auto",
                "proof_jwt": "eyJ.auto.sig",
            },
        )
    )

    client = _client()
    client.verify_agent(agent_pass="eyJ...")

    assert route.called
    request = route.calls[0].request
    idem_key = request.headers.get("idempotency-key")
    assert idem_key is not None
    assert len(idem_key) > 0


# ── 20. context_manager ──────────────────────────────────────────────────────


@respx.mock
def test_context_manager():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "service": "verdicto-api", "db": "ok"},
        )
    )

    with VerdictoClient(api_key=API_KEY, base_url=BASE_URL) as client:
        result = client.health()

    assert result["ok"] is True


# ── 21. user_agent_header ────────────────────────────────────────────────────


@respx.mock
def test_user_agent_header():
    route = respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "service": "verdicto-api", "db": "ok"},
        )
    )

    client = _client()
    client.health()

    assert route.called
    request = route.calls[0].request
    user_agent = request.headers.get("user-agent")
    assert user_agent is not None
    assert "verdicto-python/" in user_agent

"""Tests for AsyncVerdictoClient."""

from __future__ import annotations

import httpx
import pytest
import respx

from verdicto import AsyncVerdictoClient, AuthenticationError, RateLimitError, ServerError
from verdicto.types import AgentPass, CasesList, ProofVerifyResult, StepUpSession, VerifyResult


BASE_URL = "https://api.test"


@pytest.mark.asyncio
@respx.mock
async def test_async_verify_agent_allow():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(200, json={
            "ok": True,
            "tenant_id": "t_test",
            "decision": "allow",
            "confidence": 0.97,
            "reason_codes": [],
            "policy_v": "v1",
            "request_id": "req_abc",
            "verification_id": "ver_123",
            "proof_jwt": "eyJ...",
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    result = await client.verify_agent(requested_action="checkout.purchase")
    assert isinstance(result, VerifyResult)
    assert result.decision == "allow"
    assert result.ok is True
    assert result.confidence == 0.97
    assert result.proof_jwt == "eyJ..."
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_issue_agent_pass():
    respx.post(f"{BASE_URL}/v1/agent/pass/issue").mock(
        return_value=httpx.Response(200, json={
            "agent_pass": "eyJhbGciOi...",
            "request_id": "req_pass_1",
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    result = await client.issue_agent_pass(
        sub="user_42",
        scopes=["checkout.purchase"],
        currency_allowlist=["USD"],
        merchant_allowlist=["m_demo_1"],
    )
    assert isinstance(result, AgentPass)
    assert result.agent_pass == "eyJhbGciOi..."
    assert result.request_id == "req_pass_1"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_list_cases():
    respx.get(f"{BASE_URL}/v1/cases").mock(
        return_value=httpx.Response(200, json={
            "ok": True,
            "tenant_id": "t_test",
            "cases": [
                {
                    "id": "case_1",
                    "decision": "allow",
                    "confidence": 0.95,
                    "reason_codes": [],
                    "created_at": "2026-03-20T10:00:00Z",
                },
            ],
            "limit": 50,
            "offset": 0,
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    result = await client.list_cases()
    assert isinstance(result, CasesList)
    assert result.ok is True
    assert len(result.cases) == 1
    assert result.cases[0].id == "case_1"
    assert result.cases[0].decision == "allow"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_verify_proof():
    respx.post(f"{BASE_URL}/v1/proofs/verify").mock(
        return_value=httpx.Response(200, json={
            "ok": True,
            "verification_id": "ver_123",
            "decision": "allow",
            "reason_codes": [],
            "issued_at": "2026-03-20T10:00:00Z",
            "request_id": "req_proof_1",
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    result = await client.verify_proof(proof_jwt="eyJ...")
    assert isinstance(result, ProofVerifyResult)
    assert result.ok is True
    assert result.verification_id == "ver_123"
    assert result.decision == "allow"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_approve_step_up():
    respx.post(f"{BASE_URL}/v1/step-up/tok/approve").mock(
        return_value=httpx.Response(200, json={
            "ok": True,
            "session": {
                "status": "approved",
                "verification_id": "ver_456",
                "proof_jwt": "eyJstepup...",
                "decision": "allow",
            },
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    result = await client.approve_step_up("tok")
    assert isinstance(result, StepUpSession)
    assert result.ok is True
    assert result.status == "approved"
    assert result.verification_id == "ver_456"
    assert result.proof_jwt == "eyJstepup..."
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_health():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(200, json={
            "status": "ok",
            "version": "0.1.0",
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    result = await client.health()
    assert isinstance(result, dict)
    assert result["status"] == "ok"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_auth_error():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(401, json={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid API key",
            },
        })
    )
    client = AsyncVerdictoClient(api_key="vk_bad", base_url=BASE_URL)
    with pytest.raises(AuthenticationError):
        await client.verify_agent(requested_action="checkout.purchase")
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_rate_limit_error():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(429, json={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests",
            },
            "retry_after_sec": 0.01,
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        await client.verify_agent(requested_action="checkout.purchase")
    assert exc_info.value.retry_after_sec == 0.01
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_server_error():
    respx.post(f"{BASE_URL}/v1/verify/agent").mock(
        return_value=httpx.Response(500, json={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            },
        })
    )
    client = AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL)
    with pytest.raises(ServerError):
        await client.verify_agent(requested_action="checkout.purchase")
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_context_manager():
    respx.get(f"{BASE_URL}/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    async with AsyncVerdictoClient(api_key="vk_test", base_url=BASE_URL) as client:
        result = await client.health()
        assert result["status"] == "ok"

"""Async Python client for the Verdicto API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ._http import (
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    build_headers,
    map_error,
    new_idempotency_key,
    retry_delay,
    should_retry,
)
from .types import (
    AgentPass,
    Case,
    CasesList,
    ProofVerifyResult,
    RotateKeyResult,
    StepUpSession,
    VerifyResult,
)


class AsyncVerdictoClient:
    """Async Python client for the Verdicto API.

    Usage::

        async with AsyncVerdictoClient(api_key="vk_...") as client:
            result = await client.verify_agent(
                agent_pass=pass_jwt,
                requested_action="checkout.purchase",
                amount_cents=1500,
            )
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://127.0.0.1:8000",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        headers = build_headers(self._api_key, idempotency_key)

        for attempt in range(MAX_RETRIES + 1):
            response = await self._client.request(
                method, url, headers=headers, json=json, params=params
            )

            if response.status_code < 400:
                return response.json() if response.content else {}

            try:
                body = response.json()
            except Exception:
                body = {"message": response.text}

            if should_retry(response.status_code) and attempt < MAX_RETRIES:
                delay = retry_delay(response.status_code, body, attempt)
                await asyncio.sleep(delay)
                continue

            raise map_error(response.status_code, body)

    # ── Core Verification ───────────────────────────────────────────

    async def issue_agent_pass(
        self,
        *,
        sub: str,
        ttl_seconds: int = 900,
        scopes: list[str],
        max_amount_cents: int | None = None,
        currency_allowlist: list[str],
        merchant_allowlist: list[str],
    ) -> AgentPass:
        body: dict[str, Any] = {
            "sub": sub,
            "ttl_seconds": ttl_seconds,
            "scopes": scopes,
            "currency_allowlist": currency_allowlist,
            "merchant_allowlist": merchant_allowlist,
        }
        if max_amount_cents is not None:
            body["max_amount_cents"] = max_amount_cents
        data = await self._request("POST", "/v1/agent/pass/issue", json=body)
        return AgentPass(
            agent_pass=data.get("agent_pass", ""),
            request_id=data.get("request_id", ""),
        )

    async def verify_agent(
        self,
        *,
        agent_pass: str | None = None,
        requested_action: str = "",
        amount_cents: int | None = None,
        currency: str | None = None,
        merchant_id: str | None = None,
        subject_id: str | None = None,
        idempotency_key: str | None = None,
        context: dict | None = None,
    ) -> VerifyResult:
        if idempotency_key is None:
            idempotency_key = new_idempotency_key()
        body: dict[str, Any] = {}
        if agent_pass is not None:
            body["agent_pass"] = agent_pass
        if requested_action:
            body["requested_action"] = requested_action
        if amount_cents is not None:
            body["amount_cents"] = amount_cents
        if currency is not None:
            body["currency"] = currency
        if merchant_id is not None:
            body["merchant_id"] = merchant_id
        if subject_id is not None:
            body["subject_id"] = subject_id
        if context is not None:
            body["context"] = context
        data = await self._request(
            "POST", "/v1/verify/agent", json=body, idempotency_key=idempotency_key
        )
        return VerifyResult(
            ok=data.get("ok", False),
            tenant_id=data.get("tenant_id", ""),
            decision=data.get("decision", "deny"),
            confidence=data.get("confidence", 0.0),
            reason_codes=data.get("reason_codes", []),
            policy_v=data.get("policy_v", ""),
            request_id=data.get("request_id", ""),
            verification_id=data.get("verification_id", ""),
            proof_jwt=data.get("proof_jwt"),
            step_up_url=data.get("step_up_url"),
            step_up_expires_at=data.get("step_up_expires_at"),
        )

    # ── Proofs ──────────────────────────────────────────────────────

    async def verify_proof(self, proof_jwt: str) -> ProofVerifyResult:
        data = await self._request(
            "POST", "/v1/proofs/verify", json={"proof_jwt": proof_jwt}
        )
        return ProofVerifyResult(
            ok=data.get("ok", False),
            verification_id=data.get("verification_id") or data.get("claims", {}).get("verification_id"),
            decision=data.get("decision") or data.get("claims", {}).get("decision"),
            reason_codes=data.get("reason_codes", []),
            issued_at=data.get("issued_at"),
            request_id=data.get("request_id", ""),
        )

    async def get_proof_bundle(self, verification_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/proofs/{verification_id}/bundle")

    # ── Cases ───────────────────────────────────────────────────────

    async def list_cases(self, *, limit: int = 50, offset: int = 0) -> CasesList:
        data = await self._request(
            "GET", "/v1/cases", params={"limit": limit, "offset": offset}
        )
        cases = [
            Case(
                id=c.get("id", ""),
                decision=c.get("decision"),
                confidence=c.get("confidence"),
                reason_codes=c.get("reason_codes", []),
                created_at=c.get("created_at"),
            )
            for c in data.get("cases", [])
        ]
        return CasesList(
            ok=data.get("ok", False),
            tenant_id=data.get("tenant_id", ""),
            cases=cases,
            limit=data.get("limit", limit),
            offset=data.get("offset", offset),
        )

    async def get_case(self, case_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/cases/{case_id}")

    # ── Audit ───────────────────────────────────────────────────────

    async def get_audit_trail(self, verification_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/audit/{verification_id}")

    # ── Step-Up ─────────────────────────────────────────────────────

    async def approve_step_up(self, token: str) -> StepUpSession:
        data = await self._request("POST", f"/v1/step-up/{token}/approve")
        session = data.get("session", data)
        return StepUpSession(
            ok=data.get("ok", True),
            status=session.get("status", "approved"),
            verification_id=session.get("verification_id", data.get("verification_id", "")),
            proof_jwt=session.get("proof_jwt"),
            decision=session.get("decision"),
        )

    async def deny_step_up(self, token: str) -> StepUpSession:
        data = await self._request("POST", f"/v1/step-up/{token}/deny")
        session = data.get("session", data)
        return StepUpSession(
            ok=data.get("ok", True),
            status=session.get("status", "denied"),
            verification_id=session.get("verification_id", data.get("verification_id", "")),
            proof_jwt=session.get("proof_jwt"),
            decision=session.get("decision"),
        )

    # ── Webhooks ────────────────────────────────────────────────────

    async def list_events(self, *, event_type: str | None = None, limit: int = 50) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if event_type:
            params["type"] = event_type
        return await self._request("GET", "/v1/events", params=params)

    async def list_deliveries(self, *, status: str | None = None, limit: int = 50) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._request("GET", "/v1/deliveries", params=params)

    async def retry_delivery(self, delivery_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/v1/webhooks/deliveries/{delivery_id}/retry")

    async def list_webhook_endpoints(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/webhooks/endpoints")

    # ── Admin ───────────────────────────────────────────────────────

    async def rotate_key(self, *, name: str = "rotated", deactivate_previous: bool = True) -> RotateKeyResult:
        data = await self._request(
            "POST", "/v1/keys/rotate",
            params={"deactivate_previous": str(deactivate_previous).lower(), "name": name},
        )
        return RotateKeyResult(
            ok=data.get("ok", True), tenant_id=data.get("tenant_id", ""),
            key=data.get("key", ""), key_prefix=data.get("key_prefix", ""),
            name=data.get("name", name), deactivated_previous=data.get("deactivated_previous", False),
            created_at=data.get("created_at", ""), request_id=data.get("request_id", ""),
        )

    # ── Health ──────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    # ── Lifecycle ───────────────────────────────────────────────────

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncVerdictoClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

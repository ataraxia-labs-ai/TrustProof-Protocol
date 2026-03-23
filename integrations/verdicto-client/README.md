# verdicto

The official Python client for the Verdicto trust infrastructure API.

[![PyPI version](https://img.shields.io/pypi/v/verdicto.svg)](https://pypi.org/project/verdicto/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/verdicto/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)

## Install

```bash
pip install verdicto
```

## Quick Start

```python
from verdicto import VerdictoClient

client = VerdictoClient(api_key="vk_live_...")

# Issue an Agent Pass with policy constraints
agent_pass = client.issue_agent_pass(
    sub="shopping-agent-v1",
    ttl_seconds=900,
    scopes=["checkout.purchase"],
    max_amount_cents=5000,
    currency_allowlist=["USD"],
    merchant_allowlist=["m_demo_1"],
)

# Verify an action against the policy
result = client.verify_agent(
    agent_pass=agent_pass.agent_pass,
    requested_action="checkout.purchase",
    amount_cents=1500,
    currency="USD",
    merchant_id="m_demo_1",
)

print(result.decision)        # "allow"
print(result.proof_jwt[:40])  # cryptographic Trust Proof
```

## Features

- **Agent Passes** -- issue scoped, time-limited JWTs with embedded policy constraints
- **Verify Agent** -- evaluate actions against policy with a single call
- **Trust Proofs** -- cryptographic proof JWTs for every verification decision
- **Evidence Bundles** -- export full proof bundles for compliance and legal
- **Step-Up Verification** -- velocity and risk-triggered human approval flows
- **Audit Trail** -- tamper-evident logs for every verification
- **Webhook Events** -- event delivery with retry and endpoint management
- **Async Support** -- first-class `AsyncVerdictoClient` with identical API
- **Typed Exceptions** -- granular error hierarchy for precise error handling
- **Zero deps beyond httpx** -- minimal dependency footprint

## Sync vs Async

**Sync:**

```python
from verdicto import VerdictoClient

with VerdictoClient(api_key="vk_live_...") as client:
    result = client.verify_agent(
        agent_pass=pass_jwt,
        requested_action="checkout.purchase",
        amount_cents=1500,
        currency="USD",
        merchant_id="m_demo_1",
    )
    print(result.decision)
```

**Async:**

```python
import asyncio
from verdicto import AsyncVerdictoClient

async def main():
    async with AsyncVerdictoClient(api_key="vk_live_...") as client:
        result = await client.verify_agent(
            agent_pass=pass_jwt,
            requested_action="checkout.purchase",
            amount_cents=1500,
            currency="USD",
            merchant_id="m_demo_1",
        )
        print(result.decision)

asyncio.run(main())
```

## Error Handling

All errors inherit from `VerdictoError` and carry `message`, `code`, `status_code`, and `request_id` attributes.

```python
from verdicto import (
    VerdictoClient,
    VerdictoError,
    AuthenticationError,
    RateLimitError,
    ReplayDetectedError,
)

client = VerdictoClient(api_key="vk_live_...")

try:
    result = client.verify_agent(
        agent_pass=pass_jwt,
        requested_action="checkout.purchase",
        amount_cents=1500,
        currency="USD",
        merchant_id="m_demo_1",
    )
except AuthenticationError:
    # Invalid or missing API key (401)
    print("Check your API key")
except RateLimitError as exc:
    # Too many requests (429) -- back off
    print(f"Rate limited. Retry after {exc.retry_after_sec}s")
except ReplayDetectedError:
    # Agent pass was already consumed (409)
    print("Agent pass replay detected -- issue a new pass")
except VerdictoError as exc:
    # Catch-all for any Verdicto API error
    print(f"[{exc.code}] {exc.message} (request_id={exc.request_id})")
```

**Exception hierarchy:**

| Exception | HTTP Status | When |
|---|---|---|
| `AuthenticationError` | 401 | Invalid or missing API key |
| `ValidationError` | 400 / 422 | Malformed request body |
| `NotFoundError` | 404 | Resource does not exist |
| `ReplayDetectedError` | 409 | Agent pass already consumed |
| `IdempotencyConflictError` | 409 | Same idempotency key, different body |
| `RateLimitError` | 429 | Rate limit exceeded |
| `ServerError` | 5xx | Verdicto server error |

## Methods

| Method | HTTP | Return Type |
|---|---|---|
| `issue_agent_pass(...)` | `POST /v1/agent/pass/issue` | `AgentPass` |
| `verify_agent(...)` | `POST /v1/verify/agent` | `VerifyResult` |
| `verify_proof(proof_jwt)` | `POST /v1/proofs/verify` | `ProofVerifyResult` |
| `get_proof_bundle(verification_id)` | `GET /v1/proofs/{id}/bundle` | `dict` |
| `list_cases(...)` | `GET /v1/cases` | `CasesList` |
| `get_case(case_id)` | `GET /v1/cases/{id}` | `dict` |
| `get_audit_trail(verification_id)` | `GET /v1/audit/{id}` | `dict` |
| `approve_step_up(token)` | `POST /v1/step-up/{token}/approve` | `StepUpSession` |
| `deny_step_up(token)` | `POST /v1/step-up/{token}/deny` | `StepUpSession` |
| `list_events(...)` | `GET /v1/events` | `dict` |
| `list_deliveries(...)` | `GET /v1/deliveries` | `dict` |
| `retry_delivery(delivery_id)` | `POST /v1/webhooks/deliveries/{id}/retry` | `dict` |
| `list_webhook_endpoints()` | `GET /v1/webhooks/endpoints` | `dict` |
| `rotate_key(...)` | `POST /v1/keys/rotate` | `RotateKeyResult` |
| `health()` | `GET /health` | `dict` |

All methods are available on both `VerdictoClient` (sync) and `AsyncVerdictoClient` (async, with `await`).

## Related

- [trustproof](https://github.com/ataraxia-labs-ai/verdicto/tree/main/trustproof) -- open protocol specification
- [verdicto-langchain](https://github.com/ataraxia-labs-ai/verdicto/tree/main/trustproof/integrations/verdicto-langchain) -- LangChain integration
- [TrustProof Protocol](https://docs.verdicto.dev/protocol) -- full protocol specification

## License

Apache-2.0

"""Verification tools — require Verdicto API."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import ServerConfig


def _get_client(config: ServerConfig) -> Any:
    if not config.api_configured:
        return None
    from verdicto import VerdictoClient
    return VerdictoClient(api_key=config.api_key or "", base_url=config.api_url)


def register_verify_tools(mcp: FastMCP, config: ServerConfig) -> None:

    @mcp.tool()
    def verify_agent_action(
        requested_action: str,
        subject_id: str = "mcp-agent",
        amount_cents: int | None = None,
        currency: str | None = None,
        merchant_id: str | None = None,
    ) -> dict:
        """Verify an AI agent action against trust policy. Returns allow/deny/step_up with a signed Trust Proof.

        Use BEFORE performing sensitive actions: payments, data access, code changes, API calls.

        Args:
            requested_action: Action to verify (e.g. "checkout.purchase", "data.export")
            subject_id: Agent identifier
            amount_cents: Transaction amount in cents
            currency: Currency code (e.g. "USD")
            merchant_id: Merchant or service identifier
        """
        client = _get_client(config)
        if client is None:
            return {"error": "Verdicto API not configured. Set VERDICTO_API_KEY environment variable."}
        try:
            # Issue pass then verify
            pass_result = client.issue_agent_pass(
                sub=subject_id,
                scopes=[requested_action, "mcp.tool_invocation"],
                max_amount_cents=amount_cents,
                currency_allowlist=[currency] if currency else ["USD"],
                merchant_allowlist=[merchant_id] if merchant_id else [subject_id],
            )
            result = client.verify_agent(
                agent_pass=pass_result.agent_pass,
                requested_action=requested_action,
                subject_id=subject_id,
                amount_cents=amount_cents,
                currency=currency,
                merchant_id=merchant_id,
            )
            return {
                "decision": result.decision,
                "verification_id": result.verification_id,
                "confidence": result.confidence,
                "reason_codes": result.reason_codes,
                "proof_jwt": result.proof_jwt,
                "step_up_url": result.step_up_url,
            }
        except Exception as e:
            return {"error": str(e)}
        finally:
            client.close()

    @mcp.tool()
    def issue_agent_pass(
        sub: str,
        scopes: list[str],
        ttl_seconds: int = 900,
        max_amount_cents: int | None = None,
        currency_allowlist: list[str] | None = None,
        merchant_allowlist: list[str] | None = None,
    ) -> dict:
        """Issue a constrained Agent Pass (signed JWT with embedded policy).

        Defines what an agent is allowed to do: which actions, max amounts, allowed currencies/merchants, TTL.

        Args:
            sub: Agent subject identifier
            scopes: Allowed action scopes (e.g. ["checkout.purchase"])
            ttl_seconds: Validity in seconds (60-86400)
            max_amount_cents: Max transaction amount in cents
            currency_allowlist: Allowed currencies
            merchant_allowlist: Allowed merchants
        """
        client = _get_client(config)
        if client is None:
            return {"error": "Verdicto API not configured. Set VERDICTO_API_KEY environment variable."}
        try:
            result = client.issue_agent_pass(
                sub=sub, scopes=scopes, ttl_seconds=ttl_seconds,
                max_amount_cents=max_amount_cents,
                currency_allowlist=currency_allowlist or ["USD"],
                merchant_allowlist=merchant_allowlist or [sub],
            )
            return {"agent_pass": result.agent_pass, "request_id": result.request_id}
        except Exception as e:
            return {"error": str(e)}
        finally:
            client.close()

    @mcp.tool()
    def get_audit_trail(verification_id: str) -> dict:
        """Get the tamper-evident audit trail for a verification decision.

        Args:
            verification_id: ID from a previous verify_agent_action call
        """
        client = _get_client(config)
        if client is None:
            return {"error": "Verdicto API not configured."}
        try:
            return client.get_audit_trail(verification_id)
        except Exception as e:
            return {"error": str(e)}
        finally:
            client.close()

    @mcp.tool()
    def get_evidence_bundle(verification_id: str) -> dict:
        """Export a complete evidence bundle for compliance or legal use.

        Contains the Trust Proof JWT, policy snapshot, evidence hashes, and bundle signature.

        Args:
            verification_id: ID from a previous verify_agent_action call
        """
        client = _get_client(config)
        if client is None:
            return {"error": "Verdicto API not configured."}
        try:
            return client.get_proof_bundle(verification_id)
        except Exception as e:
            return {"error": str(e)}
        finally:
            client.close()

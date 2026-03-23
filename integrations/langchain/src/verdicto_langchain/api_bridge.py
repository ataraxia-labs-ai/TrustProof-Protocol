"""Bridge between verdicto-langchain and the Verdicto API.

All API operations are optional and non-blocking. If the API is unreachable,
local TrustProof generation continues unaffected.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from .config import VerdictoConfig

logger = logging.getLogger("verdicto_langchain.api_bridge")


class APIBridge:
    """Sends verification requests to the Verdicto API for dashboard persistence.

    Lazy-initializes the VerdictoClient. Caches the Agent Pass across calls.
    All operations are guarded by api_fail_silently — never crashes the agent.
    """

    def __init__(self, config: VerdictoConfig) -> None:
        self._config = config
        self._client: Any = None
        self._agent_pass_jwt: str | None = None
        self._agent_pass_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._config.api_enabled

    def _get_client(self) -> Any:
        """Lazy-initialize the VerdictoClient."""
        if self._client is not None:
            return self._client
        try:
            from verdicto import VerdictoClient

            self._client = VerdictoClient(
                api_key=self._config.verdicto_api_key or "",
                base_url=self._config.verdicto_api_url or "",
            )
        except ImportError:
            logger.warning(
                "verdicto package not installed. Install with: pip install verdicto"
            )
            return None
        except Exception as exc:
            logger.warning("Failed to create VerdictoClient: %s", exc)
            return None
        return self._client

    def ensure_agent_pass(self) -> str | None:
        """Issue an Agent Pass if not already cached. Thread-safe."""
        if not self.enabled:
            return None
        with self._agent_pass_lock:
            if self._agent_pass_jwt is not None:
                return self._agent_pass_jwt
            client = self._get_client()
            if client is None:
                return None
            try:
                result = client.issue_agent_pass(
                    sub=self._config.agent_id,
                    ttl_seconds=self._config.agent_pass_ttl_seconds,
                    scopes=self._config.agent_pass_scopes,
                    max_amount_cents=self._config.agent_pass_max_amount_cents,
                    currency_allowlist=self._config.agent_pass_currency_allowlist,
                    merchant_allowlist=self._config.agent_pass_merchant_allowlist
                    or [self._config.agent_id],
                )
                self._agent_pass_jwt = result.agent_pass
                logger.info("Agent Pass issued for %s", self._config.agent_id)
                return self._agent_pass_jwt
            except Exception as exc:
                if self._config.api_fail_silently:
                    logger.warning("Failed to issue Agent Pass: %s", exc)
                    return None
                raise

    def send_verification(
        self,
        *,
        action: str,
        subject_id: str | None = None,
        amount_cents: int | None = None,
        currency: str | None = None,
        merchant_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Send a verification request to the Verdicto API.

        If api_send_async is True, runs in a daemon background thread.
        """
        if not self.enabled:
            return

        def _do_send() -> None:
            client = self._get_client()
            if client is None:
                return
            agent_pass = self.ensure_agent_pass()
            try:
                result = client.verify_agent(
                    agent_pass=agent_pass,
                    requested_action=action,
                    subject_id=subject_id or self._config.agent_id,
                    amount_cents=amount_cents,
                    currency=currency,
                    merchant_id=merchant_id,
                    context=context,
                )
                logger.info(
                    "API verification: decision=%s verification_id=%s",
                    result.decision,
                    result.verification_id,
                )
            except Exception as exc:
                if self._config.api_fail_silently:
                    logger.warning("API verification failed (non-fatal): %s", exc)
                else:
                    raise

        if self._config.api_send_async:
            thread = threading.Thread(target=_do_send, daemon=True)
            thread.start()
        else:
            _do_send()

    def close(self) -> None:
        """Close the underlying HTTP client if present."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

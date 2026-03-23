"""Optional bridge to the Verdicto API for dashboard persistence."""

from __future__ import annotations

import logging
import threading
from typing import Any

from .config import AutoresearchConfig

logger = logging.getLogger("verdicto_autoresearch.api_bridge")


class APIBridge:
    """Sends experiment verifications to the Verdicto API."""

    def __init__(self, config: AutoresearchConfig) -> None:
        self._config = config
        self._client: Any = None
        self._agent_pass_jwt: str | None = None
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._config.api_enabled

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from verdicto import VerdictoClient
            self._client = VerdictoClient(
                api_key=self._config.verdicto_api_key or "",
                base_url=self._config.verdicto_api_url or "",
            )
        except ImportError:
            logger.warning("verdicto package not installed. Install with: pip install verdicto")
            return None
        except Exception as exc:
            logger.warning("Failed to create VerdictoClient: %s", exc)
            return None
        return self._client

    def send_verification(self, *, action: str, context: dict[str, Any] | None = None) -> None:
        if not self.enabled:
            return

        def _do_send() -> None:
            client = self._get_client()
            if client is None:
                return
            try:
                result = client.verify_agent(
                    requested_action=action,
                    subject_id=self._config.researcher_id,
                    context=context,
                )
                logger.info("API: decision=%s id=%s", result.decision, result.verification_id)
            except Exception as exc:
                logger.warning("API verification failed (non-fatal): %s", exc)

        thread = threading.Thread(target=_do_send, daemon=True)
        thread.start()

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

"""VerdictoCallbackHandler — TrustProof generation for LangChain agents.

Add to any agent to generate signed, chained audit proofs for every tool call.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from trustproof import append, verify_chain
from trustproof.chain import canonical_json, sha256_hex

from .api_bridge import APIBridge
from .proof_store import ProofStore
from .config import VerdictoConfig, ensure_keypair


class VerdictoCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that generates TrustProofs for agent actions.

    Usage::

        handler = VerdictoCallbackHandler(agent_id="my-agent")
        agent.invoke({"input": "..."}, config={"callbacks": [handler]})
        proofs = handler.get_proof_chain()
    """

    def __init__(
        self,
        config: VerdictoConfig | None = None,
        *,
        agent_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.config = config or VerdictoConfig()
        if agent_id is not None:
            self.config.agent_id = agent_id

        self._private_pem, self._public_pem = ensure_keypair(self.config)
        self._store = ProofStore()
        self._pending: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._api_bridge: APIBridge | None = (
            APIBridge(self.config) if self.config.api_enabled else None
        )

    # ── Tool callbacks ──────────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        rid = str(run_id) if run_id else str(uuid.uuid4())

        input_data = {"tool": tool_name, "input": input_str}
        input_hash = sha256_hex(canonical_json(input_data))

        pending = {
            "action": f"langchain.tool_call.{tool_name}",
            "input_hash": input_hash,
            "input_data": input_data,
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        with self._lock:
            self._pending[rid] = pending

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id) if run_id else ""
        with self._lock:
            pending = self._pending.pop(rid, None)

        if pending is None:
            return

        output_data = {"output": output}
        output_hash = sha256_hex(canonical_json(output_data))

        self._sign_and_store(
            action=pending["action"],
            input_hash=pending["input_hash"],
            output_hash=output_hash,
            decision="allow",
            reason_codes=[],
            timestamp=pending["started_at"],
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id) if run_id else ""
        with self._lock:
            pending = self._pending.pop(rid, None)

        if pending is None:
            return

        output_data = {"error": str(error)}
        output_hash = sha256_hex(canonical_json(output_data))

        self._sign_and_store(
            action=pending["action"],
            input_hash=pending["input_hash"],
            output_hash=output_hash,
            decision="deny",
            reason_codes=["tool_error"],
            timestamp=pending["started_at"],
        )

    # ── Chain callbacks ─────────────────────────────────────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        if not self.config.trace_chain_steps:
            return

        rid = str(run_id) if run_id else str(uuid.uuid4())
        chain_name = serialized.get("name", serialized.get("id", ["unknown"])[-1] if isinstance(serialized.get("id"), list) else "unknown")
        input_data = {"chain": chain_name, "inputs": inputs}
        input_hash = sha256_hex(canonical_json(input_data))

        with self._lock:
            self._pending[rid] = {
                "action": f"langchain.chain_step.{chain_name}",
                "input_hash": input_hash,
                "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        if not self.config.trace_chain_steps:
            return

        rid = str(run_id) if run_id else ""
        with self._lock:
            pending = self._pending.pop(rid, None)
        if pending is None:
            return

        output_hash = sha256_hex(canonical_json({"outputs": outputs}))
        self._sign_and_store(
            action=pending["action"],
            input_hash=pending["input_hash"],
            output_hash=output_hash,
            decision="allow",
            reason_codes=[],
            timestamp=pending["started_at"],
        )

    # ── LLM callbacks ──────────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        if not self.config.trace_llm_calls:
            return

        rid = str(run_id) if run_id else str(uuid.uuid4())
        input_data = {"prompts_hash": sha256_hex(canonical_json(prompts))}
        input_hash = sha256_hex(canonical_json(input_data))

        with self._lock:
            self._pending[rid] = {
                "action": "langchain.llm_decision",
                "input_hash": input_hash,
                "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        if not self.config.trace_llm_calls:
            return

        rid = str(run_id) if run_id else ""
        with self._lock:
            pending = self._pending.pop(rid, None)
        if pending is None:
            return

        output_str = str(response) if response else ""
        output_hash = sha256_hex(canonical_json({"response_hash": sha256_hex(output_str)}))
        self._sign_and_store(
            action=pending["action"],
            input_hash=pending["input_hash"],
            output_hash=output_hash,
            decision="allow",
            reason_codes=[],
            timestamp=pending["started_at"],
        )

    # ── Core signing ────────────────────────────────────────────────

    def _sign_and_store(
        self,
        *,
        action: str,
        input_hash: str,
        output_hash: str,
        decision: str,
        reason_codes: list[str],
        timestamp: str,
    ) -> None:
        claims: dict[str, Any] = {
            "subject": {"type": "agent", "id": self.config.agent_id},
            "action": action,
            "resource": {"type": "langchain", "id": action},
            "policy": {
                "policy_v": "v0",
                "scopes": self.config.policy_scopes,
                "constraints": {},
            },
            "result": {"decision": decision, "reason_codes": reason_codes},
            "hashes": {"input_hash": input_hash, "output_hash": output_hash},
            "timestamp": timestamp,
            "jti": str(uuid.uuid4()),
        }

        if self.config.protocol_refs:
            claims["protocol_refs"] = self.config.protocol_refs
        if self.config.vc_profile:
            claims["vc_profile"] = self.config.vc_profile

        prev = self._store.get_latest()
        jwt_token = append(prev, claims, self._private_pem)
        self._store.append_proof(jwt_token)

        # Send to Verdicto API if configured (non-blocking, fire-and-forget)
        if self._api_bridge is not None:
            self._api_bridge.send_verification(
                action=action,
                subject_id=self.config.agent_id,
                context={"source": "verdicto_langchain", "action": action},
            )

    # ── Public API ──────────────────────────────────────────────────

    def get_proof_chain(self) -> list[str]:
        """Return all signed TrustProof JWTs generated during the run."""
        return self._store.get_chain()

    def get_latest_proof(self) -> str | None:
        """Return the most recent proof, or None."""
        return self._store.get_latest()

    def verify_chain(self) -> dict[str, Any]:
        """Verify the entire proof chain for tamper evidence."""
        return verify_chain(self._store.get_chain(), self._public_pem)

    def export_bundle(self) -> dict[str, Any]:
        """Export the chain with metadata."""
        return self._store.export_bundle()

    def export_json(self) -> str:
        """Export the chain as a JSON array."""
        return self._store.export_json()

    def clear(self) -> None:
        """Reset the handler for a new run."""
        self._store.clear()
        with self._lock:
            self._pending.clear()

    def close(self) -> None:
        """Close the API bridge HTTP client if present."""
        if self._api_bridge is not None:
            self._api_bridge.close()

    def __enter__(self) -> VerdictoCallbackHandler:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

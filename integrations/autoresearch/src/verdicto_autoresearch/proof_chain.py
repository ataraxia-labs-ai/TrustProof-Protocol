"""Thread-safe proof chain for experiment loops."""

from __future__ import annotations

import json
import threading
from typing import Any

from trustproof import append, verify_chain


class ProofChain:
    """Accumulates signed TrustProof JWTs during an experiment session."""

    def __init__(self) -> None:
        self._chain: list[str] = []
        self._lock = threading.Lock()

    def append_proof(self, claims: dict[str, Any], private_key_pem: str) -> str:
        """Sign claims, chain-link to previous, and store."""
        with self._lock:
            prev = self._chain[-1] if self._chain else None
        jwt_token = append(prev, claims, private_key_pem)
        with self._lock:
            self._chain.append(jwt_token)
        return jwt_token

    def get_chain(self) -> list[str]:
        with self._lock:
            return list(self._chain)

    def get_latest(self) -> str | None:
        with self._lock:
            return self._chain[-1] if self._chain else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._chain)

    def verify(self, public_key_pem: str) -> dict[str, Any]:
        return verify_chain(self.get_chain(), public_key_pem)

    def export_json(self) -> str:
        return json.dumps(self.get_chain())

    def clear(self) -> None:
        with self._lock:
            self._chain.clear()

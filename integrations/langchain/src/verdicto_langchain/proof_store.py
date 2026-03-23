"""Thread-safe in-memory proof store for building chains during a LangChain run."""

from __future__ import annotations

import json
import threading
from typing import Any


class ProofStore:
    """Thread-safe store for accumulating TrustProof JWTs during a run."""

    def __init__(self) -> None:
        self._chain: list[str] = []
        self._lock = threading.Lock()

    def append_proof(self, jwt: str) -> None:
        """Add a signed JWT to the chain."""
        with self._lock:
            self._chain.append(jwt)

    def get_chain(self) -> list[str]:
        """Return all JWTs in order."""
        with self._lock:
            return list(self._chain)

    def get_latest(self) -> str | None:
        """Return the most recent JWT, or None if empty."""
        with self._lock:
            return self._chain[-1] if self._chain else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._chain)

    def export_json(self) -> str:
        """Export the full chain as a JSON array of JWT strings."""
        return json.dumps(self.get_chain())

    def export_bundle(self) -> dict[str, Any]:
        """Export the chain with metadata as a structured bundle."""
        chain = self.get_chain()
        return {
            "bundle_v": "0.1",
            "proof_count": len(chain),
            "proofs": chain,
        }

    def clear(self) -> None:
        """Reset the store for the next run."""
        with self._lock:
            self._chain.clear()

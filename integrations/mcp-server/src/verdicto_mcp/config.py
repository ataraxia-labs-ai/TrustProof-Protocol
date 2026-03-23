"""Server configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ServerConfig:
    api_url: str = "http://127.0.0.1:8000"
    api_key: str | None = None

    @property
    def api_configured(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def from_env(cls) -> ServerConfig:
        return cls(
            api_url=os.getenv("VERDICTO_API_URL", "http://127.0.0.1:8000"),
            api_key=os.getenv("VERDICTO_API_KEY"),
        )

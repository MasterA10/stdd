from __future__ import annotations

from typing import Any

from .providers import ExternalProvider


class ProviderRegistry:
    def __init__(self, external: Any = None):
        self.external = ExternalProvider(callback=external) if callable(external) else ExternalProvider()

    def get(self, name: str):
        if name == "external": return self.external
        if name == "local": return None
        raise ValueError(f"unsupported quiz provider: {name}")

    def permissions(self, name: str) -> dict[str, Any]:
        return {"provider": name, "context": "redacted-scoped", "credentials_in_payload": False, "ack_only": name == "external"}

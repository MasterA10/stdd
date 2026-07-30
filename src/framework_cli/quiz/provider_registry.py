from __future__ import annotations

from typing import Any

from .providers import CommandResponseFixture


class CommandRegistry:
    def __init__(self, fixture: Any = None):
        self.fixture = CommandResponseFixture(callback=fixture) if callable(fixture) else CommandResponseFixture()

    def get(self, name: str):
        if name in {"codex", "claude", "cloud", "antigravity", "generic"}: return self.fixture
        if name == "local": return None
        raise ValueError(f"unsupported quiz command: {name}")

    def permissions(self, name: str) -> dict[str, Any]:
        return {"command": name, "context": "redacted-scoped", "credentials_in_payload": False, "ack_only": name != "local"}


ProviderRegistry = CommandRegistry

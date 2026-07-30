from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class Detection:
    kind: str
    value: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


class Adapter(Protocol):
    id: str
    version: str
    capabilities: set[str]

    def detect(self, root: Path) -> list[Detection]: ...
    def symbols(self, path: Path) -> list[dict[str, Any]]: ...
    def test_commands(self, root: Path) -> list[list[str]]: ...


class BaseAdapter:
    id = "generic"
    version = "1.0"
    capabilities = {"detection", "tests", "static_rules"}

    def detect(self, root: Path) -> list[Detection]:
        return []

    def symbols(self, path: Path) -> list[dict[str, Any]]:
        return []

    def test_commands(self, root: Path) -> list[list[str]]:
        return []

from __future__ import annotations

from pathlib import Path

from ..adapters.registry import detect_project
from ..reporting.models import CommandResult


def scan_project(root: Path) -> CommandResult:
    root = root.resolve()
    detection = detect_project(root)
    from ..index.symbols import update_symbol_index
    indexed = update_symbol_index(root)
    return CommandResult("framework scan", project={"root": str(root), "detections": detection},
                         metadata={"indexed_symbols": indexed, "symbol_count": len(indexed)})

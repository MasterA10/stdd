from __future__ import annotations

from pathlib import Path
from typing import Any

from .lifecycle import record


def host_checkpoint(root: Path, *, observations: list[str] | None = None, files: list[str] | None = None,
                    symbols: list[str] | None = None, gates: list[str] | None = None) -> dict[str, Any]:
    result = record(root, "checkpoint", observations=observations or [], files=files or [],
                    symbols=symbols or [], gates=gates or [])
    return result.to_dict()

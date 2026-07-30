from __future__ import annotations

import shutil
import sys
from pathlib import Path

from ..adapters.registry import discover_adapters
from ..config.loader import load_config
from ..git.repository import GitRepository
from ..reporting.models import CommandResult


def doctor(root: Path) -> CommandResult:
    root = root.resolve()
    result = CommandResult("framework doctor", project={"root": str(root)})
    git = GitRepository(root)
    result.metadata.update({"python": sys.version.split()[0], "uv": shutil.which("uv") is not None,
                            "git": git.snapshot(), "adapters": [a.id for a in discover_adapters(root)],
                            "writable": root.exists() and root.is_dir()})
    try: load_config(root); result.metadata["configuration"] = "valid"
    except FileNotFoundError: result.metadata["configuration"] = "not_initialized"
    except ValueError as exc:
        result.status, result.exit_code = "error", 3
        result.actions.append(str(exc))
    if sys.platform not in {"darwin", "linux"}:
        result.status, result.exit_code = "degraded", 3
        result.actions.append("This platform is not supported by the first release")
    if not git.available:
        result.status = "degraded" if result.exit_code == 0 else result.status
        result.metadata["degraded"] = ["history", "diff", "commit protection"]
    return result

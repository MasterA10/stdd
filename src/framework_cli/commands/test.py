from __future__ import annotations

from pathlib import Path

from ..adapters.registry import discover_adapters
from ..config.loader import load_config
from ..reporting.children import aggregate_children
from ..scripts.runner import ScriptRunner


def run_tests(root: Path):
    root = root.resolve()
    try: config = load_config(root)
    except FileNotFoundError: config = None
    children = []
    for adapter in discover_adapters(root):
        for args in adapter.test_commands(root):
            completed = ScriptRunner(root).run(args, timeout=300)
            children.append({"command": args, "status": "passed" if completed.returncode == 0 else "failed",
                             "exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]})
    return aggregate_children("framework test", children, {"root": str(root), "profile": config.profile if config else None})

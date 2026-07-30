from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..config.loader import load_config
from ..agents.instructions import discover_instruction_chain
from ..reporting.models import CommandResult

DEFAULT_COMMANDS = {"codex": "codex", "claude": "claude", "cloud": "cloud", "antigravity": "antigravity", "generic": "cat"}


def _configured_command(root: Path, target: str) -> list[str]:
    try: raw = load_config(root).learn.get("agents", {}).get(target, {})
    except (FileNotFoundError, ValueError): raw = {}
    configured = raw.get("command") if isinstance(raw, dict) else None
    value = configured or os.environ.get(f"FRAMEWORK_{target.upper()}_COMMAND") or DEFAULT_COMMANDS.get(target, target)
    return shlex.split(value) if isinstance(value, str) else list(value)


def send_package(root: Path, target: str, package: Path, *, dry_run: bool = False) -> CommandResult:
    root = root.resolve(); package = package.resolve()
    result = CommandResult("framework learn handoff send", project={"root": str(root)})
    chain = discover_instruction_chain(root)
    result.metadata["instruction_chain"] = [item.path for item in chain.files]
    if not chain.valid:
        result.status, result.exit_code = "blocked", 1; result.actions.append("Instruction-chain conflict blocks command dispatch"); return result
    try: enabled = bool(load_config(root).learn.get("enabled", False))
    except (FileNotFoundError, ValueError): enabled = False
    if not enabled:
        result.status = "disabled"; return result
    if not package.exists(): result.status, result.exit_code = "error", 2; result.actions.append("Handoff package not found"); return result
    command = _configured_command(root, target)
    if not command: result.status, result.exit_code = "error", 2; result.actions.append("No command configured for target"); return result
    argv = [item.replace("{package}", str(package)) for item in command]
    if not any("{package}" in item for item in command): argv.append(str(package))
    if dry_run:
        result.metadata = {"target": target, "status": "ready", "dry_run": True}
        return result
    if shutil.which(argv[0]) is None:
        result.status, result.exit_code = "degraded", 3; result.metadata = {"target": target, "status": "unavailable"}; return result
    timeout = 120
    try: completed = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        result.status, result.exit_code = "degraded", 3; result.metadata = {"target": target, "status": "timeout"}; return result
    result.metadata = {"target": target, "status": "completed" if completed.returncode == 0 else "failed"}
    if completed.returncode: result.status, result.exit_code = "degraded", 3
    return result


def execute_command(root: Path, target: str, package: Path, *, timeout: int = 120) -> tuple[str, dict[str, Any]]:
    """Run a configured local agent command and keep its output inside the job boundary."""
    command = _configured_command(root, target)
    argv = [item.replace("{package}", str(package)) for item in command]
    if not any("{package}" in item for item in command): argv.append(str(package))
    if not argv or shutil.which(argv[0]) is None: return "failed", {"code": "command-unavailable"}
    try: completed = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired: return "failed", {"code": "command-timeout"}
    if completed.returncode: return "failed", {"code": "command-failed"}
    try:
        import json
        parsed = json.loads(completed.stdout)
    except (ValueError, TypeError): return "failed", {"code": "malformed-command-output"}
    return "completed", parsed if isinstance(parsed, dict) else {"code": "malformed-command-output"}

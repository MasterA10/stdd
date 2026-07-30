from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from ..agents.instructions import discover_instruction_chain
from ..config.loader import load_config
from ..git.repository import GitRepository
from ..learn.redaction import redact_record
from ..reporting.models import CommandResult
from ..testing.approval import approve_test
from ..testing.explanations import explain_test, sync_explanations


def _chain_or_block(root: Path, command: str) -> CommandResult | None:
    chain = discover_instruction_chain(root)
    if chain.conflicts:
        result = CommandResult(command, status="blocked", exit_code=1,
                               metadata={"instruction_chain": [item.path for item in chain.files],
                                         "conflicts": chain.conflicts})
        result.actions.append("Resolve the applicable Markdown instruction conflict before continuing")
        return result
    return None


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return result[:72]


def create_test(root: Path, description: str, *, path: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework test create")
    if blocked:
        return blocked
    root = root.resolve(); target = Path(path) if path else Path("tests") / f"test_{_slug(description)}.py"
    target = (root / target).resolve()
    if root not in target.parents:
        return CommandResult("framework test create", status="error", exit_code=2,
                             actions=["Test path must remain inside project root"])
    if target.exists():
        return CommandResult("framework test create", status="error", exit_code=2,
                             actions=[f"Refusing to overwrite existing test: {target.relative_to(root)}"])
    target.parent.mkdir(parents=True, exist_ok=True)
    function = _slug(description) or "behavior"
    content = (f'"""Generated behavior contract.\n\n{description}\n"""\n\n\n'
               f"def test_{function}():\n"
               f'    """TODO: replace this red test with the project-specific assertion."""\n'
               f'    raise AssertionError("Behavior not implemented: {description}")\n')
    target.write_text(content)
    result = CommandResult("framework test create", metadata={"path": str(target.relative_to(root)),
                                                                "description": description,
                                                                "state": "red"})
    result.actions.append("Review the generated test before implementing the behavior")
    return result


def approve(root: Path, test: str, behavior: str | None = None) -> CommandResult:
    return approve_test(root.resolve(), test, behavior=behavior)


def _run_test(root: Path, test: str | None) -> subprocess.CompletedProcess[str] | None:
    if not test:
        return None
    path = (root / test).resolve()
    if root not in path.parents or not path.exists():
        return None
    return subprocess.run([sys.executable, "-m", "pytest", str(path)], cwd=root, text=True,
                          capture_output=True, check=False, timeout=300)


def _agent_request(root: Path, operation: str, context: dict[str, Any]) -> Path:
    chain = discover_instruction_chain(root)
    raw = {"schema_version": 1, "request_id": f"request-{uuid.uuid4().hex[:16]}",
           "operation": operation, "context": context,
           "instruction_chain": [{"path": item.path, "checksum": item.checksum,
                                   "content": item.content} for item in chain.files]}
    request, _ = redact_record(raw)
    path = root / ".framework" / "agents" / "requests" / f"{request['request_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")
    return path


def _configured_command(root: Path, explicit: str | None) -> list[str] | None:
    if explicit:
        return shlex.split(explicit)
    try:
        config = load_config(root)
        value = config.learn.get("agent_command")
    except FileNotFoundError:
        value = None
    if not value or value in {"local", "none"}:
        return None
    return shlex.split(value) if isinstance(value, str) else list(value)


def _invoke_agent(root: Path, operation: str, context: dict[str, Any], command: str | None) -> dict[str, Any]:
    request_path = _agent_request(root, operation, context)
    argv = _configured_command(root, command)
    if not argv:
        return {"status": "prepared", "request_id": request_path.stem, "request_path": str(request_path.relative_to(root))}
    try:
        completed = subprocess.run([*argv, str(request_path)], cwd=root, text=True,
                                   capture_output=True, check=False, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "request_id": request_path.stem, "error": type(exc).__name__}
    return {"status": "completed" if completed.returncode == 0 else "failed",
            "request_id": request_path.stem, "exit_code": completed.returncode}


def implement(root: Path, test: str | None, *, agent_command: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework implement")
    if blocked:
        return blocked
    root = root.resolve()
    if not test:
        return CommandResult("framework implement", status="error", exit_code=2,
                             actions=["Provide the approved test path"])
    run = _run_test(root, test)
    if run is None:
        return CommandResult("framework implement", status="error", exit_code=2,
                             actions=["Test path does not exist inside project root"])
    if run.returncode == 0:
        return CommandResult("framework implement", status="blocked", exit_code=1,
                             actions=["Implementation requires a failing test before the agent is invoked"])
    outcome = _invoke_agent(root, "implement", {"test": test, "test_exit_code": run.returncode,
                                                  "test_output_available": True}, agent_command)
    result = CommandResult("framework implement", metadata=outcome)
    result.actions.append("Run framework test and framework check after reviewing the agent changes")
    if outcome["status"] == "failed":
        result.status, result.exit_code = "error", 2
    return result


def fix(root: Path, description: str, *, issue: str | None = None, agent_command: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework fix")
    if blocked:
        return blocked
    outcome = _invoke_agent(root, "fix", {"description": description, "issue": issue,
                                           "git_branch": GitRepository(root).branch}, agent_command)
    result = CommandResult("framework fix", metadata=outcome)
    result.actions.append("The agent request is context-only; review the diff and run framework check")
    if outcome["status"] == "failed":
        result.status, result.exit_code = "error", 2
    return result


def tradeoff(root: Path, description: str, *, agent_command: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework tradeoff")
    if blocked:
        return blocked
    context = {"description": description, "dimensions": ["complexity", "testing", "coupling",
                "performance", "security", "operations", "maintenance"]}
    outcome = _invoke_agent(root, "tradeoff", context, agent_command)
    result = CommandResult("framework tradeoff", metadata={"description": description, **outcome})
    result.actions.append("Trade-off analysis is advisory and does not modify source code")
    if outcome["status"] == "failed":
        result.status, result.exit_code = "error", 2
    return result


def review(root: Path, *, show_diff: bool = False) -> CommandResult:
    root = root.resolve(); git = GitRepository(root)
    result = CommandResult("framework review", metadata={"git": git.snapshot()})
    if not git.available:
        result.status, result.exit_code = "degraded", 0
        result.actions.append("Git is unavailable; structural diff review is partial")
        return result
    diff = git.diff()
    files = sorted({line[6:] for line in diff.splitlines() if line.startswith("+++ b/")})
    result.metadata.update({"changed_files": files, "diff": diff if show_diff else {"lines": len(diff.splitlines())}})
    result.actions.append("Review behavior, tests and security findings before committing")
    return result


def inspect(root: Path, symbol: str) -> CommandResult:
    root = root.resolve(); matches: list[dict[str, Any]] = []
    name = symbol.rsplit(".", 1)[-1]
    for path in sorted(root.rglob("*.py")):
        if {".git", ".venv", "venv", ".framework"}.intersection(path.parts):
            continue
        text = path.read_text(errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(rf"\b(def|class)\s+{re.escape(name)}\b", line):
                matches.append({"path": str(path.relative_to(root)), "line": line_no, "declaration": line.strip()})
    return CommandResult("framework inspect", metadata={"symbol": symbol, "matches": matches})


def update(root: Path) -> CommandResult:
    result = sync_explanations(root)
    result.command = "framework update"
    result.actions.append("Update currently regenerates deterministic test explanations")
    return result

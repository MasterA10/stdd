from __future__ import annotations

import json
import hashlib
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from ..agents.instructions import discover_instruction_chain
from ..adapters.registry import detect_project
from ..commands.check import check
from ..commands.test import run_tests
from ..config.loader import load_config
from ..git.repository import GitRepository
from ..history.records import record_bug, record_change, record_tradeoff
from ..learn.redaction import redact_record
from ..reporting.models import CommandResult
from ..testing.approval import approve_test, approved_hashes, approved_paths
from ..testing.explanations import explain_test, sync_explanations


LOCAL_AGENTS = ("codex", "claude", "cloud", "antigravity")


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


def _regression_test(root: Path, description: str) -> str:
    clean, _ = redact_record({"description": description})
    safe_description = clean["description"]
    slug = _slug(safe_description) or "behavior"
    suffix = ".py"
    for candidate in sorted(root.rglob("*")):
        if candidate.is_file() and "tests" in candidate.parts and candidate.suffix in {".py", ".js", ".ts"}:
            suffix = candidate.suffix
            break
    directory = root / "tests" / "regressions"
    target = directory / f"test_bug_{slug}{suffix}"
    if target.exists():
        return str(target.relative_to(root))
    directory.mkdir(parents=True, exist_ok=True)
    if suffix == ".py":
        content = (f'"""Regression contract.\n\n{safe_description}\n"""\n\n\n'
                   f"def test_bug_{slug}():\n"
                   f'    raise AssertionError("Regression not implemented: {safe_description}")\n')
    else:
        content = (f"// Regression contract: {safe_description}\n"
                   f"test(\"{safe_description}\", () => {{\n"
                   f"  throw new Error(\"Regression not implemented\");\n"
                   f"}});\n")
    target.write_text(content)
    return str(target.relative_to(root))


def _protected_paths(root: Path) -> list[str]:
    return [str(path.relative_to(root)) for path in approved_paths(root)]


def _source_paths(root: Path) -> list[str]:
    suffixes = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".php"}
    return [str(path.relative_to(root)) for path in sorted(root.rglob("*"))
            if path.is_file() and path.suffix in suffixes and
            not {".git", ".venv", "venv", ".framework"}.intersection(path.parts)]


def _hash_paths(root: Path, paths: list[str]) -> dict[str, str]:
    return {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in paths if (root / relative).is_file()}


def _related_paths(root: Path, description: str) -> list[str]:
    """Find likely source/test files to include in the bug's Git evidence."""
    terms = {term for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", description.lower())}
    paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or {".git", ".venv", "venv", ".framework"}.intersection(path.parts):
            continue
        if path.suffix not in {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".php"}:
            continue
        try:
            content = path.read_text(errors="replace").lower()
        except OSError:
            continue
        if terms.intersection(re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", content)):
            paths.append(str(path.relative_to(root)))
    return paths[:20]


def _make_read_only(root: Path, paths: list[str]) -> dict[Path, int]:
    modes: dict[Path, int] = {}
    for relative in paths:
        path = (root / relative).resolve()
        if root in path.parents and path.is_file():
            modes[path] = path.stat().st_mode & 0o777
            path.chmod(modes[path] & ~0o222)
    return modes


def _restore_modes(modes: dict[Path, int]) -> None:
    for path, mode in modes.items():
        if path.exists():
            path.chmod(mode)


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


def _native_command(root: Path, target: str) -> tuple[list[str], bool] | None:
    executable = shutil.which(target)
    if not executable:
        return None
    if target == "codex":
        return [executable, "exec", "-C", str(root), "-"], True
    if target == "claude":
        return [executable, "-p", "--permission-mode", "acceptEdits", "--add-dir", str(root)], True
    return [executable], False


def _parse_agent_value(root: Path, value: str | list[str]) -> tuple[list[str], bool] | None:
    parsed = shlex.split(value) if isinstance(value, str) else list(value)
    if not parsed:
        return None
    name = Path(parsed[0]).name
    if name in {"codex", "claude"}:
        return _native_command(root, name)
    return (parsed, False) if shutil.which(parsed[0]) else None


def _preferred_agents(root: Path, learn: dict[str, Any]) -> list[str]:
    preferred: list[str] = []
    try:
        preferred.extend(load_config(root).agent_integrations)
    except FileNotFoundError:
        pass
    return preferred + [item for item in LOCAL_AGENTS if item not in preferred]


def _configured_agent(root: Path, target: str, configured: dict[str, Any]) -> tuple[list[str], bool] | None:
    entry = configured.get(target, {})
    command = entry.get("command") if isinstance(entry, dict) else entry
    if command:
        parsed = _parse_agent_value(root, command)
        if parsed:
            return parsed
    return _native_command(root, target)


def _configured_command(root: Path, explicit: str | None) -> tuple[list[str], bool] | None:
    if explicit:
        return _parse_agent_value(root, explicit)
    try:
        learn = load_config(root).learn
    except FileNotFoundError:
        learn = {}
    value = learn.get("agent_command")
    if value and value not in {"local", "auto", "none"}:
        return _parse_agent_value(root, value)
    configured = learn.get("agents", {}) if isinstance(learn.get("agents", {}), dict) else {}
    for target in _preferred_agents(root, learn):
        result = _configured_agent(root, target, configured)
        if result:
            return result
    return None


def _invoke_agent(root: Path, operation: str, context: dict[str, Any], command: str | None) -> dict[str, Any]:
    request_path = _agent_request(root, operation, context)
    resolved = _configured_command(root, command)
    if not resolved:
        return {"status": "prepared", "request_id": request_path.stem, "request_path": str(request_path.relative_to(root))}
    argv, stdin_prompt = resolved
    prompt = ("You are the local project agent. Read and follow the redacted framework request below. "
              "Respect every applicable Markdown instruction in instruction_chain. "
              "Perform the requested operation in the current workspace and do not expose secrets.\n\n" +
              request_path.read_text())
    protected_hashes = approved_hashes(root)
    read_only_paths = context.get("read_only_paths", [])
    read_only_hashes = _hash_paths(root, read_only_paths)
    modes = _make_read_only(root, sorted(set([*context.get("protected_tests", []), *read_only_paths])))
    try:
        completed = subprocess.run(argv if stdin_prompt else [*argv, str(request_path)], cwd=root, text=True,
                                   input=prompt if stdin_prompt else None, capture_output=True,
                                   check=False, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "request_id": request_path.stem, "error": type(exc).__name__}
    finally:
        _restore_modes(modes)
    response = {"status": "completed" if completed.returncode == 0 else "failed",
            "request_id": request_path.stem, "exit_code": completed.returncode,
            "agent": Path(argv[0]).name}
    safe, _ = redact_record({"status": response["status"], "stdout": completed.stdout,
                             "stderr": completed.stderr})
    response_path = root / ".framework" / "agents" / "results" / f"{request_path.stem}.json"
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text(json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    response["response_path"] = str(response_path.relative_to(root))
    current_hashes = _hash_paths(root, sorted(set([*protected_hashes, *read_only_hashes])))
    violations = [relative for relative, expected in protected_hashes.items()
                  if current_hashes.get(relative) != expected]
    read_only_violations = [relative for relative, expected in read_only_hashes.items()
                            if current_hashes.get(relative) != expected]
    read_only_violations.extend(sorted(set(_source_paths(root)) - set(read_only_hashes)))
    if violations:
        response["status"] = "failed"
        response["protected_test_violations"] = violations
    if read_only_violations:
        response["status"] = "failed"
        response["read_only_violations"] = read_only_violations
    return response


def implement(root: Path, test: str | None, *, agent_command: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework implement")
    if blocked:
        return blocked
    root = root.resolve()
    git = GitRepository(root)
    git_before = git.context([test] if test else None)
    run = _run_test(root, test) if test else None
    if test and run is None:
        return CommandResult("framework implement", status="error", exit_code=2,
                             actions=["Test path does not exist inside project root"])
    if test and run and run.returncode == 0:
        return CommandResult("framework implement", status="blocked", exit_code=1,
                             actions=["Implementation requires a failing test before the agent is invoked"])
    protected = _protected_paths(root)
    outcome = _invoke_agent(root, "implement", {"test": test,
                                                  "test_exit_code": run.returncode if run else None,
                                                  "test_output_available": bool(run),
                                                  "protected_tests": protected}, agent_command)
    result = CommandResult("framework implement", status=outcome["status"], metadata=outcome)
    result.actions.append("The local agent received the request; framework check validates its changes")
    if outcome["status"] == "failed":
        result.status, result.exit_code = "error", 2
    elif outcome["status"] == "completed":
        regression_after = _run_test(root, regression_test) if regression_test.endswith(".py") else None
        result.metadata["regression_exit_code_after_agent"] = (regression_after.returncode
                                                                if regression_after else None)
        result.actions.append("Regression test executed after the local agent")
        _attach_gates(root, result)
    history = record_change(root, operation="implement", description=f"Implement behavior from {test or 'agent-discovered scope'}",
                            tests=[test] if test else [], status=outcome["status"],
                            behavior_before="Failing or unspecified behavior before implementation",
                            behavior_after="Agent outcome recorded; verify the related tests and gates",
                            git_context={"before": git_before, "after": git.context([test] if test else None)})
    result.metadata["history_path"] = str(history.relative_to(root))
    return result


def fix(root: Path, description: str, *, issue: str | None = None, agent_command: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework fix")
    if blocked:
        return blocked
    root = root.resolve()
    related = _related_paths(root, description)
    regression_test = _regression_test(root, description)
    regression_run = _run_test(root, regression_test) if regression_test.endswith(".py") else None
    git = GitRepository(root)
    evidence_paths = sorted(set([*related, *git.changed_files(), regression_test]))
    git_before = git.context(evidence_paths)
    outcome = _invoke_agent(root, "fix", {"description": description, "issue": issue,
                                           "regression_test": regression_test,
                                           "regression_red": regression_run is None or regression_run.returncode != 0,
                                           "git_branch": git.branch, "git_before": git_before,
                                           "protected_tests": _protected_paths(root)}, agent_command)
    result = CommandResult("framework fix", status=outcome["status"], metadata=outcome)
    result.metadata["regression_test"] = regression_test
    result.actions.append("Regression test created before the local agent was invoked")
    if outcome["status"] == "failed":
        result.status, result.exit_code = "error", 2
    elif outcome["status"] == "completed":
        _attach_gates(root, result)
    git_after = git.context(evidence_paths)
    result.metadata["git_before"] = git_before
    result.metadata["git_after"] = git_after
    history = record_bug(root, description=description, regression_test=regression_test,
                         symbols=[],
                         evidence={"issue": issue, "regression_exit_code": regression_run.returncode if regression_run else None,
                                   "related_files": related,
                                   "behavior_before": "Bug reproduced by the generated regression contract",
                                   "behavior_after": "Agent outcome recorded; verify the regression test result"},
                         status=outcome["status"], git_context={"before": git_before, "after": git_after})
    result.metadata["history_path"] = str(history.relative_to(root))
    return result


def tradeoff(root: Path, description: str, *, agent_command: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework tradeoff")
    if blocked:
        return blocked
    git = GitRepository(root.resolve())
    context = {"description": description, "dimensions": ["complexity", "testing", "coupling",
                "performance", "security", "operations", "maintenance"],
               "git_context": git.context(), "read_only_paths": _source_paths(root)}
    outcome = _invoke_agent(root, "tradeoff", context, agent_command)
    analysis = _tradeoff_analysis(root, outcome)
    history = record_tradeoff(root, description=description, analysis=analysis,
                              agent=outcome.get("agent"), status=outcome["status"],
                              git_context=git.context())
    result = CommandResult("framework tradeoff", status=outcome["status"], metadata={"description": description, **outcome,
                                                            "analysis": analysis,
                                                            "history_path": str(history.relative_to(root))})
    result.actions.append("Trade-off analysis is advisory and does not modify source code")
    result.actions.append(f"Trade-off record: {history.relative_to(root)}")
    if analysis.get("summary"):
        result.actions.append(f"Summary: {analysis['summary'][:300]}")
    if outcome["status"] == "failed":
        result.status, result.exit_code = "error", 2
    return result


def _tradeoff_analysis(root: Path, outcome: dict[str, Any]) -> dict[str, Any]:
    response_path = outcome.get("response_path")
    if not response_path:
        return {"status": outcome["status"], "summary": "Analysis pending local agent execution", "sections": {}}
    try:
        response = json.loads((root / response_path).read_text())
    except (OSError, json.JSONDecodeError):
        return {"status": "failed", "summary": "Agent response could not be read", "sections": {}}
    text = str(response.get("stdout", "")).strip()
    if not text:
        return {"status": outcome["status"], "summary": "Agent returned no analysis", "sections": {}}
    sections: dict[str, list[str]] = {}
    current = "summary"
    sections[current] = []
    for line in text.splitlines():
        value = line.strip()
        heading = re.match(r"^#{1,6}\s+(.+?)\s*:?(?:\s*)$", value)
        if heading and len(heading.group(1)) < 80:
            current = re.sub(r"[^a-z0-9]+", "_", heading.group(1).lower()).strip("_")
            sections.setdefault(current, [])
        elif value.endswith(":") and len(value) < 80:
            current = re.sub(r"[^a-z0-9]+", "_", value[:-1].lower()).strip("_")
            sections.setdefault(current, [])
        elif value:
            sections.setdefault(current, []).append(value[:500])
    return {"status": outcome["status"], "summary": " ".join(sections.get("summary", []))[:500],
            "sections": sections}


def _attach_gates(root: Path, result: CommandResult) -> None:
    gates = check(root)
    result.metadata["gates"] = {"status": gates.status, "exit_code": gates.exit_code}
    result.children = gates.children
    if gates.exit_code:
        result.status, result.exit_code = "blocked", 1


def generate_scripts(root: Path, *, agent_command: str | None = None) -> CommandResult:
    blocked = _chain_or_block(root, "framework scripts generate")
    if blocked:
        return blocked
    root = root.resolve()
    try:
        config = load_config(root).to_dict()
    except FileNotFoundError:
        config = {}
    context = {"project_config": config, "detected_stack": detect_project(root),
               "output_directory": ".framework/scripts",
               "requirements": ["generate executable scripts for detected stack",
                                "include test-all and test-changed when meaningful",
                                "do not hardcode unsupported languages",
                                "keep secrets and prompts out of generated files"]}
    outcome = _invoke_agent(root, "generate-scripts", context, agent_command)
    result = CommandResult("framework scripts generate", metadata=outcome)
    if outcome["status"] == "completed":
        scripts = sorted(str(path.relative_to(root)) for path in (root / ".framework/scripts").glob("*") if path.is_file())
        result.metadata["scripts"] = scripts
        if not scripts:
            result.status, result.exit_code = "error", 2
            result.actions.append("Agent completed without generating a script")
    elif outcome["status"] == "prepared":
        result.actions.append("No local agent was found; request prepared for an authorized agent")
    elif outcome["status"] == "failed":
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

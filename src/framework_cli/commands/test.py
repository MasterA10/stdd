from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

from ..adapters.registry import discover_adapters
from ..config.loader import load_config
from ..git.repository import GitRepository
from ..reporting.children import aggregate_children
from ..reporting.models import CommandResult
from ..scripts.runner import ScriptRunner


SCOPES = ("unit", "integration", "database", "security", "performance")


def _configured_commands(config: Any, scope: str | None) -> list[list[str]]:
    if config is None:
        return []
    commands: list[list[str]] = []
    for application in config.applications.values():
        tests = application.get("tests", {}) if isinstance(application, dict) else {}
        selected = tests.get(scope, {}) if scope else tests
        values = selected if isinstance(selected, list) else [selected]
        if scope is None and isinstance(tests, dict):
            values = [item for item in tests.values()]
        for value in values:
            raw = value.get("command") if isinstance(value, dict) else value
            if raw:
                commands.append(shlex.split(raw) if isinstance(raw, str) else list(raw))
    return commands


def _scope_paths(root: Path, scope: str) -> list[str]:
    names = {
        "unit": ("tests/unit", "test/unit", "__tests__"),
        "integration": ("tests/integration", "test/integration"),
        "database": ("tests/database", "tests/db", "tests/integration/database"),
        "security": ("tests/security", "test/security"),
        "performance": ("tests/performance", "test/performance"),
    }
    return [item for item in names[scope] if (root / item).exists()]


def _changed_test_paths(root: Path) -> list[str]:
    changed = GitRepository(root).changed_files()
    tests = [item for item in changed if "test" in Path(item).name.lower() or "tests" in Path(item).parts]
    if tests:
        return tests
    stems = {Path(item).stem.replace("test_", "") for item in changed}
    result = []
    for path in root.rglob("*"):
        if path.is_file() and "tests" in path.parts and any(stem in path.stem for stem in stems):
            result.append(str(path.relative_to(root)))
    return sorted(result)


def _with_scope(command: list[str], paths: list[str]) -> list[str]:
    if not paths:
        return command
    return [*command, *paths]


def _result_for_security(root: Path) -> CommandResult:
    from .security import security_scan
    scan = security_scan(root)
    return CommandResult("framework test", status=scan.status, exit_code=scan.exit_code,
                         findings=scan.findings, actions=scan.actions,
                         metadata={"scope": "security", "security": scan.to_dict()})


def _load_project_config(root: Path):
    try:
        return load_config(root)
    except FileNotFoundError:
        return None


def _select_scope(scope: str | None, all_scopes: bool) -> str | None:
    if all_scopes:
        return None
    if scope and scope not in SCOPES:
        raise ValueError(f"Unknown test scope: {scope}")
    return scope


def _commands_for(root: Path, config: Any, scope: str | None) -> list[list[str]]:
    commands = _configured_commands(config, scope)
    if not commands:
        for adapter in discover_adapters(root):
            commands.extend(adapter.test_commands(root))
    return commands


def _run_commands(root: Path, commands: list[list[str]], paths: list[str]) -> list[dict[str, Any]]:
    children = []
    seen: set[tuple[str, ...]] = set()
    for args in commands:
        command = _with_scope(args, paths)
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        completed = ScriptRunner(root).run(command, timeout=300)
        children.append({"command": command, "status": "passed" if completed.returncode == 0 else "failed",
                         "exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]})
    return children


def _append_security_child(root: Path, result: CommandResult) -> None:
    security = _result_for_security(root)
    result.children.append({"command": ["framework", "security", "scan"], "status": security.status,
                            "exit_code": security.exit_code, "findings": [item.to_dict() if hasattr(item, "to_dict") else item for item in security.findings]})
    if security.exit_code:
        result.status, result.exit_code = "blocked", 1


def _empty_scope_result(scope: str | None, changed: bool) -> CommandResult:
    label = "changed" if changed else scope
    return CommandResult("framework test", metadata={"scope": label, "changed": changed, "paths": []},
                         actions=[f"No {label} test files were found"])


def _select_test_paths(root: Path, scope: str | None, changed: bool,
                       explicit_paths: list[str] | None) -> tuple[list[str], CommandResult | None]:
    if explicit_paths:
        invalid = [path for path in explicit_paths
                   if not ((root / path).resolve().is_file()
                           and root in (root / path).resolve().parents)]
        if invalid:
            return [], CommandResult(
                "framework test", status="error", exit_code=2,
                actions=[f"Test path does not exist inside project: {path}" for path in invalid],
            )
        return sorted(set(explicit_paths)), None
    if changed:
        return _changed_test_paths(root), None
    return _scope_paths(root, scope) if scope else [], None


def _add_run_actions(result: CommandResult, root: Path, scope: str | None,
                     changed: bool, all_scopes: bool, paths: list[str], config: Any) -> None:
    result.metadata.update({"scope": "all" if all_scopes else scope,
                            "changed": changed, "paths": paths})
    if all_scopes:
        _append_security_child(root, result)
    if changed and not paths:
        result.actions.append("No changed or related test files were found")
    if scope and not _scope_paths(root, scope) and not _configured_commands(config, scope):
        result.actions.append(f"No dedicated {scope} test path was found; configured runners were used")


def run_tests(root: Path, *, scope: str | None = None, changed: bool = False,
              all_scopes: bool = False, explicit_paths: list[str] | None = None):
    root = root.resolve()
    config = _load_project_config(root)
    if scope == "security":
        return _result_for_security(root)
    try:
        scope = _select_scope(scope, all_scopes)
    except ValueError as exc:
        return CommandResult("framework test", status="error", exit_code=2, actions=[str(exc)])
    paths, path_error = _select_test_paths(root, scope, changed, explicit_paths)
    if path_error:
        return path_error
    if (changed or scope) and not paths and not _configured_commands(config, scope):
        return _empty_scope_result(scope, changed)
    commands = _commands_for(root, config, scope)
    children = _run_commands(root, commands, paths)
    result = aggregate_children("framework test", children, {"root": str(root), "profile": config.profile if config else None,
                                                               "scope": "all" if all_scopes else scope, "changed": changed,
                                                               "paths": paths})
    _add_run_actions(result, root, scope, changed, all_scopes, paths, config)
    return result

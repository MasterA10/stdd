from __future__ import annotations

import argparse
import platform
from pathlib import Path

from .commands.check import check
from .commands.doctor import doctor
from .commands.init import init_project
from .agents.integrations import integration_keys
from .commands.install import install, integration_list, integration_status_command
from .commands.learn import run_learn
from .commands.quiz import run as run_quiz_command
from .commands.scan import scan_project
from .commands.security import security_scan
from .commands.test import run_tests
from .commands.workflow import (approve, create_test, fix, implement, inspect, review,
                                generate_scripts, sync_explanations, tradeoff, update)
from .reporting.render import render
from .version import RELEASE_SOURCE, __version__


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--verbose", action="store_true")


def _add_test_commands(sub: argparse._SubParsersAction) -> None:
    test = sub.add_parser("test")
    for scope in ("unit", "integration", "database", "security", "performance"):
        test.add_argument(f"--{scope}", action="store_true", help=f"run only {scope} tests")
    test.add_argument("--changed", action="store_true", help="run tests related to changed files")
    test.add_argument("--all", action="store_true", help="run the complete suite and security gate")
    test_sub = test.add_subparsers(dest="test_command")
    test_run = test_sub.add_parser("run")
    test_run.add_argument("path", nargs="?", default=".")
    _common(test_run)
    test_create = test_sub.add_parser("create")
    test_create.add_argument("description", nargs="+",
                             help="descrição completa da feature/test suite")
    test_create.add_argument("--agent-command")
    _common(test_create)
    test_explain = test_sub.add_parser("explain")
    test_explain.add_argument("test_path", nargs="?")
    test_explain.add_argument("--all", action="store_true")
    test_explain.add_argument("--mode", choices=("header", "first-use", "virtual"))
    _common(test_explain)
    test_approve = test_sub.add_parser("approve")
    test_approve.add_argument("test_path", nargs="?")
    test_approve.add_argument("--behavior")
    _common(test_approve)
    _common(test)


def _add_learn_commands(sub: argparse._SubParsersAction) -> None:
    learn = sub.add_parser("learn")
    learn_sub = learn.add_subparsers(dest="learn_command")

    def learn_common(command: argparse.ArgumentParser) -> None:
        command.add_argument("--session-id")
        command.add_argument("--observation", dest="observations", action="append", default=[])
        command.add_argument("--inference", dest="inferences", action="append", default=[])
        command.add_argument("--file", dest="files", action="append", default=[])
        command.add_argument("--symbol", dest="symbols", action="append", default=[])
        command.add_argument("--task", dest="tasks", action="append", default=[])
        command.add_argument("--gate", dest="gates", action="append", default=[])
        command.add_argument("--evidence", action="append", default=[])

    start = learn_sub.add_parser("start")
    start.add_argument("--agent", default="framework")
    start.add_argument("--host", default="framework-cli")
    start.add_argument("path", nargs="?", default=".")
    _common(start)
    for name in ("checkpoint", "compact", "resume", "close"):
        command = learn_sub.add_parser(name)
        learn_common(command)
        command.add_argument("path", nargs="?", default=".")
        _common(command)
    for name in ("summary", "rework"):
        command = learn_sub.add_parser(name)
        command.add_argument("--session-id")
        command.add_argument("path", nargs="?", default=".")
        _common(command)
    review_lesson = learn_sub.add_parser("review")
    review_lesson.add_argument("lesson_id")
    review_lesson.add_argument("decision", choices=("approved", "rejected", "edited"))
    review_lesson.add_argument("--content", action="append")
    review_lesson.add_argument("path", nargs="?", default=".")
    _common(review_lesson)
    _add_handoff_commands(learn_sub)
    _add_hook_commands(learn_sub)
    learn.add_argument("path", nargs="?", default=".")
    _common(learn)


def _add_handoff_commands(learn_sub: argparse._SubParsersAction) -> None:
    handoff = learn_sub.add_parser("handoff")
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    export = handoff_sub.add_parser("export")
    export.add_argument("--target", default="generic", choices=("generic", "codex", "claude", "antigravity", "new-session"))
    export.add_argument("--session-id")
    export.add_argument("--scope-session", dest="scope_sessions", action="append", default=[])
    export.add_argument("--scope-category", dest="scope_categories", action="append", default=[])
    export.add_argument("--scope-file", dest="scope_files", action="append", default=[])
    export.add_argument("--scope-symbol", dest="scope_symbols", action="append", default=[])
    export.add_argument("--scope-status", dest="scope_statuses", action="append", default=["approved"])
    export.add_argument("path", nargs="?", default=".")
    _common(export)
    importer = handoff_sub.add_parser("import")
    importer.add_argument("package")
    importer.add_argument("path", nargs="?", default=".")
    _common(importer)
    sender = handoff_sub.add_parser("send")
    sender.add_argument("package")
    sender.add_argument("--target", required=True, choices=("codex", "claude", "cloud", "antigravity", "generic"))
    sender.add_argument("--dry-run", action="store_true")
    sender.add_argument("path", nargs="?", default=".")
    _common(sender)


def _add_hook_commands(learn_sub: argparse._SubParsersAction) -> None:
    hooks = learn_sub.add_parser("hooks")
    hooks_sub = hooks.add_subparsers(dest="hooks_command", required=True)
    installer = hooks_sub.add_parser("install")
    installer.add_argument("--host", dest="hosts", action="append", choices=("codex", "claude", "cloud", "antigravity", "generic"))
    installer.add_argument("path", nargs="?", default=".")
    _common(installer)
    event = hooks_sub.add_parser("event")
    event.add_argument("--host", default="generic", choices=("codex", "claude", "cloud", "antigravity", "generic"))
    event.add_argument("--event", required=True)
    event.add_argument("--session-id")
    event.add_argument("--facts", help="JSON facts from the host hook; redacted before persistence")
    event.add_argument("path", nargs="?", default=".")
    _common(event)


def _add_quiz_commands(sub: argparse._SubParsersAction) -> None:
    quiz = sub.add_parser("quiz")
    quiz_sub = quiz.add_subparsers(dest="quiz_command", required=True)
    generate = quiz_sub.add_parser("generate")
    generate.add_argument("--agent", "--provider", dest="agent", choices=("local", "codex", "claude", "cloud", "antigravity", "generic"), default="local")
    generate.add_argument("--scope", default="project")
    generate.add_argument("path", nargs="?", default=".")
    _common(generate)
    run = quiz_sub.add_parser("run")
    run.add_argument("--category")
    run.add_argument("--count", type=int, default=10)
    run.add_argument("--answer", dest="answers", action="append")
    run.add_argument("path", nargs="?", default=".")
    _common(run)
    synchronize = quiz_sub.add_parser("refresh")
    synchronize.add_argument("path", nargs="?", default=".")
    _common(synchronize)
    export = quiz_sub.add_parser("export")
    export.add_argument("--format", dest="quiz_format", choices=("json", "yaml", "markdown"), default="json")
    export.add_argument("path", nargs="?", default=".")
    _common(quiz)


def _add_integration_commands(sub: argparse._SubParsersAction) -> None:
    integration = sub.add_parser("integration")
    integration_sub = integration.add_subparsers(dest="integration_command", required=True)
    listed = integration_sub.add_parser("list")
    listed.add_argument("path", nargs="?", default=".")
    _common(listed)
    status = integration_sub.add_parser("status")
    status.add_argument("path", nargs="?", default=".")
    _common(status)
    installer = integration_sub.add_parser("install")
    installer.add_argument("integration", choices=integration_keys(installable_only=True))
    installer.add_argument("path", nargs="?", default=".")
    _common(installer)


def _add_workflow_commands(sub: argparse._SubParsersAction) -> None:
    tradeoff_parser = sub.add_parser("tradeoff")
    tradeoff_parser.add_argument("description",
                                 help="descrição completa da decisão")
    tradeoff_parser.add_argument("--agent-command")
    tradeoff_parser.add_argument("path", nargs="?", default=".")
    _common(tradeoff_parser)
    implement_parser = sub.add_parser("implement")
    implement_parser.add_argument("test", nargs="?")
    implement_parser.add_argument("--agent-command")
    implement_parser.add_argument("path", nargs="?", default=".")
    _common(implement_parser)
    fix_parser = sub.add_parser("fix")
    fix_parser.add_argument("description",
                            help="descrição completa do bug")
    fix_parser.add_argument("--issue")
    fix_parser.add_argument("--agent-command")
    fix_parser.add_argument("path", nargs="?", default=".")
    _common(fix_parser)
    review_parser = sub.add_parser("review")
    review_parser.add_argument("--diff", action="store_true")
    review_parser.add_argument("path", nargs="?", default=".")
    _common(review_parser)
    synchronize = sub.add_parser("sync")
    synchronize.add_argument("path", nargs="?", default=".")
    _common(synchronize)
    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("symbol")
    inspect_parser.add_argument("path", nargs="?", default=".")
    _common(inspect_parser)
    update_parser = sub.add_parser("update")
    update_parser.add_argument("path", nargs="?", default=".")
    _common(update_parser)
    scripts = sub.add_parser("scripts")
    scripts_sub = scripts.add_subparsers(dest="scripts_command", required=True)
    generate = scripts_sub.add_parser("generate")
    generate.add_argument("--agent-command")
    generate.add_argument("path", nargs="?", default=".")
    _common(generate)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="framework", description="Deterministic development framework CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    version = sub.add_parser("version")
    _common(version)
    init = sub.add_parser("init")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--here", action="store_true")
    init.add_argument("--from", dest="requirements")
    init.add_argument("--integration", choices=integration_keys(installable_only=True))
    init.add_argument("--profile", choices=("experiment", "mvp", "product"), default="mvp")
    init.add_argument("--install-hooks", action="store_true")
    _common(init)
    for name in ("scan", "check"):
        command = sub.add_parser(name)
        command.add_argument("path", nargs="?", default=".")
        _common(command)
    doctor_parser = sub.add_parser("doctor")
    _common(doctor_parser)
    _add_test_commands(sub)
    security = sub.add_parser("security")
    security_sub = security.add_subparsers(dest="security_command", required=True)
    scan = security_sub.add_parser("scan")
    scan.add_argument("path", nargs="?", default=".")
    scan.add_argument("--staged", action="store_true")
    _common(scan)
    _add_learn_commands(sub)
    _add_quiz_commands(sub)
    _add_integration_commands(sub)
    _add_workflow_commands(sub)
    return parser


def _dispatch_test(args: argparse.Namespace, root: Path):
    command = getattr(args, "test_command", None)
    if command == "create":
        return create_test(root, " ".join(args.description), agent_command=args.agent_command)
    if command == "explain":
        if args.all:
            return sync_explanations(root, mode=args.mode, include_unmarked=True)
        if args.test_path:
            from .testing.explanations import explain_test
            return explain_test(root, args.test_path, mode=args.mode)
        return sync_explanations(root, mode=args.mode, include_unmarked=True)
    if command == "approve":
        return approve(root, args.test_path, args.behavior)
    if command == "run":
        explicit = None if args.path == "." else [args.path]
        return run_tests(root, explicit_paths=explicit)
    selected = [name for name in ("unit", "integration", "database", "security", "performance") if getattr(args, name, False)]
    if len(selected) > 1 or (selected and getattr(args, "all", False)):
        from .reporting.models import CommandResult
        return CommandResult("framework test", status="error", exit_code=2,
                             actions=["Choose one test scope or --all"])
    return run_tests(root, scope=selected[0] if selected else None,
                     changed=getattr(args, "changed", False), all_scopes=getattr(args, "all", False))


def _dispatch_workflow(args: argparse.Namespace, root: Path):
    handlers = {
        "tradeoff": lambda: tradeoff(root, args.description, agent_command=args.agent_command),
        "implement": lambda: implement(root, args.test, agent_command=args.agent_command),
        "fix": lambda: fix(root, args.description, issue=args.issue, agent_command=args.agent_command),
        "review": lambda: review(root, show_diff=args.diff),
        "sync": lambda: sync_explanations(root),
        "inspect": lambda: inspect(root, args.symbol),
        "update": lambda: update(root),
    }
    return handlers[args.command]()


def _dispatch_init(args: argparse.Namespace, root: Path):
    return init_project(root, integration=args.integration, interactive=not args.non_interactive,
                        install_git_hooks=args.install_hooks, requirements=args.requirements,
                        profile=args.profile)


def _dispatch(args: argparse.Namespace, root: Path):
    if args.command == "init":
        return _dispatch_init(args, root)
    if args.command == "test":
        return _dispatch_test(args, root)
    direct = {
        "scan": lambda: scan_project(root),
        "doctor": lambda: doctor(Path(".")),
        "check": lambda: check(root),
        "security": lambda: security_scan(root, staged_only=args.staged),
        "integration": lambda: ({
            "list": integration_list,
            "status": integration_status_command,
            "install": lambda path: install(path, args.integration),
        }[args.integration_command])(root),
        "learn": lambda: run_learn(root, args),
        "quiz": lambda: run_quiz_command(root, args),
        "scripts": lambda: generate_scripts(root, agent_command=args.agent_command),
    }
    if args.command in direct:
        return direct[args.command]()
    if args.command in {"tradeoff", "implement", "fix", "review", "sync", "inspect", "update"}:
        return _dispatch_workflow(args, root)
    raise ValueError(f"unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fmt = getattr(args, "format", "text")
    if args.command == "version":
        result = {"schema_version": 1, "command": "framework version", "version": __version__,
                  "source": RELEASE_SOURCE, "platform": platform.system().lower()}
        if fmt == "json":
            import json
            print(json.dumps(result, indent=2))
        else:
            print(f"framework {__version__} ({RELEASE_SOURCE}) on {platform.system()}")
        return 0
    root = Path(getattr(args, "path", ".")).resolve()
    result = _dispatch(args, root)
    print(render(result, fmt))
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

from __future__ import annotations

import argparse
import platform
from pathlib import Path

from .commands.check import check
from .commands.doctor import doctor
from .commands.init import init_project
from .commands.install import install
from .commands.scan import scan_project
from .commands.security import security_scan
from .commands.test import run_tests
from .commands.learn import run_learn
from .commands.quiz import run as run_quiz_command
from .reporting.render import render
from .version import RELEASE_SOURCE, __version__


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--verbose", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="framework", description="Deterministic development framework CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    version = sub.add_parser("version"); _common(version)
    init = sub.add_parser("init"); init.add_argument("path", nargs="?", default="."); init.add_argument("--here", action="store_true"); init.add_argument("--from", dest="requirements"); init.add_argument("--integration", choices=("codex", "claude")); init.add_argument("--install-hooks", action="store_true"); _common(init)
    for name in ("scan", "doctor", "test", "check"):
        command = sub.add_parser(name)
        if name != "doctor": command.add_argument("path", nargs="?", default=".")
        _common(command)
    security = sub.add_parser("security")
    security_sub = security.add_subparsers(dest="security_command", required=True)
    scan = security_sub.add_parser("scan"); scan.add_argument("path", nargs="?", default="."); scan.add_argument("--staged", action="store_true"); _common(scan)
    install_parser = sub.add_parser("install"); install_parser.add_argument("--integration", choices=("codex", "claude"), required=True); install_parser.add_argument("path", nargs="?", default="."); _common(install_parser)
    learn = sub.add_parser("learn")
    learn_sub = learn.add_subparsers(dest="learn_command")
    def learn_common(command):
        command.add_argument("--session-id"); command.add_argument("--observation", dest="observations", action="append", default=[]); command.add_argument("--inference", dest="inferences", action="append", default=[]); command.add_argument("--file", dest="files", action="append", default=[]); command.add_argument("--symbol", dest="symbols", action="append", default=[]); command.add_argument("--task", dest="tasks", action="append", default=[]); command.add_argument("--gate", dest="gates", action="append", default=[]); command.add_argument("--evidence", action="append", default=[])
    start = learn_sub.add_parser("start"); start.add_argument("--agent", default="framework"); start.add_argument("--host", default="framework-cli"); start.add_argument("path", nargs="?", default="."); _common(start)
    for name in ("checkpoint", "compact", "resume", "close"):
        command = learn_sub.add_parser(name); learn_common(command); command.add_argument("path", nargs="?", default="."); _common(command)
    for name in ("summary", "rework"):
        command = learn_sub.add_parser(name); command.add_argument("--session-id"); command.add_argument("path", nargs="?", default="."); _common(command)
    review = learn_sub.add_parser("review"); review.add_argument("lesson_id"); review.add_argument("decision", choices=("approved", "rejected", "edited")); review.add_argument("--content", action="append"); review.add_argument("path", nargs="?", default="."); _common(review)
    handoff = learn_sub.add_parser("handoff"); handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_export = handoff_sub.add_parser("export"); handoff_export.add_argument("--target", default="generic", choices=("generic", "codex", "claude", "antigravity", "new-session")); handoff_export.add_argument("--session-id"); handoff_export.add_argument("--scope-session", dest="scope_sessions", action="append", default=[]); handoff_export.add_argument("--scope-category", dest="scope_categories", action="append", default=[]); handoff_export.add_argument("--scope-file", dest="scope_files", action="append", default=[]); handoff_export.add_argument("--scope-symbol", dest="scope_symbols", action="append", default=[]); handoff_export.add_argument("path", nargs="?", default="."); _common(handoff_export)
    handoff_import = handoff_sub.add_parser("import"); handoff_import.add_argument("package"); handoff_import.add_argument("path", nargs="?", default="."); _common(handoff_import)
    learn_quiz = learn_sub.add_parser("quiz")
    learn_quiz_sub = learn_quiz.add_subparsers(dest="learn_quiz_command", required=True)
    learn_gen = learn_quiz_sub.add_parser("generate"); learn_gen.add_argument("--provider", dest="learn_provider", choices=("local", "external"), default="local"); learn_gen.add_argument("--scope", dest="learn_scope", default="project"); learn_gen.add_argument("path", nargs="?", default="."); _common(learn_gen)
    learn_run = learn_quiz_sub.add_parser("run"); learn_run.add_argument("--category", dest="learn_category"); learn_run.add_argument("--count", dest="learn_count", type=int, default=10); learn_run.add_argument("--answer", dest="learn_answers", action="append"); learn_run.add_argument("path", nargs="?", default="."); _common(learn_run)
    learn_sync = learn_quiz_sub.add_parser("sync"); learn_sync.add_argument("path", nargs="?", default="."); _common(learn_sync)
    learn_export = learn_quiz_sub.add_parser("export"); learn_export.add_argument("--format", dest="learn_quiz_format", choices=("json", "yaml", "markdown"), default="json"); learn_export.add_argument("path", nargs="?", default=".")
    learn.add_argument("path", nargs="?", default=".")
    _common(learn)
    quiz = sub.add_parser("quiz")
    quiz_sub = quiz.add_subparsers(dest="quiz_command", required=True)
    gen = quiz_sub.add_parser("generate"); gen.add_argument("--provider", choices=("local", "external"), default="local"); gen.add_argument("--scope", default="project"); gen.add_argument("path", nargs="?", default="."); _common(gen)
    run = quiz_sub.add_parser("run"); run.add_argument("--category"); run.add_argument("--count", type=int, default=10); run.add_argument("--answer", dest="answers", action="append"); run.add_argument("path", nargs="?", default="."); _common(run)
    quiz_sync = quiz_sub.add_parser("sync"); quiz_sync.add_argument("path", nargs="?", default="."); _common(quiz_sync)
    export = quiz_sub.add_parser("export"); export.add_argument("--format", dest="quiz_format", choices=("json", "yaml", "markdown"), default="json"); export.add_argument("path", nargs="?", default=".")
    quiz.add_argument("path", nargs="?", default=".")
    _common(quiz)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fmt = getattr(args, "format", "text")
    if args.command == "version":
        result = {"schema_version": 1, "command": "framework version", "version": __version__, "source": RELEASE_SOURCE, "platform": platform.system().lower()}
        if fmt == "json":
            import json; print(json.dumps(result, indent=2))
        else: print(f"framework {__version__} ({RELEASE_SOURCE}) on {platform.system()}")
        return 0
    root = Path(getattr(args, "path", ".")).resolve()
    result = _dispatch(args, root)
    print(render(result, fmt))
    return result.exit_code


def _dispatch(args, root: Path):
    if args.command == "init":
        integration = args.integration
        if not args.non_interactive and integration is None:
            try:
                answer = input("Agent integration [codex/claude]: ").strip().lower()
            except EOFError: answer = ""
            integration = answer if answer in {"codex", "claude"} else None
        result = init_project(root, integration=integration, interactive=args.non_interactive and integration is None, install_git_hooks=args.install_hooks)
    elif args.command == "scan": result = scan_project(root)
    elif args.command == "doctor": result = doctor(Path("."))
    elif args.command == "test": result = run_tests(root)
    elif args.command == "check": result = check(root)
    elif args.command == "security": result = security_scan(root, staged_only=args.staged)
    elif args.command == "install": result = install(root, args.integration)
    elif args.command == "learn": result = run_learn(root, args)
    elif args.command == "quiz": result = run_quiz_command(root, args)
    else: raise ValueError(f"unsupported command: {args.command}")
    return result


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

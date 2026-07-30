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
    else: return 2
    print(render(result, fmt))
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

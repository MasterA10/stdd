from __future__ import annotations

from pathlib import Path

from ..config.loader import load_config
from ..quality.engine import QualityEngine
from ..reporting.models import CommandResult
from .security import security_scan
from .test import run_tests


def check(root: Path, *, include_tests: bool = True) -> CommandResult:
    root = root.resolve()
    try: config = load_config(root)
    except FileNotFoundError: config = None
    quality = QualityEngine(root, config).run()
    security = security_scan(root)
    result = CommandResult("framework check", project=quality.project, metadata={"quality": quality.to_dict(), "security": security.to_dict()})
    for finding in [*quality.findings, *security.findings]: result.add(finding)
    if include_tests:
        tests = run_tests(root)
        result.children = tests.children
        if tests.exit_code: result.status, result.exit_code = "blocked", 1
    if security.status == "degraded" and result.exit_code == 0: result.status = "degraded"
    return result

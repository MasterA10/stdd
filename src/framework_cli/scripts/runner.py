from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable


class ScriptRunner:
    def __init__(self, root: Path, allowed_paths: Iterable[Path] | None = None):
        self.root = root.resolve()
        self.allowed_paths = [p.resolve() for p in (allowed_paths or [self.root])]

    def _allowed(self, cwd: Path) -> bool:
        cwd = cwd.resolve()
        return any(cwd == p or p in cwd.parents for p in self.allowed_paths)

    def run(self, args: list[str], *, cwd: Path | None = None, timeout: int = 120, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        workdir = (cwd or self.root).resolve()
        if not args or any(not isinstance(x, str) for x in args):
            raise ValueError("script arguments must be a non-empty list of strings")
        if not self._allowed(workdir):
            raise PermissionError(f"script cwd is outside allowed paths: {workdir}")
        safe_env = {k: v for k, v in (env or os.environ).items() if k not in {"API_KEY", "SECRET", "TOKEN", "PASSWORD"}}
        try:
            return subprocess.run(args, cwd=workdir, env=safe_env, text=True, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(args, 124, str(exc), "timeout")

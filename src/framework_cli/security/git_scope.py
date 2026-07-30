from __future__ import annotations

import fnmatch
from pathlib import Path

from ..git.repository import GitRepository


def parse_gitignore(root: Path) -> list[str]:
    path = root / ".gitignore"
    if not path.exists(): return []
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip() and not line.startswith("#")]


def ignored_by_pattern(path: str, patterns: list[str]) -> bool:
    normalized = path.lstrip("./")
    return any(fnmatch.fnmatch(normalized, p) or fnmatch.fnmatch(Path(normalized).name, p.lstrip("!")) for p in patterns if not p.startswith("!"))


def collect_scope(root: Path, git: GitRepository) -> dict:
    tracked = git.tracked_files()
    staged = git.staged_files()
    return {"tracked": tracked, "staged": staged, "patterns": parse_gitignore(root),
            "git_available": git.available}

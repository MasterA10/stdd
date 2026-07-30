from __future__ import annotations

import subprocess
from pathlib import Path


class GitRepository:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.available = self._run(["rev-parse", "--git-dir"]).returncode == 0

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.root, text=True, capture_output=True, check=False)

    @property
    def branch(self) -> str | None:
        if not self.available: return None
        value = self._run(["branch", "--show-current"]).stdout.strip()
        return value or None

    def tracked_files(self) -> list[str]:
        if not self.available: return []
        return [x for x in self._run(["ls-files", "-z"]).stdout.split("\0") if x]

    def staged_files(self) -> list[str]:
        if not self.available: return []
        return [x for x in self._run(["diff", "--cached", "--name-only", "--diff-filter=ACMR"]).stdout.splitlines() if x]

    def changed_files(self) -> list[str]:
        if not self.available: return []
        names = self._run(["diff", "--name-only", "--diff-filter=ACMR"]).stdout.splitlines()
        names += self.staged_files()
        for line in self._run(["status", "--porcelain=v1"]).stdout.splitlines():
            if len(line) >= 4:
                names.append(line[3:].split(" -> ")[-1])
        return sorted(set(x for x in names if x))

    def diff(self, staged: bool = False) -> str:
        if not self.available: return ""
        return self._run(["diff", "--cached"] if staged else ["diff"]).stdout

    def history(self) -> str:
        if not self.available: return ""
        return self._run(["log", "--all", "--format=%H", "--name-only"]).stdout

    def history_content(self) -> str:
        if not self.available: return ""
        return self._run(["log", "--all", "-p", "--format="]).stdout

    def snapshot(self) -> dict:
        return {"available": self.available, "branch": self.branch, "staged_files": self.staged_files()}

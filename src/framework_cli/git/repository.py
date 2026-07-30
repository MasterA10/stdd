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

    def log_for_paths(self, paths: list[str] | None = None, *, limit: int = 20) -> list[dict[str, str]]:
        if not self.available: return []
        args = ["log", "--all", f"-{limit}", "--date=iso-strict", "--format=%H%x09%an%x09%ad%x09%s"]
        if paths: args.extend(["--", *paths])
        rows = []
        for line in self._run(args).stdout.splitlines():
            commit, author, date, subject = (line.split("\t", 3) + [""] * 4)[:4]
            rows.append({"commit": commit, "author": author, "date": date, "subject": subject})
        return rows

    def blame(self, path: str) -> list[dict[str, str]]:
        if not self.available: return []
        completed = self._run(["blame", "--line-porcelain", "--", path])
        rows: list[dict[str, str]] = []
        current: dict[str, str] = {}
        for line in completed.stdout.splitlines():
            if line and not line.startswith("\t") and len(line.split()) >= 3 and len(line.split()[0]) >= 8:
                if current: rows.append(current)
                parts = line.split()
                current = {"commit": parts[0], "line": parts[2]}
            elif line.startswith("author "):
                current["author"] = line[7:]
            elif line.startswith("summary "):
                current["summary"] = line[8:]
        if current: rows.append(current)
        return rows

    def context(self, paths: list[str] | None = None) -> dict:
        selected = paths or self.changed_files()
        return {"available": self.available, "branch": self.branch,
                "changed_files": selected, "log": self.log_for_paths(selected),
                "blame": {path: self.blame(path)[:20] for path in selected if (self.root / path).exists()},
                "diff": self.diff()[:20000] if self.available else ""}

    def snapshot(self) -> dict:
        return {"available": self.available, "branch": self.branch, "staged_files": self.staged_files()}

from __future__ import annotations

import fnmatch
from pathlib import Path

from .fingerprint import fingerprint
from .git_scope import collect_scope
from .patterns import entropy, matches
from ..git.repository import GitRepository
from ..reporting.models import CommandResult, Finding


class SecurityScanner:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.git = GitRepository(self.root)

    def _files(self) -> list[Path]:
        ignored = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
        paths = []
        for path in self.root.rglob("*"):
            if not path.is_file() or any(x in ignored for x in path.parts): continue
            if ".framework" in path.parts:
                framework_index = path.parts.index(".framework")
                if len(path.parts) > framework_index + 1 and path.parts[framework_index + 1] in {"reports", "security"}: continue
            if path.name in {"index.db", "index.db-shm", "index.db-wal"}: continue
            paths.append(path)
        return paths

    def _add_policy_findings(self, result: CommandResult, patterns: list[str]) -> None:
        if not (self.root / ".gitignore").exists():
            result.add(Finding("SEC-IGNORE", "security", "warning", "open", ".gitignore", 1, "missing-gitignore", "No .gitignore protects environment files", "Add .env and credential exclusions to .gitignore", {}, fingerprint(".gitignore")))
        elif not any(p in {".env", ".env.*", "*.env"} for p in patterns):
            result.add(Finding("SEC-IGNORE", "security", "warning", "open", ".gitignore", 1, "env-not-ignored", "Git ignore rules do not clearly exclude environment files", "Add .env and .env.* rules while allowing fictitious examples", {}, fingerprint("env-not-ignored")))

    def _scan_path(self, result: CommandResult, path: Path) -> None:
        rel = str(path.relative_to(self.root))
        if (path.name == ".env" or path.name.startswith(".env.")) and path.name not in {".env.example", ".env.sample", ".env.template"}:
            result.add(Finding("SEC-ENV", "security", "block", "open", rel, 1, "environment-file", "Environment file cannot be versioned", "Remove the file and rotate its credentials", {}, fingerprint(rel)))
            return
        try: lines = path.read_text(errors="replace").splitlines()
        except OSError: return
        for number, line in enumerate(lines, 1):
            for rule, value in matches(line):
                fp = fingerprint(rel, str(number), rule)
                result.add(Finding("SEC-" + fp[7:15], "security", "block", "open", rel, number, rule, "Sensitive value detected; value redacted", "Move the value to a secret manager and rotate it", {"entropy": round(entropy(value), 2)}, fp, {"source": "workspace"}))

    def _scan_text(self, result: CommandResult, text: str, source: str) -> None:
        for number, line in enumerate(text.splitlines(), 1):
            for rule, value in matches(line):
                fp = fingerprint(source, str(number), rule)
                result.add(Finding("SEC-" + fp[7:15], "security", "block", "open", source, number, rule, "Sensitive value detected; value redacted", "Rotate the credential and remove it from history", {"entropy": round(entropy(value), 2)}, fp, {"source": source}))

    def scan(self, *, staged_only: bool = False, history: bool = True) -> CommandResult:
        result = CommandResult("framework security scan", metadata={"git": self.git.snapshot()})
        scope = collect_scope(self.root, self.git)
        patterns = scope["patterns"]
        self._add_policy_findings(result, patterns)
        tracked_env = [p for p in scope["tracked"] if p == ".env" or fnmatch.fnmatch(p, ".env.*") and not p in {".env.example", ".env.sample", ".env.template"}]
        for path in tracked_env:
            result.add(Finding("SEC-ENV", "security", "block", "open", path, 1, "tracked-env-file", "Environment file must not be versioned", "Remove it from Git and rotate its credentials", fingerprint(path)))
        files = [self.root / p for p in scope["staged"]] if staged_only and self.git.available else self._files()
        for path in files: self._scan_path(result, path)
        if staged_only and self.git.available:
            self._scan_text(result, self.git.diff(staged=True), "<staged-diff>")
        elif history and self.git.available:
            self._scan_text(result, self.git.history_content(), "<git-history>")
        if not self.git.available:
            result.status = "degraded" if result.exit_code == 0 else result.status
            result.metadata["degraded"] = ["history", "staged_diff", "commit_blocking"]
        return result

from __future__ import annotations

import re
from pathlib import Path

from ..security.fingerprint import fingerprint
from ..reporting.models import Finding


def normalized_lines(path: Path) -> list[str]:
    try: lines = path.read_text(errors="replace").splitlines()
    except OSError: return []
    return [re.sub(r"\s+", " ", x.strip()) for x in lines if x.strip() and not x.strip().startswith(("#", "//"))]


def find_duplicates(root: Path, threshold: int = 6) -> list[Finding]:
    blocks: dict[tuple[str, ...], tuple[Path, int]] = {}
    findings: list[Finding] = []
    ignored = {".framework", ".venv", "venv", "node_modules", "tests", ".git"}
    paths = [p for p in root.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".ts", ".tsx", ".jsx"} and not ignored.intersection(p.parts)]
    for path in paths:
        lines = normalized_lines(path)
        for start in range(max(0, len(lines) - threshold + 1)):
            block = tuple(lines[start:start + threshold])
            if len(block) < threshold: continue
            previous = blocks.get(block)
            if previous and previous[0] != path:
                rel = str(path.relative_to(root))
                fp = fingerprint(rel, str(start + 1), "duplicate")
                findings.append(Finding("DUP-" + fp[7:15], "duplication", "block", "open", rel, start + 1,
                    "duplicate_block_statements", f"Repeated block of {threshold} normalized statements", "Extract a shared function or module", {"lines": threshold}, fp))
            else: blocks[block] = (path, start)
    return findings

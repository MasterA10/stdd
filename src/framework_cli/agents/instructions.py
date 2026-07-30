from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


NAMES = ("AGENTS.md", "CLAUDE.md", "CLOUD.md", "GEMINI.md")


@dataclass
class InstructionFile:
    path: str
    scope: str
    checksum: str
    content: str


@dataclass
class InstructionChain:
    files: list[InstructionFile]
    conflicts: list[str]

    @property
    def valid(self) -> bool:
        return not self.conflicts


def discover_instruction_chain(root: Path, target: Path | None = None) -> InstructionChain:
    root, target = root.resolve(), (target or root).resolve()
    if root not in target.parents and target != root: raise ValueError("target outside root")
    directories = list(reversed([*target.parents])) + [target]
    directories = [d for d in directories if root == d or root in d.parents]
    files: list[InstructionFile] = []
    for directory in directories:
        for name in NAMES:
            path = directory / name
            if path.exists():
                content = path.read_text(errors="replace")
                files.append(InstructionFile(str(path.relative_to(root)), str(directory.relative_to(root)), hashlib.sha256(content.encode()).hexdigest(), content))
    conflicts: list[str] = []
    for item in files:
        if "CONFLICT:" in item.content or "<<<<<<<" in item.content:
            conflicts.append(item.path)
    return InstructionChain(files, conflicts)

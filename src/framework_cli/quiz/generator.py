from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from ..security.fingerprint import fingerprint
from .models import KnowledgeQuestion


def source_catalog(root: Path) -> list[dict[str, Any]]:
    catalog = []
    for path in sorted(root.rglob("*.py")):
        if {".git", ".venv", "venv", ".framework", "tests"}.intersection(path.parts): continue
        try: tree = ast.parse(path.read_text(errors="replace"))
        except (OSError, SyntaxError, UnicodeDecodeError): continue
        rel = str(path.relative_to(root)); text = path.read_text(errors="replace")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                source_id = f"{rel}:{node.name}"
                catalog.append({"kind": "symbol", "id": source_id, "fingerprint": fingerprint(source_id, text),
                                "name": node.name, "type": "class" if isinstance(node, ast.ClassDef) else "function"})
    for filename in ("plan.md", "AGENTS.md"):
        path = root / filename
        if path.exists():
            source_id = filename
            catalog.append({"kind": "decision", "id": source_id, "fingerprint": fingerprint(source_id, path.read_text(errors="replace")), "name": filename, "type": "document"})
    return catalog


def generate_local(root: Path, *, scope: str = "project", limit: int = 20) -> list[KnowledgeQuestion]:
    questions = []
    for source in source_catalog(root)[:limit]:
        category = "architecture" if source["type"] == "class" else "practice" if source["type"] == "function" else "trade-off"
        options = ["A shared boundary", "A global mutable state", "An unvalidated side effect"]
        questions.append(KnowledgeQuestion(
            question_id=f"question-{fingerprint(source['id'])[7:23]}", revision=1, category=category,
            prompt=f"What kind of codebase source is {source['name']}?", options=options,
            correct_option="A shared boundary", explanation="The local fallback uses a safe conceptual answer and remains reviewable.",
            difficulty="easy", sources=[{k: source[k] for k in ("kind", "id", "fingerprint")}],
            provenance={"provider": "local", "version": "1", "scope": scope}, fingerprint=source["fingerprint"]))
    return questions

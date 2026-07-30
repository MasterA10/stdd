from __future__ import annotations

import ast
from pathlib import Path

from ..reporting.models import Finding
from ..security.fingerprint import fingerprint


def find_god_classes(root: Path, threshold: int = 15) -> list[Finding]:
    findings = []
    for path in root.rglob("*.py"):
        if {".framework", ".venv", "venv", "node_modules", "tests", ".git"}.intersection(path.parts): continue
        try: tree = ast.parse(path.read_text(errors="replace"))
        except (OSError, SyntaxError, UnicodeDecodeError): continue
        rel = str(path.relative_to(root))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [x for x in node.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
                fields = {n.targets[0].attr for n in ast.walk(node) if isinstance(n, ast.Assign) for _ in [0] if n.targets and isinstance(n.targets[0], ast.Attribute) and isinstance(n.targets[0].value, ast.Name) and n.targets[0].value.id == "self"}
                score = len(methods) + len(fields)
                if score > threshold:
                    fp = fingerprint(rel, str(node.lineno), "god-class")
                    findings.append(Finding("GOD-" + fp[7:15], "god_class", "block", "open", rel, node.lineno, "god_class", f"Class {node.name} has God-class score {score}", "Split responsibilities behind cohesive collaborators", {"name": node.name, "methods": len(methods), "fields": len(fields), "value": score, "threshold": threshold}, fp))
    return findings

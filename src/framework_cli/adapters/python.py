from __future__ import annotations

import ast
import sys
from pathlib import Path

from .base import BaseAdapter, Detection


class PythonAdapter(BaseAdapter):
    id = "python"
    capabilities = {"detection", "ast", "tests", "static_rules"}

    def detect(self, root: Path) -> list[Detection]:
        out: list[Detection] = []
        evidence: list[str] = []
        if (root / "pyproject.toml").exists(): evidence.append("pyproject.toml")
        if list(root.rglob("*.py")): evidence.append("*.py")
        if evidence:
            out.append(Detection("language", "python", .99 if "pyproject.toml" in evidence else .85, evidence))
        if (root / "manage.py").exists(): out.append(Detection("framework", "django", .99, ["manage.py"]))
        if (root / "requirements.txt").exists(): out.append(Detection("dependency", "pip", .9, ["requirements.txt"]))
        return out

    def symbols(self, path: Path) -> list[dict]:
        try: tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError): return []
        symbols = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                end = getattr(node, "end_lineno", node.lineno)
                symbols.append({"kind": "class" if isinstance(node, ast.ClassDef) else "function", "name": node.name,
                                "line": node.lineno, "end_line": end, "logical_lines": end - node.lineno + 1,
                                "complexity": sum(isinstance(x, (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.Match)) for x in ast.walk(node))})
        return symbols

    def test_commands(self, root: Path) -> list[list[str]]:
        if (root / "pytest.ini").exists() or (root / "tests").exists() or (root / "pyproject.toml").exists():
            return [[sys.executable, "-m", "pytest"]]
        return []

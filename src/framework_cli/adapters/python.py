from __future__ import annotations

import ast
import hashlib
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
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            return []

        symbols: list[dict] = []

        def visit(nodes: list[ast.stmt], parent: str = "") -> None:
            for node in nodes:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                qualified = f"{parent}.{node.name}" if parent else node.name
                end = getattr(node, "end_lineno", node.lineno)
                is_class = isinstance(node, ast.ClassDef)
                if is_class:
                    signature = f"class {qualified}"
                else:
                    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                    returns = ast.unparse(node.returns) if node.returns else "unknown"
                    signature = f"{prefix}{qualified}({ast.unparse(node.args)}) -> {returns}"
                complexity = sum(isinstance(item, (ast.If, ast.For, ast.While, ast.Try,
                                                    ast.BoolOp, ast.Match, ast.IfExp))
                                 for item in ast.walk(node))
                doc = ast.get_docstring(node)
                symbols.append({"kind": "class" if is_class else "function",
                                "name": node.name, "qualified_name": qualified,
                                "line": node.lineno, "end_line": end,
                                "signature": signature,
                                "description": (doc.splitlines()[0] if doc else
                                                 "Descrição não encontrada no código-fonte."),
                                "description_status": "documented" if doc else "missing",
                                "logical_lines": end - node.lineno + 1,
                                "complexity": complexity,
                                "body_fingerprint": hashlib.sha256(
                                    ast.dump(node, include_attributes=False).encode("utf-8")
                                ).hexdigest()})
                visit(node.body, qualified)

        visit(tree.body)
        return symbols

    def test_commands(self, root: Path) -> list[list[str]]:
        if (root / "pytest.ini").exists() or (root / "tests").exists() or (root / "pyproject.toml").exists():
            return [[sys.executable, "-m", "pytest"]]
        return []

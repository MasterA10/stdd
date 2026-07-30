from __future__ import annotations

import json
import re
from pathlib import Path

from .base import BaseAdapter, Detection


class JavaScriptAdapter(BaseAdapter):
    id = "javascript"
    capabilities = {"detection", "tests", "static_rules"}

    def detect(self, root: Path) -> list[Detection]:
        package = root / "package.json"
        if not package.exists():
            return []
        try: data = json.loads(package.read_text())
        except (OSError, ValueError): data = {}
        value = "typescript" if (root / "tsconfig.json").exists() else "javascript"
        results = [Detection("language", value, .99, ["package.json"])]
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for key, framework in (("react", "react"), ("next", "next"), ("express", "express")):
            if key in deps: results.append(Detection("framework", framework, .95, ["package.json"]))
        return results

    def test_commands(self, root: Path) -> list[list[str]]:
        package = root / "package.json"
        if not package.exists(): return []
        try: scripts = json.loads(package.read_text()).get("scripts", {})
        except (OSError, ValueError): scripts = {}
        return [["npm", "test"]] if "test" in scripts else []

    def symbols(self, path: Path) -> list[dict]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []
        symbols: list[dict] = []
        patterns = (
            (r"(?:async\s+)?function\s+([\w$]+)\s*\(([^)]*)\)", "function"),
            (r"(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", "function"),
            (r"class\s+([\w$]+)", "class"),
        )
        for pattern, kind in patterns:
            for match in re.finditer(pattern, text):
                name = match.group(1)
                line = text.count("\n", 0, match.start()) + 1
                args = match.group(2) if kind == "function" and match.lastindex == 2 else ""
                signature = f"{name}({args}) -> unknown" if kind == "function" else f"class {name}"
                symbols.append({"kind": kind, "name": name, "qualified_name": name,
                                "line": line, "end_line": line, "signature": signature,
                                "description": "Descrição não encontrada no código-fonte.",
                                "description_status": "missing", "logical_lines": 1,
                                "complexity": 0})
        return sorted(symbols, key=lambda item: (item["line"], item["name"]))

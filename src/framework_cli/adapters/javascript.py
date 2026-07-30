from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .base import BaseAdapter, Detection


def _jsdoc(text: str, start: int) -> tuple[str, str]:
    prefix = text[:start].rstrip()
    match = re.search(r"/\*\*(.*?)\*/\s*$", prefix, re.DOTALL)
    if not match:
        return "Descrição não encontrada no código-fonte.", "missing"
    for line in match.group(1).splitlines():
        clean = re.sub(r"^\s*\*\s?", "", line).strip()
        if clean and not clean.startswith("@"):
            return clean, "documented"
    return "Descrição não encontrada no código-fonte.", "missing"


def _js_body_end(text: str, start: int) -> int:
    opening = text.find("{", start)
    if opening < 0:
        newline = text.find("\n", start)
        return newline if newline >= 0 else len(text)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return len(text)


def _javascript_symbol(text: str, match: re.Match[str], kind: str) -> dict:
    name = match.group(1)
    line = text.count("\n", 0, match.start()) + 1
    args = match.group(2) if kind == "function" and match.lastindex == 2 else ""
    signature = f"{name}({args}) -> unknown" if kind == "function" else f"class {name}"
    description, description_status = _jsdoc(text, match.start())
    end = _js_body_end(text, match.start())
    body = text[match.start():end]
    return {"kind": kind, "name": name, "qualified_name": name,
            "line": line, "end_line": text.count("\n", 0, end) + 1,
            "signature": signature, "description": description,
            "description_status": description_status,
            "logical_lines": text.count("\n", match.start(), end) + 1,
            "complexity": len(re.findall(r"\b(?:if|for|while|catch|case)\b", body)),
            "body_fingerprint": hashlib.sha256(body.encode("utf-8")).hexdigest()}


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
                symbols.append(_javascript_symbol(text, match, kind))
        return sorted(symbols, key=lambda item: (item["line"], item["name"]))

#!/usr/bin/env python3
"""Adapter local de análise estática Python para o protocolo do STDD.

Usa somente ``ast`` e o conteúdo do workspace. Não importa nem executa o código
analisado; a saída é determinística e contém fatos primários para o STDD derivar
traceabilidade, arquivos e testes.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "1"
IGNORED_PARTS = {".git", ".stdd", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}


def relative_module(root: Path, path: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def stable_identity(file: str, qualified_name: str, line: int, end_line: int) -> str:
    raw = f"{file}:{qualified_name}:{line}:{end_line}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def source_text(node: ast.AST, lines: list[str]) -> str:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start)
    return "\n".join(lines[max(0, start - 1) : end])


def function_lines(node: ast.AST) -> int:
    return max(1, getattr(node, "end_lineno", getattr(node, "lineno", 1)) - getattr(node, "lineno", 1) + 1)


def cyclomatic(node: ast.AST) -> int:
    value = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.Match)):  # noqa: UP038
            value += 1
        elif isinstance(child, ast.BoolOp):
            value += max(0, len(child.values) - 1)
        elif isinstance(child, ast.comprehension):
            value += 1 + len(child.ifs)
    return value


def max_nesting(node: ast.AST) -> int:
    branching = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)

    def visit(current: ast.AST, depth: int) -> int:
        next_depth = depth + 1 if isinstance(current, branching) else depth
        return max([next_depth, *(visit(child, next_depth) for child in ast.iter_child_nodes(current))])

    return max(0, visit(node, 0))


def parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if node.args.vararg:
        args.append(node.args.vararg)
    if node.args.kwarg:
        args.append(node.args.kwarg)
    return [item.arg for item in args]


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


@dataclass
class ParsedFile:
    path: str
    module: str
    tree: ast.Module
    lines: list[str]
    symbols: list[dict[str, Any]] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    module_dependencies: set[str] = field(default_factory=set)


def discover_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.py"))
        if path.is_file() and not IGNORED_PARTS.intersection(path.relative_to(root).parts)
    ]


def parse_files(root: Path) -> list[ParsedFile]:
    parsed: list[ParsedFile] = []
    for path in discover_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=relative)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        item = ParsedFile(relative, relative_module(root, path), tree, text.splitlines())
        for statement in tree.body:
            if isinstance(statement, ast.Import):
                for alias in statement.names:
                    item.aliases[alias.asname or alias.name.split(".")[0]] = alias.name
                    item.module_dependencies.add(alias.name)
            elif isinstance(statement, ast.ImportFrom):
                base = ("." * statement.level) + (statement.module or "")
                for alias in statement.names:
                    item.aliases[alias.asname or alias.name] = f"{base}.{alias.name}".strip(".")
                if statement.module:
                    item.module_dependencies.add(statement.module)
        parsed.append(item)
    return parsed


def collect_symbols(parsed: list[ParsedFile]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    def add_function(item: ParsedFile, node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str, kind: str) -> None:
        qualified = f"{item.module}.{prefix}{node.name}"
        signature = f"{node.name}({', '.join(parameters(node))})"
        symbol = {
            "symbol_id": f"{item.path}:{qualified}",
            "qualified_name": qualified,
            "kind": kind,
            "name": node.name,
            "signature": signature,
            "visibility": "private" if node.name.startswith("_") else "public",
            "file": item.path,
            "line": node.lineno,
            "column": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_column": getattr(node, "end_col_offset", node.col_offset),
            "identity": stable_identity(item.path, qualified, node.lineno, getattr(node, "end_lineno", node.lineno)),
            "source": "python_ast",
            "_node": node,
        }
        item.symbols.append(symbol)
        index[qualified] = symbol

    for item in parsed:
        for statement in item.tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                add_function(item, statement, "", "function")
            elif isinstance(statement, ast.ClassDef):
                class_name = f"{item.module}.{statement.name}"
                class_symbol = {
                    "symbol_id": f"{item.path}:{class_name}",
                    "qualified_name": class_name,
                    "kind": "class",
                    "name": statement.name,
                    "signature": statement.name,
                    "visibility": "private" if statement.name.startswith("_") else "public",
                    "file": item.path,
                    "line": statement.lineno,
                    "column": statement.col_offset,
                    "end_line": getattr(statement, "end_lineno", statement.lineno),
                    "end_column": getattr(statement, "end_col_offset", statement.col_offset),
                    "identity": stable_identity(item.path, class_name, statement.lineno, getattr(statement, "end_lineno", statement.lineno)),
                    "source": "python_ast",
                    "_node": statement,
                }
                item.symbols.append(class_symbol)
                index[class_name] = class_symbol
                for child in statement.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        add_function(item, child, f"{statement.name}.", "method")
    return index


def resolve_target(name: str | None, item: ParsedFile, current: dict[str, Any], index: dict[str, dict[str, Any]]) -> str | None:
    if not name:
        return None
    if name in item.aliases:
        imported = item.aliases[name]
        if imported in index:
            return imported
        return imported
    if name in index:
        return name
    if "." in name and name in index:
        return name
    candidate = f"{item.module}.{name}"
    if candidate in index:
        return candidate
    if current.get("qualified_name", "").rsplit(".", 1)[0] + "." + name in index:
        return current["qualified_name"].rsplit(".", 1)[0] + "." + name
    matches = [qualified for qualified in index if qualified.endswith(f".{name}")]
    return matches[0] if len(matches) == 1 else None


def build_analysis(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_files(root)
    index = collect_symbols(parsed)
    dependencies: list[dict[str, Any]] = []
    complexity: list[dict[str, Any]] = []
    structural: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    quality = config.get("static_analysis", {}).get("quality", {}) if isinstance(config.get("static_analysis"), dict) else {}
    function_limits = quality.get("functions", {}) if isinstance(quality, dict) else {}
    max_lines = function_limits.get("max_lines", {}) if isinstance(function_limits, dict) else {}
    max_complexity = function_limits.get("max_complexity", {}) if isinstance(function_limits, dict) else {}
    line_warning, line_blocking = int(max_lines.get("warning", 40)), int(max_lines.get("blocking", 100))
    complexity_warning, complexity_blocking = int(max_complexity.get("warning", 10)), int(max_complexity.get("blocking", 25))

    for item in parsed:
        classes = [symbol for symbol in item.symbols if symbol["kind"] == "class"]
        functions = [symbol for symbol in item.symbols if symbol["kind"] in {"function", "method"}]
        structural.append({
            "file": item.path,
            "lines": len(item.lines),
            "classes": len(classes),
            "functions": len(functions),
            "imports": len(item.module_dependencies),
            "source": "python_ast",
        })
        for module in sorted(item.module_dependencies):
            dependencies.append({"source": item.module, "target": module, "kind": "import", "file": item.path, "source_tool": "python_ast"})
        for symbol in functions:
            node = symbol["_node"]
            lines = function_lines(node)
            branches = cyclomatic(node)
            nesting = max_nesting(node)
            metrics = {
                "symbol_id": symbol["symbol_id"],
                "qualified_name": symbol["qualified_name"],
                "file": item.path,
                "line": symbol["line"],
                "lines": lines,
                "parameters": len(parameters(node)),
                "cyclomatic": branches,
                "max_nesting": nesting,
                "returns": sum(isinstance(child, ast.Return) for child in ast.walk(node)),
                "calls": sum(isinstance(child, ast.Call) for child in ast.walk(node)),
                "source": "python_ast",
            }
            complexity.append(metrics)
            if lines > line_blocking or lines > line_warning:
                findings.append({"kind": "long_function", "severity": "blocking" if lines > line_blocking else "warning", "file": item.path, "symbol_id": symbol["symbol_id"], "value": lines, "limit": line_blocking if lines > line_blocking else line_warning, "evidence": f"{lines} linhas em {symbol['qualified_name']}"})
            if branches > complexity_blocking or branches > complexity_warning:
                findings.append({"kind": "high_complexity", "severity": "blocking" if branches > complexity_blocking else "warning", "file": item.path, "symbol_id": symbol["symbol_id"], "value": branches, "limit": complexity_blocking if branches > complexity_blocking else complexity_warning, "evidence": f"complexidade ciclomática {branches}"})
            if len(parameters(node)) > 9 or len(parameters(node)) > 5:
                findings.append({"kind": "too_many_parameters", "severity": "blocking" if len(parameters(node)) > 9 else "warning", "file": item.path, "symbol_id": symbol["symbol_id"], "value": len(parameters(node)), "limit": 9 if len(parameters(node)) > 9 else 5, "evidence": f"{len(parameters(node))} parâmetros"})
            if nesting > 6 or nesting > 4:
                findings.append({"kind": "deep_nesting", "severity": "blocking" if nesting > 6 else "warning", "file": item.path, "symbol_id": symbol["symbol_id"], "value": nesting, "limit": 6 if nesting > 6 else 4, "evidence": f"profundidade máxima {nesting}"})
            for call in ast.walk(node):
                if not isinstance(call, ast.Call):
                    continue
                target = resolve_target(dotted_name(call.func), item, symbol, index)
                if target and target in index:
                    target_file = index[target]["file"]
                    kind = "test" if item.path.startswith("tests/") or "/tests/" in item.path else "calls"
                    dependencies.append({"source": symbol["qualified_name"], "target": target, "kind": kind, "file": target_file, "source_file": item.path, "source_tool": "python_ast"})
    for symbol in index.values():
        symbol.pop("_node", None)
    dependencies = sorted({json.dumps(item, sort_keys=True, ensure_ascii=False): item for item in dependencies}.values(), key=lambda item: (item.get("source", ""), item.get("target", ""), item.get("kind", ""), item.get("file", "")))
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "passed",
        "capabilities": {"symbols": True, "dependencies": True, "complexity": True, "structural_metrics": True, "changes": False},
        "symbols": sorted((symbol for symbol in index.values()), key=lambda item: (item["file"], item["line"], item["qualified_name"])),
        "dependencies": dependencies,
        "complexity": sorted(complexity, key=lambda item: (item["file"], item["line"], item["qualified_name"])),
        "structural_metrics": sorted(structural, key=lambda item: item["file"]),
        "quality_findings": sorted(findings, key=lambda item: (item["file"], item.get("symbol_id", ""), item["kind"])),
        "changes": [],
        "warnings": ["changes_unavailable: adapter não recebe snapshot anterior do código"],
        "errors": [],
    }


def main() -> int:
    try:
        request = json.load(sys.stdin)
        root = Path(request["project_path"]).resolve()
        config_path = root / ".stdd" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        print(json.dumps(build_analysis(root, config), ensure_ascii=False, sort_keys=True))
        return 0
    except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(json.dumps({
            "contract_version": CONTRACT_VERSION,
            "status": "blocked",
            "capabilities": {},
            "symbols": [], "dependencies": [], "complexity": [], "structural_metrics": [], "quality_findings": [], "changes": [], "warnings": [],
            "errors": [f"python_adapter_error:{error.__class__.__name__}"],
        }, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Dispatcher local do Looper para Python, JavaScript/TypeScript e PHP.

O dispatcher mantém um contrato único e delega cada linguagem ao parser nativo
disponível no projeto. Nenhuma mensagem de diagnóstico é escrita no stdout.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".php"}
IGNORED = {".git", ".looper", ".venv", "venv", "node_modules", "vendor", "dist", "build", "coverage", "draw_assets", "__pycache__", ".pytest_cache"}
BASE = ("symbols", "dependencies", "technologies", "external_logic", "complexity", "structural_metrics", "quality_findings", "changes")


def report(status="passed"):
    return {"contract_version": "1", "status": status, "capabilities": {}, **{key: [] for key in BASE}, "warnings": [], "errors": []}


def source_files(root: Path):
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in EXTENSIONS and not IGNORED.intersection(path.relative_to(root).parts))


def rel(root: Path, path: Path):
    return path.relative_to(root).as_posix()


def module_from_path(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    without_extension = os.path.splitext(relative)[0]
    module_parts = list(Path(without_extension).parts)
    if "src" in module_parts:
        module_parts = module_parts[module_parts.index("src") + 1 :]
    if module_parts and module_parts[-1] == "__init__":
        module_parts.pop()
    return ".".join(module_parts)


def quality_config(root: Path):
    try:
        data = json.loads((root / ".looper" / "config.json").read_text(encoding="utf-8"))
        quality = data.get("static_analysis", {}).get("quality", {})
    except (OSError, ValueError, TypeError):
        quality = {}
    functions = quality.get("functions", {}) if isinstance(quality, dict) else {}
    tests = quality.get("tests", {}) if isinstance(quality, dict) else {}
    return {
        "lines": functions.get("max_lines", {"warning": 100, "blocking": 150}),
        "complexity": functions.get("max_complexity", {"warning": 10, "blocking": 25}),
        "tests": tests.get("max_lines", {"warning": 80, "blocking": 160}),
        "parameters": {"warning": 5, "blocking": 9},
        "depth": {"warning": 4, "blocking": 6},
    }


def severity(value, limits):
    if value > int(limits.get("blocking", 0)):
        return "blocking"
    if value > int(limits.get("warning", 0)):
        return "warning"
    return None


def py_adapter(root: Path, result: dict):
    limits = quality_config(root)
    index = {}
    parsed = []
    for path in source_files(root):
        if path.suffix != ".py":
            continue
        relative = rel(root, path)
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=relative)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            result["warnings"].append(f"python_parse_unavailable:{relative}:{exc.__class__.__name__}")
            continue
        module = module_from_path(root, path)
        parsed.append((path, relative, module, text, tree))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                qualified = f"{module}.{name}"
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                symbol_id = f"{relative}:{qualified}"
                symbol = {"symbol_id": symbol_id, "qualified_name": qualified, "kind": kind, "name": name, "file": relative, "line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno), "source": "python_ast", "_node": node}
                index[qualified] = symbol
                result["symbols"].append({key: value for key, value in symbol.items() if key != "_node"})
    for path, relative, module, text, tree in parsed:
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        result["structural_metrics"].append({"file": relative, "lines": len(text.splitlines()), "classes": sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree)), "functions": sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree)), "imports": len(imports), "source": "python_ast"})
        result["dependencies"].extend({"source": module, "target": item, "kind": "import", "file": relative, "source_tool": "python_ast"} for item in sorted(imports))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            qualified = f"{module}.{node.name}"
            symbol_id = f"{relative}:{qualified}"
            lines = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
            params = len(node.args.posonlyargs + node.args.args + node.args.kwonlyargs) + bool(node.args.vararg) + bool(node.args.kwarg)
            cyclomatic = 1 + sum(isinstance(item, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.Match, ast.comprehension)) for item in ast.walk(node))
            depth = 0
            for item in ast.walk(node):
                if isinstance(item, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)):
                    depth = max(depth, 1)
            result["complexity"].append({"symbol_id": symbol_id, "qualified_name": qualified, "file": relative, "line": node.lineno, "lines": lines, "parameters": params, "cyclomatic": cyclomatic, "max_depth": depth, "source": "python_ast"})
            checks = [("long_function", lines, limits["lines"]), ("high_complexity", cyclomatic, limits["complexity"]), ("too_many_parameters", params, limits["parameters"]), ("deep_nesting", depth, limits["depth"])]
            for kind, value, threshold in checks:
                level = severity(value, threshold)
                if level:
                    result["quality_findings"].append({"kind": kind, "severity": level, "file": relative, "symbol_id": symbol_id, "value": value, "limit": threshold[level], "evidence": f"{kind}:{value}", "source": "python_ast"})
    result["capabilities"].update({"symbols": True, "dependencies": True, "complexity": True, "structural_metrics": True, "changes": False})
    result["warnings"].append("changes_unavailable_without_git_symbol_baseline")


def external_adapter(root: Path, command: list[str], result: dict, request: dict):
    try:
        process = subprocess.run(command, cwd=root, input=json.dumps(request), text=True, capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        result["warnings"].append(f"adapter_unavailable:{command[0]}:{exc.__class__.__name__}")
        return
    if process.returncode != 0:
        result["errors"].append(f"adapter_exit_code:{command[0]}:{process.returncode}")
        result["status"] = "blocked"
        return
    try:
        child = json.loads(process.stdout)
    except ValueError:
        result["errors"].append(f"adapter_output_invalid:{command[0]}")
        result["status"] = "blocked"
        return
    if child.get("status") == "blocked":
        result["status"] = "blocked"
    for key in BASE:
        result[key].extend(child.get(key, []))
    for key in ("warnings", "errors"):
        result[key].extend(child.get(key, []))
    result["capabilities"].update(child.get("capabilities", {}))


def main():
    try:
        request = json.load(sys.stdin)
        root = Path(request["project_path"]).resolve()
        if not root.is_dir():
            raise ValueError("project_path inválido")
        result = report()
        if any(path.suffix == ".py" for path in source_files(root)):
            py_adapter(root, result)
        js = any(path.suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"} for path in source_files(root))
        js_adapter = root / ".looper" / "adapters" / "js_ts_static_adapter.js"
        if js and js_adapter.exists():
            external_adapter(root, ["node", str(js_adapter)], result, request)
        php = any(path.suffix == ".php" for path in source_files(root))
        php_adapter = root / ".looper" / "adapters" / "php_static_adapter.php"
        if php and php_adapter.exists() and shutil_which("php"):
            external_adapter(root, ["php", str(php_adapter)], result, request)
        result["status"] = "blocked" if result["errors"] else result["status"]
        for key in BASE:
            result[key] = sorted({json.dumps(item, sort_keys=True, ensure_ascii=False): item for item in result[key]}.values(), key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        error = report("blocked"); error["errors"] = [f"dispatcher_error:{exc.__class__.__name__}"]; print(json.dumps(error, ensure_ascii=False, sort_keys=True)); return 0
    return 0


def shutil_which(command):
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    raise SystemExit(main())

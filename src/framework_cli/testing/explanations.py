from __future__ import annotations

import ast
import builtins
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config.loader import load_config
from ..reporting.models import CommandResult


MARKER_START = "@framework:explanations:start"
MARKER_END = "@framework:explanations:end"
SUPPORTED = {".py", ".js", ".jsx", ".ts", ".tsx"}
PYTHON_BUILTINS = set(dir(builtins)) | {"assert", "len", "range", "str", "int", "dict", "list"}
JS_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "typeof"}


@dataclass(frozen=True)
class Symbol:
    name: str
    qualified_name: str
    signature: str
    description: str
    source: str
    kind: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "qualified_name": self.qualified_name,
                "signature": self.signature, "description": self.description,
                "source": self.source, "kind": self.kind, "line": self.line}


def _safe_relative(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise ValueError("test path must remain inside project root")
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"unsupported test language: {path.suffix}")
    return path


def _module_path(root: Path, importer: Path, module: str, level: int = 0) -> Path | None:
    base = importer.parent
    if level:
        for _ in range(level - 1):
            base = base.parent
        candidate = base / Path(*module.split(".")) if module else base
    else:
        candidate = root / Path(*module.split("."))
    for path in (candidate.with_suffix(".py"), candidate / "__init__.py"):
        if path.exists():
            return path
    return None


def _annotation(node: ast.AST | None) -> str:
    return ast.unparse(node) if node is not None else "unknown"


def _python_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = ast.unparse(node.args)
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return f"{prefix}{node.name}({args}) -> {_annotation(node.returns)}"


def _python_symbols(path: Path) -> dict[str, Symbol]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    symbols: dict[str, Symbol] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or "Descrição não encontrada no código-fonte."
            symbols[node.name] = Symbol(node.name, node.name, _python_signature(node),
                                        doc.splitlines()[0], str(path), "function", node.lineno)
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or "Descrição não encontrada no código-fonte."
            symbols[node.name] = Symbol(node.name, node.name, f"class {node.name}",
                                        doc.splitlines()[0], str(path), "class", node.lineno)
    return symbols


def _flatten_attribute(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _flatten_attribute(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _resolve_python_symbol(root: Path, test_path: Path, aliases: dict[str, tuple[str, int]], name: str) -> Symbol | None:
    imported, level = aliases.get(name, (name, 0))
    module, _, member = imported.rpartition(".")
    if module:
        local = _module_path(root, test_path, module, level)
        if local:
            symbols = _python_symbols(local)
            if member in symbols:
                item = symbols[member]
                return Symbol(name, imported, item.signature.replace(item.name, name, 1),
                              item.description, str(local.relative_to(root)), item.kind, item.line)
    for path in sorted(root.rglob("*.py")):
        if {".git", ".venv", "venv", ".framework"}.intersection(path.parts):
            continue
        item = _python_symbols(path).get(name)
        if item:
            return Symbol(name, imported, item.signature, item.description,
                          str(path.relative_to(root)), item.kind, item.line)
    return None


def _python_tree(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot parse {path}: {exc}") from exc


def _python_aliases(tree: ast.AST) -> dict[str, tuple[str, int]]:
    aliases: dict[str, tuple[str, int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = (item.name, 0)
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                qualified = f"{node.module}.{item.name}" if node.module else item.name
                aliases[item.asname or item.name] = (qualified, node.level)
    return aliases


def _python_call_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        value = _flatten_attribute(node.func)
        if value:
            name = value.split(".")[-1]
            if name not in names and name not in PYTHON_BUILTINS:
                names.append(name)
    return names


def _python_explanations(root: Path, path: Path) -> list[Symbol]:
    tree = _python_tree(path)
    aliases = _python_aliases(tree)
    names = _python_call_names(tree)
    result: list[Symbol] = []
    for name in names:
        item = _resolve_python_symbol(root, path, aliases, name)
        if item is None:
            imported, level = aliases.get(name, (name, 0))
            qualified = ("." * level) + imported if level else imported
            item = Symbol(name, qualified, f"{name}(...) -> unknown",
                          f"Símbolo externo ou não resolvido ({qualified}).",
                          qualified.split(".")[0], "external")
        result.append(item)
    return result


def _js_explanations(root: Path, path: Path) -> list[Symbol]:
    text = path.read_text(encoding="utf-8", errors="replace")
    aliases: dict[str, str] = {}
    for match in re.finditer(r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)", text):
        for raw in match.group(1).split(","):
            parts = raw.strip().split(" as ")
            aliases[parts[-1].strip()] = f"{match.group(2)}.{parts[0].strip()}"
    for match in re.finditer(r"import\s+([\w$]+)\s+from\s+['\"]([^'\"]+)", text):
        aliases[match.group(1)] = match.group(2)
    declarations: dict[str, Symbol] = {}
    pattern = r"(?:async\s+)?function\s+([\w$]+)\s*\(([^)]*)\)|(?:const|let)\s+([\w$]+)\s*=\s*\(([^)]*)\)\s*=>"
    for match in re.finditer(pattern, text):
        name = match.group(1) or match.group(3)
        args = match.group(2) if match.group(1) else match.group(4)
        line = text.count("\n", 0, match.start()) + 1
        declarations[name] = Symbol(name, name, f"{name}({args}) -> unknown",
                                     "Descrição não encontrada no código-fonte.",
                                     str(path.relative_to(root)), "function", line)
    names: list[str] = []
    for match in re.finditer(r"\b([A-Za-z_$][\w$]*)\s*\(", text):
        name = match.group(1)
        if name not in names and name not in JS_KEYWORDS:
            names.append(name)
    result: list[Symbol] = []
    for name in names:
        item = declarations.get(name)
        if item:
            result.append(item)
        else:
            result.append(Symbol(name, aliases.get(name, name), f"{name}(...) -> unknown",
                                f"Símbolo externo ou não resolvido ({aliases.get(name, name)}).",
                                aliases.get(name, name), "external"))
    return result


def _explanations(root: Path, path: Path) -> list[Symbol]:
    return _python_explanations(root, path) if path.suffix == ".py" else _js_explanations(root, path)


def _comment_prefix(path: Path) -> str:
    return "#" if path.suffix == ".py" else "//"


def _block(path: Path, symbols: list[Symbol]) -> str:
    prefix = _comment_prefix(path)
    lines = [f"{prefix} {MARKER_START}", f"{prefix} FUNÇÕES UTILIZADAS NESTE TESTE", f"{prefix}"]
    for item in symbols:
        lines.extend([f"{prefix} {item.name}: {item.signature}", f"{prefix} {item.description}",
                      f"{prefix} Fonte: {item.source}", f"{prefix}"])
    lines.append(f"{prefix} {MARKER_END}")
    return "\n".join(lines) + "\n"


def _remove_block(text: str) -> str:
    pattern = rf"(?ms)^\s*(?:#|//) {re.escape(MARKER_START)}.*?(?:#|//) {re.escape(MARKER_END)}\n?"
    return re.sub(pattern, "", text, count=1)


def _insert(text: str, path: Path, block: str, mode: str, symbols: list[Symbol]) -> str:
    clean = _remove_block(text)
    if mode == "virtual":
        return clean
    if mode == "first-use" and symbols:
        name = re.escape(symbols[0].name)
        match = re.search(rf"\b{name}\b", clean)
        if match:
            line_start = clean.rfind("\n", 0, match.start()) + 1
            return clean[:line_start] + block + clean[line_start:]
    return block + clean.lstrip("\n")


def _mode(root: Path, mode: str | None) -> str:
    if mode:
        if mode not in {"header", "first-use", "virtual"}:
            raise ValueError("mode must be header, first-use or virtual")
        return mode
    try:
        config = load_config(root)
        return config.documentation.get("test_explanations", "header")
    except FileNotFoundError:
        return "header"


def explain_test(root: Path, test: str, *, mode: str | None = None) -> CommandResult:
    root = root.resolve()
    path = _safe_relative(root, test)
    selected = _mode(root, mode)
    symbols = _explanations(root, path)
    original = path.read_text(encoding="utf-8", errors="replace")
    updated = _insert(original, path, _block(path, symbols), selected, symbols)
    changed = updated != original and selected != "virtual"
    if changed:
        path.write_text(updated, encoding="utf-8")
    from ..index.symbols import update_symbol_index
    indexed = update_symbol_index(root, symbols)
    result = CommandResult("framework test explain", metadata={"path": str(path.relative_to(root)),
        "mode": selected, "symbols": [item.to_dict() for item in symbols], "changed": changed,
        "indexed_symbols": indexed})
    result.actions.append("Generated explanations are managed by framework sync")
    return result


def _candidates(root: Path, *, include_unmarked: bool = False) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SUPPORTED:
            continue
        if {".git", ".venv", "venv", ".framework"}.intersection(path.parts):
            continue
        text = path.read_text(errors="replace")
        is_test = "tests" in path.parts or path.name.startswith("test_") or ".test." in path.name
        if MARKER_START in text or (include_unmarked and is_test):
            paths.append(path)
    return sorted(paths)


def sync_explanations(root: Path, *, tests: list[str] | None = None, mode: str | None = None,
                      include_unmarked: bool = False) -> CommandResult:
    root = root.resolve()
    paths = [_safe_relative(root, item) for item in tests] if tests else _candidates(root, include_unmarked=include_unmarked)
    updated: list[str] = []
    errors: list[str] = []
    indexed_symbols: list[str] = []
    selected = _mode(root, mode)
    for path in paths:
        try:
            symbols = _explanations(root, path)
            from ..index.symbols import update_symbol_index
            indexed_symbols.extend(update_symbol_index(root, symbols))
            original = path.read_text(encoding="utf-8", errors="replace")
            value = _insert(original, path, _block(path, symbols), selected, symbols)
            if selected != "virtual" and value != original:
                path.write_text(value, encoding="utf-8")
                updated.append(str(path.relative_to(root)))
        except (OSError, ValueError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    from ..index.symbols import update_symbol_index
    indexed_symbols.extend(update_symbol_index(root))
    result = CommandResult("framework sync", metadata={"mode": selected, "updated": updated,
                                                         "scanned": len(paths),
                                                         "indexed_symbols": sorted(set(indexed_symbols))})
    for error in errors:
        result.actions.append(error)
    if errors:
        result.status, result.exit_code = "error", 2
    return result


def explanation_fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

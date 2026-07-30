from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..adapters.registry import discover_adapters
from ..security.fingerprint import fingerprint
from ..testing.explanations import SUPPORTED, Symbol, _explanations
from .db import IndexDB
from .symbol_repository import SymbolRepository


IGNORED = {".git", ".venv", "venv", ".framework", "node_modules"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}


def _source_symbols(root: Path) -> list[Symbol]:
    adapters = discover_adapters(root)
    result: list[Symbol] = []
    seen: set[tuple[str, str, str]] = set()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES or IGNORED.intersection(path.parts):
            continue
        for adapter in adapters:
            if path.suffix == ".py" and adapter.id != "python":
                continue
            if path.suffix in {".js", ".jsx", ".ts", ".tsx"} and adapter.id != "javascript":
                continue
            for data in adapter.symbols(path):
                key = (str(path), data["name"], data["kind"])
                if key in seen:
                    continue
                seen.add(key)
                metadata = {
                    key: data.get(key)
                    for key in ("logical_lines", "complexity", "description_status")
                    if data.get(key) is not None
                }
                result.append(Symbol(
                    data["name"], data.get("qualified_name", data["name"]),
                    data.get("signature", f"{data['name']}(...) -> unknown"),
                    data.get("description", "Descrição não encontrada no código-fonte."),
                    str(path.relative_to(root)), data["kind"], data.get("line"),
                    data.get("end_line"), metadata,
                ))
    return result


def _test_paths(root: Path) -> list[Path]:
    result = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SUPPORTED or IGNORED.intersection(path.parts):
            continue
        if "tests" in path.parts or path.name.startswith("test_") or ".test." in path.name:
            result.append(path)
    return result


def _merge_explanations(source: list[Symbol], explanations: Iterable[Symbol]) -> list[Symbol]:
    by_key = {(item.source, item.name, item.kind): item for item in source}
    for item in explanations:
        key = (item.source, item.name, item.kind)
        if key in by_key:
            current = by_key[key]
            metadata = {**current.metadata, "description_status": "documented"}
            by_key[key] = Symbol(current.name, item.qualified_name, item.signature,
                                 item.description, current.source, current.kind,
                                 current.line, current.end_line, metadata)
    return list(by_key.values())


def _record_payload(root: Path, symbol: Symbol, *, source: str = "source-index") -> dict:
    relative = str((root / symbol.source).relative_to(root))
    qualified = symbol.qualified_name or symbol.name
    identifier = fingerprint(relative, qualified, symbol.kind)
    content_fingerprint = fingerprint(relative, qualified, symbol.signature,
                                      symbol.description, str(symbol.end_line or symbol.line or ""))
    return {
        "id": identifier, "path": relative, "name": symbol.name, "kind": symbol.kind,
        "line": symbol.line, "end_line": symbol.end_line or symbol.line,
        "signature": symbol.signature, "description": symbol.description,
        "qualified_name": qualified, "metadata": symbol.metadata,
        "fingerprint": content_fingerprint, "source": source,
    }


def update_symbol_index(root: Path, symbols: Iterable[Symbol] | None = None) -> list[str]:
    """Rebuild the local symbol catalog and test-to-symbol relationships."""
    root = root.resolve()
    source = _source_symbols(root)
    provided = list(symbols or [])
    source = _merge_explanations(source, provided)
    records = [_record_payload(root, item) for item in source if (root / item.source).is_file()]
    relations: list[dict] = []
    for test in _test_paths(root):
        relative_test = str(test.relative_to(root))
        test_id = "test:" + fingerprint(relative_test, "test-file")
        records.append({"id": test_id, "path": relative_test, "name": relative_test,
                        "kind": "test-file", "line": 1, "end_line": None,
                        "signature": relative_test, "description": "Arquivo de testes",
                        "qualified_name": relative_test, "metadata": {},
                        "fingerprint": fingerprint(relative_test, "test-file"),
                        "source": "test-index"})
        try:
            used = _explanations(root, test)
        except (OSError, ValueError):
            used = []
        for item in used:
            target_path = root / item.source
            if not target_path.is_file():
                continue
            target_id = fingerprint(str(target_path.relative_to(root)), item.name, item.kind)
            relation = "test-uses-symbol"
            relations.append({
                "source_id": test_id, "target_id": target_id, "relation": relation,
                "fingerprint": fingerprint(test_id, target_id, relation),
                "test_path": relative_test, "symbol": item.name,
            })
    db = IndexDB(root / ".framework" / "index.db")
    repository = SymbolRepository(db)
    indexed: list[str] = []
    try:
        repository.clear()
        for record in records:
            repository.save(record)
            indexed.append(record["id"])
        for relation in relations:
            repository.relation(relation)
    finally:
        db.close()
    return indexed

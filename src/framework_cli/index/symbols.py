from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..adapters.registry import discover_adapters
from ..security.fingerprint import fingerprint
from ..testing.explanations import Symbol
from .db import IndexDB
from .repository import Repository


def _source_symbols(root: Path) -> list[Symbol]:
    adapters = discover_adapters(root)
    result: list[Symbol] = []
    seen: set[tuple[str, str, str]] = set()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or {".git", ".venv", "venv", ".framework"}.intersection(path.parts):
            continue
        for adapter in adapters:
            if not ((path.suffix == ".py" and adapter.id == "python") or
                    (path.suffix in {".js", ".jsx", ".ts", ".tsx"} and adapter.id == "javascript")):
                continue
            for data in adapter.symbols(path):
                key = (str(path), data["name"], data["kind"])
                if key in seen:
                    continue
                seen.add(key)
                result.append(Symbol(data["name"], data["name"],
                                     f"{data['name']}(...) -> unknown",
                                     "Descrição não encontrada no código-fonte.",
                                     str(path.relative_to(root)), data["kind"], data.get("line")))
    return result


def update_symbol_index(root: Path, symbols: Iterable[Symbol] | None = None) -> list[str]:
    root = root.resolve()
    symbols = list(symbols) if symbols is not None else _source_symbols(root)
    db = IndexDB(root / ".framework" / "index.db")
    repository = Repository(db)
    indexed: list[str] = []
    try:
        for symbol in symbols:
            source = root / symbol.source
            if not source.is_file():
                continue
            relative = str(source.relative_to(root))
            identifier = fingerprint(relative, symbol.name, symbol.kind)
            repository.symbol({"id": identifier, "path": relative, "name": symbol.name,
                               "kind": symbol.kind, "line": symbol.line, "end_line": symbol.line,
                               "signature": symbol.signature,
                               "description": symbol.description,
                               "fingerprint": fingerprint(relative, symbol.name, symbol.signature),
                               "source": "test-explanation"})
            indexed.append(identifier)
    finally:
        db.close()
    return indexed

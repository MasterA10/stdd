"""Associação determinística entre nós de Draw e fatos da codebase."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .draw import create_draw, read_draw


TRACEABILITY_VERSION = 1


def _unique_strings(values: Iterable[str]) -> list[str]:
    return sorted({value.strip() for value in values if isinstance(value, str) and value.strip()})


def _draw_facts_path(root: Path, draw_id: str) -> Path:
    return root / ".stdd" / "draws" / f"{draw_id}.facts.json"


def _find_node(document: dict[str, Any], node_id: int) -> dict[str, Any]:
    for node in document.get("nodes", []):
        if node.get("id") == node_id:
            return node
    raise ValueError(f"nó não encontrado: {node_id}")


def associate_node_reference(
    root: Path,
    draw_id: str,
    node_id: int,
    qualified_name: str,
    source_dependencies: list[str],
) -> Path:
    """Persiste somente o vínculo mínimo informado pelo comando de associação.
    Mantém fatos derivados fora do JSON lógico e substitui o vínculo do mesmo símbolo.
    """
    if not isinstance(node_id, int) or isinstance(node_id, bool) or node_id < 0:
        raise ValueError("node_id deve ser inteiro não negativo")
    if not isinstance(qualified_name, str) or not qualified_name.strip():
        raise ValueError("qualified_name é obrigatório")
    dependencies = _unique_strings(source_dependencies)
    if not dependencies:
        raise ValueError("source_dependencies deve conter ao menos um símbolo qualificado")

    document = read_draw(root, draw_id)
    node = _find_node(document, node_id)
    references = [reference for reference in node.get("code_refs", []) if isinstance(reference, dict)]
    references = [reference for reference in references if reference.get("symbol") != qualified_name]
    references.append({"symbol": qualified_name.strip(), "source_dependencies": dependencies})
    node["code_refs"] = references
    return create_draw(root, document)


def associate_node_references(root: Path, draw_id: str, references: list[dict[str, Any]]) -> Path:
    """Aplica várias associações unitárias no mesmo desenho em uma operação de lote.
    Reutiliza a validação unitária para manter o contrato idêntico nos dois modos.
    """
    if not isinstance(references, list) or not references:
        raise ValueError("references deve conter ao menos uma associação")
    output: Path | None = None
    for reference in references:
        if not isinstance(reference, dict):
            raise ValueError("cada associação deve ser um objeto")
        output = associate_node_reference(
            root,
            draw_id,
            reference.get("node_id"),
            reference.get("qualified_name"),
            reference.get("source_dependencies", []),
        )
    assert output is not None
    return output


def build_traceability_report(root: Path, node: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    """Calcula impacto reproduzível a partir de referências e facts estáticos.
    Não substitui referências explícitas por sugestões inferidas.
    """
    del root
    symbols = {
        item.get("qualified_name"): item
        for item in facts.get("symbols", [])
        if isinstance(item, dict) and isinstance(item.get("qualified_name"), str)
    }
    references: list[dict[str, Any]] = []
    unresolved: list[str] = []
    files: set[str] = set()
    explicit_symbols: set[str] = set()
    declared_dependencies: set[str] = set()
    for reference in node.get("code_refs", []):
        symbol_name = reference.get("symbol") if isinstance(reference, dict) else None
        if not isinstance(symbol_name, str) or not symbol_name:
            continue
        explicit_symbols.add(symbol_name)
        declared_dependencies.update(_unique_strings(reference.get("source_dependencies", [])))
        symbol = symbols.get(symbol_name)
        if symbol is None:
            references.append({"symbol": symbol_name, "status": "unresolved"})
            unresolved.append(symbol_name)
            continue
        status = "resolved" if reference.get("identity") in (None, symbol.get("identity")) else "drift"
        item = {
            "symbol": symbol_name,
            "identity": reference.get("identity", symbol.get("identity")),
            "status": status,
            "file": symbol.get("file"),
        }
        references.append(item)
        if status == "resolved" and symbol.get("file"):
            files.add(symbol["file"])
        else:
            unresolved.append(symbol_name)

    for dependency_name in sorted(declared_dependencies):
        dependency_symbol = symbols.get(dependency_name)
        if dependency_symbol is None:
            unresolved.append(dependency_name)
            continue
        if dependency_symbol.get("file"):
            files.add(dependency_symbol["file"])

    tests: set[str] = set()
    suggestions: list[dict[str, str]] = []
    for dependency in facts.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        source = dependency.get("source")
        target = dependency.get("target")
        if target in explicit_symbols | declared_dependencies and dependency.get("kind") == "test":
            if isinstance(source, str):
                tests.add(source)
            if dependency.get("file"):
                files.add(dependency["file"])
        if source in explicit_symbols and target not in explicit_symbols and isinstance(target, str):
            suggestions.append({"symbol": target, "reason": "dependency"})

    return {
        "node_id": node.get("id"),
        "references": references,
        "source_dependencies": sorted(declared_dependencies),
        "files": sorted(files),
        "tests": sorted(tests),
        "unresolved": sorted(set(unresolved)),
        "suggestions": sorted(suggestions, key=lambda item: item["symbol"]),
    }


def enrich_traceability(root: Path, draw_id: str, analysis_facts: dict[str, Any]) -> Path:
    """Recalcula facts para todos os nós associados e grava documento separado.
    A associação declarada permanece no Draw; somente o relatório derivado é substituído.
    """
    document = read_draw(root, draw_id)
    reports = {
        str(node["id"]): build_traceability_report(root, node, analysis_facts)
        for node in document.get("nodes", [])
        if node.get("code_refs")
    }
    output = _draw_facts_path(root, draw_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"version": TRACEABILITY_VERSION, "draw_id": draw_id, "nodes": reports}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def refresh_traceability(root: Path, analysis_facts: dict[str, Any]) -> list[Path]:
    """Enriquece todos os Draws que possuem referências quando facts estão disponíveis.
    Retorna somente os arquivos derivados atualizados nesta execução.
    """
    draws_root = root / ".stdd" / "draws"
    outputs: list[Path] = []
    for path in sorted(draws_root.glob("*.json")):
        if path.name == "index.json" or path.name.endswith(".facts.json") or path.name.startswith("._"):
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if any(node.get("code_refs") for node in document.get("nodes", []) if isinstance(node, dict)):
            outputs.append(enrich_traceability(root, str(document.get("id")), analysis_facts))
    return outputs

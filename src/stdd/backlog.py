"""Backlog derivado dos Draws e executor determinístico de jornadas."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .draw import draw_directory, facts_directory, read_draw, read_draw_index


BACKLOG_VERSION = 1
VALID_TASK_STATUSES = {"pending", "in_progress", "done"}


def backlog_path(root: Path) -> Path:
    """Retorna o arquivo agregado e persistente do backlog do projeto."""
    return root / ".stdd" / "backlog.json"


def _atomic_write(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def _draw_documents(root: Path) -> list[dict[str, Any]]:
    """Carrega os Draws indexados em ordem hierárquica estável."""
    index_path = draw_directory(root) / "index.json"
    if index_path.exists():
        entries = read_draw_index(root).get("draws", [])
        draw_ids = [entry.get("id") for entry in entries if isinstance(entry, dict) and isinstance(entry.get("id"), str)]
    else:
        draw_ids = [path.stem for path in sorted(draw_directory(root).glob("*.json")) if path.name != "index.json"]
    documents = []
    for draw_id in draw_ids:
        try:
            document = read_draw(root, draw_id)
        except ValueError:
            continue
        hierarchy = document.get("hierarchy") if isinstance(document.get("hierarchy"), dict) else {}
        documents.append(document | {"_hierarchy": hierarchy})
    return sorted(
        documents,
        key=lambda document: (
            int(document["_hierarchy"].get("level", 99)),
            str(document["_hierarchy"].get("parent_draw_ref") or ""),
            str(document.get("id", "")),
        ),
    )


def _reference_symbols(node: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    """Extrai símbolos, dependências e referências sem inventar fatos."""
    symbols: set[str] = set()
    dependencies: set[str] = set()
    references: list[dict[str, Any]] = []
    for reference in node.get("code_refs", []):
        if isinstance(reference, str):
            reference = {"symbol": reference}
        if not isinstance(reference, dict):
            continue
        symbol = reference.get("symbol") or reference.get("qualified_name")
        if isinstance(symbol, str) and symbol.strip():
            symbols.add(symbol.strip())
        source_dependencies = reference.get("source_dependencies", [])
        if isinstance(source_dependencies, list):
            dependencies.update(item.strip() for item in source_dependencies if isinstance(item, str) and item.strip())
        references.append(deepcopy(reference))
    return sorted(symbols), sorted(dependencies), references


def _traceability(root: Path, draw_id: str, node_id: Any, symbols: list[str]) -> list[dict[str, Any]]:
    """Acrescenta o status factual dos símbolos já analisados."""
    facts_path = facts_directory(root) / f"{draw_id}.facts.json"
    if not facts_path.exists():
        return [{"symbol": symbol, "status": "not-analyzed"} for symbol in symbols]
    try:
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [{"symbol": symbol, "status": "not-analyzed"} for symbol in symbols]
    node_facts = facts.get("nodes", {}).get(str(node_id), {}) if isinstance(facts, dict) else {}
    fact_references = node_facts.get("references", []) if isinstance(node_facts, dict) else []
    by_symbol = {
        item.get("symbol"): item
        for item in fact_references
        if isinstance(item, dict) and isinstance(item.get("symbol"), str)
    }
    return [
        {"symbol": symbol, **{key: value for key, value in by_symbol.get(symbol, {}).items() if key != "symbol"}}
        if symbol in by_symbol
        else {"symbol": symbol, "status": "not-analyzed"}
        for symbol in symbols
    ]


def _child_checklist_id(node: dict[str, Any], checklist_ids: set[str]) -> str | None:
    """Retorna somente uma referência de subfluxo que exista no backlog."""
    child_id = node.get("draw_ref")
    return child_id if isinstance(child_id, str) and child_id in checklist_ids else None


def _checklist_item(root: Path, document: dict[str, Any], node: dict[str, Any], checklist_ids: set[str]) -> dict[str, Any]:
    """Monta o item informativo de qualquer nó, em qualquer nível."""
    symbols, dependencies, code_refs = _reference_symbols(node)
    return {
        "id": f"item:{document['id']}:node:{node['id']}",
        "node_id": node["id"],
        "label": node.get("label", ""),
        "description": node.get("description", ""),
        "status": "pending",
        "questions": deepcopy(node.get("questions", [])) if isinstance(node.get("questions", []), list) else [],
        "code_refs": code_refs,
        "symbols": symbols,
        "source_dependencies": dependencies,
        "traceability": _traceability(root, str(document["id"]), node["id"], symbols),
        "child_checklist_id": _child_checklist_id(node, checklist_ids),
    }


def _has_self_loop(document: dict[str, Any], node_id: Any) -> bool:
    return any(
        isinstance(edge, dict) and edge.get("from") == node_id and edge.get("to") == node_id
        for edge in document.get("edges", [])
    )


def _graph_branches(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumera caminhos simples e encerra self-loops sem recursão infinita."""
    nodes = [node.get("id") for node in document.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in document.get("edges", []) if isinstance(edge, dict)]
    outgoing: dict[Any, list[dict[str, Any]]] = {node_id: [] for node_id in nodes}
    incoming: dict[Any, int] = {node_id: 0 for node_id in nodes}
    for edge in edges:
        if edge.get("from") not in outgoing or edge.get("to") not in outgoing:
            continue
        outgoing[edge["from"]].append(edge)
        if edge["from"] != edge["to"]:
            incoming[edge["to"]] += 1
    for edge_list in outgoing.values():
        edge_list.sort(key=lambda edge: (int(edge.get("id", 0)), str(edge.get("label", ""))))
    roots = sorted((node_id for node_id, count in incoming.items() if count == 0), key=str) or sorted(nodes, key=str)
    branches: list[dict[str, Any]] = []

    def walk(path: list[Any], branch_edges: list[dict[str, Any]], branch_number: list[int], visited: set[Any]) -> None:
        current = path[-1]
        continuations = outgoing.get(current, [])
        if not continuations:
            branches.append({"id": branch_number[0], "node_ids": path, "edges": branch_edges, "terminal_node_id": current, "terminal_reason": "no-outgoing"})
            branch_number[0] += 1
            return
        for edge in continuations:
            target = edge.get("to")
            next_edges = branch_edges + [edge]
            if target == current:
                branches.append({"id": branch_number[0], "node_ids": path, "edges": next_edges, "terminal_node_id": current, "terminal_reason": "self-loop"})
                branch_number[0] += 1
            elif target in visited:
                branches.append({"id": branch_number[0], "node_ids": path + [target], "edges": next_edges, "terminal_node_id": target, "terminal_reason": "cycle"})
                branch_number[0] += 1
            else:
                walk(path + [target], next_edges, branch_number, visited | {target})

    for root_node in roots:
        walk([root_node], [], [len(branches) + 1], {root_node})
    return branches


def _branches_for_draw(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Prefere caminhos explícitos e garante uma branch para cada nó."""
    flows = [flow for flow in document.get("flows", []) if isinstance(flow, dict) and flow.get("steps")]
    if not flows:
        return _graph_branches(document)
    branches = []
    for index, flow in enumerate(flows, start=1):
        node_ids = [step.get("node") for step in flow.get("steps", []) if isinstance(step, dict)]
        if not node_ids:
            continue
        terminal = node_ids[-1]
        reason = "self-loop" if _has_self_loop(document, terminal) else "flow-end"
        branches.append({"id": index, "node_ids": node_ids, "edges": [], "terminal_node_id": terminal, "terminal_reason": reason, "flow_id": flow.get("id")})
    covered_node_ids = {
        node_id
        for branch in branches
        for node_id in branch.get("node_ids", [])
    }
    next_branch_id = max((int(branch["id"]) for branch in branches), default=0) + 1
    for node in document.get("nodes", []):
        if not isinstance(node, dict) or node.get("id") in covered_node_ids:
            continue
        node_id = node.get("id")
        branches.append({
            "id": next_branch_id,
            "node_ids": [node_id],
            "edges": [],
            "terminal_node_id": node_id,
            "terminal_reason": "node-not-listed-in-flow",
            "flow_id": None,
        })
        next_branch_id += 1
    return branches


def _existing_state(root: Path) -> dict[str, Any]:
    path = backlog_path(root)
    if not path.exists():
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return document if isinstance(document, dict) else {}


def _branch_occurrence(draw_id: str, branch: dict[str, Any], position: int, node_id: Any) -> dict[str, Any]:
    """Descreve uma ocorrência de nó dentro de uma branch específica."""
    return {
        "id": f"{draw_id}:branch:{branch['id']}",
        "position": position,
        "terminal": node_id == branch.get("terminal_node_id"),
        "terminal_node_id": branch.get("terminal_node_id"),
        "terminal_reason": branch.get("terminal_reason"),
    }


def _task_for_node(root: Path, document: dict[str, Any], node: dict[str, Any], branch: dict[str, Any], position: int, checklist_ids: set[str], parent_task_id: str | None = None) -> dict[str, Any]:
    draw_id = str(document["id"])
    node_id = node["id"]
    symbols, dependencies, code_refs = _reference_symbols(node)
    item_id = f"task:{draw_id}:node:{node_id}"
    occurrence = _branch_occurrence(draw_id, branch, position, node_id)
    return {
        "id": item_id,
        "draw_id": draw_id,
        "backlog_id": draw_id,
        "parent_task_id": parent_task_id,
        "draw_title": document.get("title", draw_id),
        "node_id": node_id,
        "level": document.get("_hierarchy", {}).get("level"),
        "label": node.get("label", ""),
        "description": node.get("description", ""),
        "questions": deepcopy(node.get("questions", [])) if isinstance(node.get("questions", []), list) else [],
        "code_refs": code_refs,
        "symbols": symbols,
        "source_dependencies": dependencies,
        "traceability": _traceability(root, draw_id, node_id, symbols),
        "child_checklist_id": next((ref for ref in node.get("draw_ref", []) if ref in checklist_ids), node.get("draw_ref")) if isinstance(node.get("draw_ref"), list) else node.get("draw_ref"),
        "status": "pending",
        "branch": occurrence,
        "branches": [occurrence],
    }


def _refresh_branch_completion(payload: dict[str, Any]) -> None:
    """Recalcula todas as branches a partir do status das suas tasks."""
    tasks_by_id = {
        task.get("id"): task
        for task in payload.get("tasks", [])
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    completed_branches = []
    execution = payload.get("execution", {})
    for branch in execution.get("branches", []):
        task_ids = branch.get("task_ids", [])
        branch["completed"] = bool(task_ids) and all(
            tasks_by_id.get(task_id, {}).get("status") == "done"
            for task_id in task_ids
        )
        if branch["completed"]:
            completed_branches.append(branch["id"])
    execution["completed_branches"] = completed_branches


def _append_child_backlog(root: Path, parent_task: dict[str, Any], parent_node: dict[str, Any], context: dict[str, Any]) -> None:
    """Expande recursivamente o backlog associado ao nó pai."""
    child_id = parent_node.get("draw_ref")
    documents_by_id = context["documents_by_id"]
    child_document = documents_by_id.get(str(child_id)) if isinstance(child_id, str) else None
    expanded = context["expanded_child_backlogs"]
    if child_document is None or str(child_id) in expanded:
        return
    hierarchy = child_document.get("_hierarchy", {})
    if hierarchy.get("parent_draw_ref") != parent_task.get("draw_id") or hierarchy.get("parent_node_id") != parent_task.get("node_id"):
        return
    expanded.add(str(child_id))
    child_nodes = {node.get("id"): node for node in child_document.get("nodes", []) if isinstance(node, dict)}
    child_task_ids: list[str] = []
    child_branch_ids: list[str] = []
    for child_branch in _branches_for_draw(child_document):
        branch_task_ids: list[str] = []
        branch_node_ids: list[Any] = []
        for position, node_id in enumerate(child_branch["node_ids"], start=1):
            child_node = child_nodes.get(node_id)
            if child_node is None:
                continue
            task_id = f"task:{child_id}:node:{node_id}"
            tasks_by_id = context["tasks_by_id"]
            child_task = tasks_by_id.get(task_id)
            if child_task is None:
                child_task = _task_for_node(root, child_document, child_node, child_branch, position, context["checklist_ids"], parent_task["id"])
                previous_task = context["previous_tasks"].get(task_id)
                if previous_task and previous_task.get("status") in VALID_TASK_STATUSES:
                    child_task["status"] = previous_task["status"]
                context["tasks"].append(child_task)
                tasks_by_id[task_id] = child_task
                _append_child_backlog(root, child_task, child_node, context)
            else:
                occurrence = _branch_occurrence(str(child_id), child_branch, position, node_id)
                if not any(item.get("id") == occurrence["id"] for item in child_task.get("branches", [])):
                    child_task.setdefault("branches", []).append(occurrence)
            branch_node_ids.append(node_id)
            branch_task_ids.append(task_id)
            descendants = child_task.get("child_task_ids", [])
            for descendant_id in descendants:
                if descendant_id not in branch_task_ids:
                    branch_task_ids.append(descendant_id)
            for nested_task_id in [task_id, *descendants]:
                if nested_task_id not in child_task_ids:
                    child_task_ids.append(nested_task_id)
        branch_id = f"{child_id}:branch:{child_branch['id']}"
        child_branch_ids.append(branch_id)
        context["execution_branches"].append({
            "id": branch_id,
            "draw_id": str(child_id),
            "backlog_id": str(child_id),
            "parent_task_id": parent_task["id"],
            "flow_id": child_branch.get("flow_id"),
            "task_ids": branch_task_ids,
            "node_ids": branch_node_ids,
            "edges": deepcopy(child_branch.get("edges", [])),
            "terminal_node_id": child_branch.get("terminal_node_id"),
            "terminal_reason": child_branch.get("terminal_reason"),
            "scope": "nested",
            "completed": False,
        })
    parent_task["child_backlog_id"] = str(child_id)
    parent_task["child_task_ids"] = child_task_ids
    parent_task["child_branch_ids"] = child_branch_ids


def _build_checklist(root: Path, document: dict[str, Any], checklist_ids: set[str], context: dict[str, Any]) -> dict[str, Any]:
    """Constrói o checklist e as branches operacionais de um Draw."""
    draw_id = str(document["id"])
    hierarchy = deepcopy(document.get("_hierarchy", {}))
    nodes_by_id = {node.get("id"): node for node in document.get("nodes", []) if isinstance(node, dict)}
    items = [_checklist_item(root, document, node, checklist_ids) for node in nodes_by_id.values()]
    items_by_node = {item["node_id"]: item for item in items}
    if hierarchy.get("level") != 2:
        return {
            "id": draw_id,
            "draw_id": draw_id,
            "title": document.get("title", draw_id),
            "hierarchy": hierarchy,
            "parent_checklist_id": hierarchy.get("parent_draw_ref"),
            "parent_node_id": hierarchy.get("parent_node_id"),
            "items": items,
        }
    for branch in _branches_for_draw(document):
        branch_task_ids = []
        branch_node_ids = []
        for position, node_id in enumerate(branch["node_ids"], start=1):
            if node_id not in nodes_by_id:
                continue
            task_id = f"task:{draw_id}:node:{node_id}"
            branch_task_ids.append(task_id)
            branch_node_ids.append(node_id)
            task = context["tasks_by_id"].get(task_id)
            if task is None:
                task = _task_for_node(root, document, nodes_by_id[node_id], branch, position, checklist_ids)
                previous_task = context["previous_tasks"].get(task_id)
                if previous_task and previous_task.get("status") in VALID_TASK_STATUSES:
                    task["status"] = previous_task["status"]
                context["tasks"].append(task)
                context["tasks_by_id"][task_id] = task
                items_by_node[node_id].update({"task_id": task_id, "status": task["status"], "task": task})
            else:
                occurrence = _branch_occurrence(draw_id, branch, position, node_id)
                if not any(item.get("id") == occurrence["id"] for item in task.get("branches", [])):
                    task.setdefault("branches", []).append(occurrence)
            _append_child_backlog(root, task, nodes_by_id[node_id], context)
            for child_task_id in task.get("child_task_ids", []):
                if child_task_id not in branch_task_ids:
                    branch_task_ids.append(child_task_id)
        context["execution_branches"].append({
            "id": f"{draw_id}:branch:{branch['id']}",
            "draw_id": draw_id,
            "backlog_id": draw_id,
            "flow_id": branch.get("flow_id"),
            "task_ids": branch_task_ids,
            "node_ids": branch_node_ids,
            "edges": deepcopy(branch.get("edges", [])),
            "terminal_node_id": branch.get("terminal_node_id"),
            "terminal_reason": branch.get("terminal_reason"),
            "scope": "root",
            "completed": False,
        })
    return {
        "id": draw_id,
        "draw_id": draw_id,
        "title": document.get("title", draw_id),
        "hierarchy": hierarchy,
        "parent_checklist_id": hierarchy.get("parent_draw_ref"),
        "parent_node_id": hierarchy.get("parent_node_id"),
        "items": items,
    }


def build_backlog(root: Path, generated_at: str | None = None) -> dict[str, Any]:
    """Constrói o backlog único, preservando progresso e cursor anteriores."""
    documents = _draw_documents(root)
    previous = _existing_state(root)
    previous_tasks = {item.get("id"): item for item in previous.get("tasks", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    checklist_ids = {str(document["id"]) for document in documents}
    documents_by_id = {str(document["id"]): document for document in documents}
    checklists = []
    tasks = []
    tasks_by_id: dict[str, dict[str, Any]] = {}
    execution_branches = []
    context = {
        "documents_by_id": documents_by_id,
        "expanded_child_backlogs": set(),
        "tasks_by_id": tasks_by_id,
        "tasks": tasks,
        "previous_tasks": previous_tasks,
        "checklist_ids": checklist_ids,
        "execution_branches": execution_branches,
    }

    checklists = [_build_checklist(root, document, checklist_ids, context) for document in documents]
    previous_execution = previous.get("execution", {}) if isinstance(previous.get("execution", {}), dict) else {}
    valid_task_ids = {task["id"] for task in tasks}
    current_task_id = previous_execution.get("current_task_id") if previous_execution.get("current_task_id") in valid_task_ids else None
    if current_task_id and next((task for task in tasks if task["id"] == current_task_id), {}).get("status") == "done":
        current_task_id = None
    current_task = next((task for task in tasks if task["id"] == current_task_id), None)
    for checklist in checklists:
        for item in checklist.get("items", []):
            task_id = f"task:{checklist['draw_id']}:node:{item['node_id']}"
            task = tasks_by_id.get(task_id)
            if task is not None:
                item.update({"task_id": task_id, "status": task["status"], "task": task})
    backlogs = []
    for document in documents:
        draw_id = str(document["id"])
        draw_tasks = [task for task in tasks if task.get("backlog_id") == draw_id]
        if not draw_tasks:
            continue
        backlogs.append({
            "id": f"backlog:{draw_id}",
            "draw_id": draw_id,
            "title": document.get("title", draw_id),
            "parent_task_id": next((task.get("parent_task_id") for task in draw_tasks if task.get("parent_task_id")), None),
            "task_ids": [task["id"] for task in draw_tasks],
        })
    payload = {
        "version": BACKLOG_VERSION,
        "kind": "backlog",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "system": {"root_draw_ids": [str(document["id"]) for document in documents if document.get("_hierarchy", {}).get("level") == 1]},
        "checklists": checklists,
        "backlogs": backlogs,
        "tasks": tasks,
        "execution": {
            "current_task_id": current_task_id,
            "current_backlog_id": current_task.get("backlog_id") if current_task else None,
            "current_branch_id": previous_execution.get("current_branch_id"),
            "branch_position": previous_execution.get("branch_position"),
            "completed_branches": [],
            "branches": execution_branches,
        },
    }
    _refresh_branch_completion(payload)
    return payload


def validate_backlog(payload: Any) -> list[str]:
    """Valida o contrato mínimo antes de persistir um backlog."""
    if not isinstance(payload, dict):
        return ["backlog deve ser um objeto"]
    violations = []
    if payload.get("version") != BACKLOG_VERSION:
        violations.append("version de backlog inválida")
    if payload.get("kind") != "backlog":
        violations.append("kind de backlog inválido")
    if not isinstance(payload.get("tasks"), list):
        violations.append("tasks deve ser uma lista")
    else:
        for index, task in enumerate(payload["tasks"]):
            if not isinstance(task, dict) or not isinstance(task.get("id"), str):
                violations.append(f"tasks[{index}] precisa de id")
            elif task.get("status") not in VALID_TASK_STATUSES:
                violations.append(f"tasks[{index}].status inválido")
    if not isinstance(payload.get("execution"), dict):
        violations.append("execution deve ser um objeto")
    return violations


def write_backlog(root: Path, payload: dict[str, Any]) -> Path:
    """Valida e grava o backlog agregado de forma atômica."""
    violations = validate_backlog(payload)
    if violations:
        raise ValueError("Backlog inválido: " + "; ".join(violations))
    return _atomic_write(backlog_path(root), payload)


def read_backlog(root: Path) -> dict[str, Any]:
    """Lê o backlog persistido e rejeita documentos incompatíveis."""
    path = backlog_path(root)
    if not path.exists():
        raise ValueError("backlog ainda não foi gerado")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("backlog inválido") from error
    violations = validate_backlog(payload)
    if violations:
        raise ValueError("Backlog inválido: " + "; ".join(violations))
    return payload


def check_backlog(root: Path) -> dict[str, Any]:
    """Verifica se o backlog persistido não deixou implementação sem check.
    Ausência de backlog não bloqueia projetos que ainda não adotaram o fluxo.
    """
    path = backlog_path(root)
    if not path.exists():
        return {
            "name": "backlog",
            "status": "not_executed",
            "reason": "backlog_not_generated",
            "total": 0,
            "done": 0,
            "remaining": 0,
            "current_task_id": None,
        }
    try:
        payload = read_backlog(root)
    except ValueError as error:
        return {
            "name": "backlog",
            "status": "blocked",
            "reason": "backlog_invalid",
            "total": 0,
            "done": 0,
            "remaining": 0,
            "current_task_id": None,
            "errors": [str(error)],
        }
    tasks = [task for task in payload.get("tasks", []) if isinstance(task, dict)]
    remaining = [task for task in tasks if task.get("status") != "done"]
    execution = payload.get("execution", {}) if isinstance(payload.get("execution"), dict) else {}
    return {
        "name": "backlog",
        "status": "blocked" if remaining else "passed",
        "reason": "tasks_pending" if remaining else "all_tasks_complete",
        "total": len(tasks),
        "done": len(tasks) - len(remaining),
        "remaining": len(remaining),
        "remaining_task_ids": [task.get("id") for task in remaining[:10]],
        "current_task_id": execution.get("current_task_id"),
    }


def generate_backlog(root: Path) -> dict[str, Any]:
    """Reconstrói a estrutura sem perder os status já persistidos."""
    payload = build_backlog(root)
    write_backlog(root, payload)
    return payload


def missing_backlog(root: Path) -> dict[str, Any]:
    """Retorna somente tasks que ainda não estão concluídas."""
    payload = generate_backlog(root)
    items = [deepcopy(task) for task in payload["tasks"] if task.get("status") != "done"]
    done = len(payload["tasks"]) - len(items)
    return {
        "kind": "missing-backlog",
        "version": BACKLOG_VERSION,
        "summary": {"total": len(payload["tasks"]), "missing": len(items), "done": done},
        "items": items,
    }


def next_backlog_task(root: Path) -> dict[str, Any]:
    """Entrega e persiste a próxima task da ordem de branches."""
    payload = generate_backlog(root)
    execution = payload["execution"]
    current_id = execution.get("current_task_id")
    if current_id:
        current = next((task for task in payload["tasks"] if task["id"] == current_id), None)
        if current and current.get("status") == "in_progress":
            return {"kind": "backlog-task", "task": current}
    task = next((item for item in payload["tasks"] if item.get("status") != "done"), None)
    if task is None:
        execution["current_task_id"] = None
        execution["current_backlog_id"] = None
        write_backlog(root, payload)
        return {"kind": "backlog-empty", "status": "complete", "remaining": 0}
    task["status"] = "in_progress"
    execution["current_task_id"] = task["id"]
    execution["current_backlog_id"] = task.get("backlog_id")
    execution["current_branch_id"] = task["branch"]["id"]
    execution["branch_position"] = task["branch"]["position"]
    for checklist in payload["checklists"]:
        for item in checklist.get("items", []):
            if item.get("id") == task["id"]:
                item["status"] = "in_progress"
    write_backlog(root, payload)
    return {"kind": "backlog-task", "task": task}


def complete_backlog_task(root: Path, task_id: str) -> dict[str, Any]:
    """Conclui somente a task atualmente reservada para o agente."""
    payload = read_backlog(root)
    execution = payload["execution"]
    if execution.get("current_task_id") != task_id:
        raise ValueError("task-id não corresponde à task atual")
    task = next((item for item in payload["tasks"] if item["id"] == task_id), None)
    if task is None or task.get("status") != "in_progress":
        raise ValueError("task atual não está em andamento")
    task["status"] = "done"
    for checklist in payload["checklists"]:
        for item in checklist.get("items", []):
            if item.get("id") == task_id:
                item["status"] = "done"
    execution["current_task_id"] = None
    execution["current_backlog_id"] = None
    _refresh_branch_completion(payload)
    write_backlog(root, payload)
    return {"kind": "backlog-complete", "status": "done", "task": task, "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")}

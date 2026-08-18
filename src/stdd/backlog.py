"""Backlog derivado dos Draws e executor determinístico de jornadas."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .draw import EDGE_CONDITIONS, draw_directory, facts_directory, read_draw, read_draw_index


BACKLOG_VERSION = 1
VALID_TASK_STATUSES = {"pending", "in_progress", "done"}
VALID_TEST_STATUSES = {"missing", "in_progress", "done"}
VALID_EXECUTION_PHASES = {None, "bootstrap", "test", "implementation"}
VALID_CHECKLIST_PHASES = {"test", "implementation"}
DEFAULT_MIN_TASK_INTERVAL_SECONDS = 0
DEFAULT_TASK_BATCH_SIZE = 1
VALID_TASK_BATCH_SCOPES = {"task", "node"}
VALID_TASK_DELIVERY_SCOPES = {"task", "node"}
DEFAULT_LEVEL_MEANINGS = {
    "2": "Tela",
    "3": "Regra de negócio e detalhes da tela",
}


def _level_guidance(level: str, meaning: str) -> str:
    """Converte a definição escolhida no init em uma orientação acionável."""
    normalized = meaning.casefold().strip()
    if level == "2" and normalized == "tela":
        return "Trate esta task como implementação da view/tela: entregue a apresentação e o comportamento frontend necessário."
    if level == "3" and normalized in {"regra de negócio", "regra de negocio"}:
        return "Trate este fluxo como regra de negócio: implemente decisões, validações, persistência e efeitos exigidos pelo comportamento."
    if level == "3" and normalized == "detalhes da tela":
        return "Trate este fluxo como detalhes da tela: implemente estados, interações, validações e comportamentos específicos da view."
    if level == "3" and normalized in {
        "regra de negócio e detalhes da tela",
        "regra de negocio e detalhes da tela",
    }:
        return "Trate este fluxo como regra de negócio e detalhes da tela: implemente decisões, validações, estados, interações e efeitos necessários."
    return f"Use esta definição como orientação de escopo para o nível {level}: {meaning}."


def _level_semantics(root: Path) -> dict[str, dict[str, Any]]:
    """Retorna as definições L2/L3 persistidas e suas orientações para o agente."""
    config = _get_backlog_config(root)
    semantics: dict[str, dict[str, Any]] = {}
    for level, default in DEFAULT_LEVEL_MEANINGS.items():
        configured = config.get(f"level_{level}_meaning", default)
        meaning = configured.strip() if isinstance(configured, str) and configured.strip() else default
        semantics[level] = {
            "level": int(level),
            "meaning": meaning,
            "guidance": _level_guidance(level, meaning),
        }
    return semantics


def _get_backlog_config(root: Path) -> dict[str, Any]:
    """Lê a configuração da chave 'backlog' em .stdd/config.json."""
    config_path = root / ".stdd" / "config.json"
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            backlog_cfg = data.get("backlog")
            if isinstance(backlog_cfg, dict):
                return backlog_cfg
    except Exception:
        pass
    return {}


def _bootstrap_enabled(config: dict[str, Any]) -> bool:
    """Habilita bootstrap salvo quando houver opt-out explícito.
    Trata o antigo default ``bootstrap_task: false`` como configuração legada.
    """
    return config.get("bootstrap_opt_out") is not True


def _execution_config(root: Path) -> dict[str, Any]:
    """Normaliza as opções de cursor sem quebrar configurações antigas."""
    config = _get_backlog_config(root)
    size = config.get("task_batch_size", DEFAULT_TASK_BATCH_SIZE)
    try:
        size = max(1, min(5, int(size)))
    except (TypeError, ValueError):
        size = DEFAULT_TASK_BATCH_SIZE
    scope = config.get("task_batch_scope", "task")
    if scope not in VALID_TASK_BATCH_SCOPES:
        scope = "task"
    delivery_scope = config.get("task_delivery_scope", config.get("test_task_scope", "task"))
    if delivery_scope not in VALID_TASK_DELIVERY_SCOPES:
        delivery_scope = "task"
    interval = config.get("min_task_interval_seconds", config.get("task_min_interval_seconds", config.get("minimum_task_interval_seconds", DEFAULT_MIN_TASK_INTERVAL_SECONDS)))
    try:
        interval = max(0, int(interval))
    except (TypeError, ValueError):
        interval = DEFAULT_MIN_TASK_INTERVAL_SECONDS
    return {
        "task_batch_size": size,
        "task_batch_scope": scope,
        "task_delivery_scope": delivery_scope,
        "min_task_interval_seconds": interval,
        "lease_seconds": max(3, int(config.get("lease_seconds", 900) or 900)),
    }


def get_backlog_config(root: Path) -> dict[str, Any]:
    """Retorna a configuração da seção 'backlog' em .stdd/config.json."""
    return _get_backlog_config(root)


def set_backlog_config(
    root: Path,
    verification_interval: int | None = None,
    bootstrap_task: bool | None = None,
    final_verification_task: bool | None = None,
    task_batch_size: int | None = None,
    task_batch_scope: str | None = None,
    task_delivery_scope: str | None = None,
    min_task_interval_seconds: int | None = None,
    level_2_meaning: str | None = None,
    level_3_meaning: str | None = None,
) -> dict[str, Any]:
    """Atualiza a seção 'backlog' em .stdd/config.json de forma persistente."""
    config_path = root / ".stdd" / "config.json"
    data: dict[str, Any] = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
    backlog_cfg = data.setdefault("backlog", {})
    if not isinstance(backlog_cfg, dict):
        backlog_cfg = {}
        data["backlog"] = backlog_cfg
    if verification_interval is not None:
        backlog_cfg["l2_verification_interval"] = int(verification_interval)
    if bootstrap_task is not None:
        backlog_cfg["bootstrap_task"] = bool(bootstrap_task)
        backlog_cfg["bootstrap_opt_out"] = not bool(bootstrap_task)
    if final_verification_task is not None:
        backlog_cfg["final_verification_task"] = bool(final_verification_task)
    if task_batch_size is not None:
        if not 1 <= int(task_batch_size) <= 5:
            raise ValueError("task_batch_size deve estar entre 1 e 5")
        backlog_cfg["task_batch_size"] = int(task_batch_size)
    if task_batch_scope is not None:
        if task_batch_scope not in VALID_TASK_BATCH_SCOPES:
            raise ValueError("task_batch_scope deve ser task ou node")
        backlog_cfg["task_batch_scope"] = task_batch_scope
    if task_delivery_scope is not None:
        if task_delivery_scope not in VALID_TASK_DELIVERY_SCOPES:
            raise ValueError("task_delivery_scope deve ser task ou node")
        backlog_cfg["task_delivery_scope"] = task_delivery_scope
        backlog_cfg.pop("test_task_scope", None)
    if min_task_interval_seconds is not None:
        if int(min_task_interval_seconds) < 0:
            raise ValueError("min_task_interval_seconds não pode ser negativo")
        backlog_cfg["min_task_interval_seconds"] = int(min_task_interval_seconds)
    for level, meaning in ((2, level_2_meaning), (3, level_3_meaning)):
        if meaning is not None:
            normalized = str(meaning).strip()
            if not normalized:
                raise ValueError(f"level_{level}_meaning não pode ser vazio")
            backlog_cfg[f"level_{level}_meaning"] = normalized
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return backlog_cfg


def _bootstrap_instruction() -> str:
    """Retorna a orientação curta e agnóstica da preparação inicial."""
    return (
        "Prepare o local antes das tasks de produto: leia a estrutura existente e deixe pronto o ponto de entrada, "
        "arquivos raiz, configuração, dependências, convenções e comandos necessários para associar e executar as próximas tasks. "
        "Use as evidências do projeto e da stack; não invente framework nem implemente funcionalidade de produto."
    )


def _create_injected_bootstrap_task() -> dict[str, Any]:
    """Cria a primeira task operacional sem assumir uma stack específica."""
    return {
        "id": "task:bootstrap",
        "draw_id": "system",
        "backlog_id": "system",
        "label": "Preparar a Estrutura Inicial",
        "description": _bootstrap_instruction(),
        "level": 1,
        "status": "in_progress",
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "bootstrap inicial"},
        "checklist_state": {"test": True, "implementation": False},
        "branch": {"id": "system:bootstrap", "position": 1},
        "branches": [{"id": "system:bootstrap", "position": 1}],
    }


def bootstrap_report(root: Path) -> dict[str, Any]:
    """Audita os pré-requisitos mínimos antes da primeira task do backlog."""
    documents = _draw_documents(root)
    root_draw = next(
        (document for document in documents if document.get("_hierarchy", {}).get("level") == 1 and document.get("kind") == "system"),
        None,
    )
    from .setup import bootstrap_design_status

    checks = {
        "system_level_1": {"status": "passed" if root_draw else "blocked", "reason": None if root_draw else "system_level_1_missing"},
        "design": bootstrap_design_status(root),
        "env_example": {"status": "passed" if (root / ".env.example").is_file() else "blocked", "reason": None if (root / ".env.example").is_file() else "env_example_missing"},
        "stdd_config": {"status": "passed" if (root / ".stdd" / "config.json").is_file() else "blocked", "reason": None if (root / ".stdd" / "config.json").is_file() else "config_missing"},
        "draw_storage": {"status": "passed" if (root / ".stdd" / "draws" / "index.json").is_file() else "blocked", "reason": None if (root / ".stdd" / "draws" / "index.json").is_file() else "draw_storage_missing"},
    }
    failures = [name for name, check in checks.items() if check.get("status") != "passed"]
    return {"status": "blocked" if failures else "passed", "checks": checks, "failures": failures}


def _create_injected_l2_batch_verify_task(target_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Cria a task de verificação funcional em lote para 1 ou mais nós L2 finalizados."""
    if not target_nodes:
        raise ValueError("lista de nós vazia para verificação")
    if len(target_nodes) == 1:
        n = target_nodes[0]
        task_id = f"task:verify:{n.get('draw_id')}:node:{n.get('node_id')}"
        label = f"Verificação da Implementação — {n.get('label', '')}"
        desc = f"Auditar e validar o código implementado para o nó '{n.get('label', '')}' e seus subfluxos em relação à especificação do Draw. Não altere o fluxo ou o desenho: confira se a implementação de produção cumpre fielmente as regras de negócio, persistência real, validações de entrada e endpoints."
    else:
        labels = [n.get("label", f"Nó {n.get('node_id')}") for n in target_nodes]
        node_ids_str = ":".join(str(n.get("node_id")) for n in target_nodes)
        draw_id = target_nodes[0].get("draw_id", "system")
        task_id = f"task:verify:{draw_id}:batch:{node_ids_str}"
        label = f"Verificação da Implementação em Lote — ({len(target_nodes)} nós: {', '.join(labels)})"
        desc = f"Auditar e validar o código implementado para os nós ({', '.join(labels)}) e seus respectivos subfluxos internos em relação à especificação do Draw. Não altere o fluxo ou o desenho: confira se a implementação de produção cumpre fielmente as regras de negócio, persistência real, validações de entrada e endpoints."

    all_symbols: set[str] = set()
    all_deps: set[str] = set()
    all_code_refs: list[dict[str, Any]] = []
    all_questions: list[dict[str, Any]] = []
    all_child_task_ids: list[str] = []
    verified_nodes: list[dict[str, Any]] = []

    for n in target_nodes:
        for s in n.get("symbols", []):
            all_symbols.add(s)
        for d in n.get("source_dependencies", []):
            all_deps.add(d)
        all_code_refs.extend(deepcopy(n.get("code_refs", [])))
        all_questions.extend(deepcopy(n.get("questions", [])))
        all_child_task_ids.extend(n.get("child_task_ids", []))
        verified_nodes.append({
            "task_id": n["id"],
            "draw_id": n.get("draw_id"),
            "node_id": n.get("node_id"),
            "label": n.get("label", ""),
            "description": n.get("description", ""),
            "symbols": list(n.get("symbols", [])),
            "source_dependencies": list(n.get("source_dependencies", [])),
            "code_refs": deepcopy(n.get("code_refs", [])),
            "questions": deepcopy(n.get("questions", [])),
            "child_task_ids": list(n.get("child_task_ids", [])),
        })

    first = target_nodes[0]
    return {
        "id": task_id,
        "draw_id": first.get("draw_id"),
        "backlog_id": first.get("backlog_id"),
        "parent_task_id": first.get("id"),
        "node_id": first.get("node_id"),
        "label": label,
        "description": desc,
        "level": 2,
        "status": "in_progress",
        "verified_nodes": verified_nodes,
        "verified_task_ids": [n["id"] for n in target_nodes],
        "questions": all_questions,
        "code_refs": all_code_refs,
        "symbols": sorted(all_symbols),
        "source_dependencies": sorted(all_deps),
        "child_task_ids": all_child_task_ids,
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "verificação em lote de nós L2"},
        "checklist_state": {"test": True, "implementation": False},
        "branch": first.get("branch", {}),
        "branches": first.get("branches", []),
    }


def _create_injected_l2_association_task(target_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Cria a segunda auditoria L2: associação de código e testes reais."""
    if not target_nodes:
        raise ValueError("lista de nós vazia para associação")
    first = target_nodes[0]
    ids = ":".join(str(node.get("node_id")) for node in target_nodes)
    draw_id = first.get("draw_id", "system")
    task_id = f"task:associate:{draw_id}:batch:{ids}" if len(target_nodes) > 1 else f"task:associate:{draw_id}:node:{first.get('node_id')}"
    return {
        "id": task_id,
        "draw_id": draw_id,
        "backlog_id": first.get("backlog_id"),
        "parent_task_id": first.get("id"),
        "node_id": first.get("node_id"),
        "label": "Associação de símbolos, arquivos e testes",
        "description": "Associar os símbolos qualificados, arquivos de implementação, views, contratos e testes reais aos nós L2 e aos subfluxos auditados, sem usar placeholders.",
        "level": 2,
        "status": "in_progress",
        "target_task_ids": [node.get("id") for node in target_nodes],
        "verified_nodes": deepcopy([{"node_id": node.get("node_id"), "label": node.get("label", ""), "symbols": node.get("symbols", [])} for node in target_nodes]),
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "associação posterior à auditoria funcional"},
        "checklist_state": {"test": True, "implementation": False},
    }


def _create_injected_final_task() -> dict[str, Any]:
    """Cria a task de encerramento final e verificação end-to-end do MVP."""
    return {
        "id": "task:final:verification",
        "draw_id": "system",
        "backlog_id": "system",
        "label": "Verificação Final da Implementação e Associação de Símbolos",
        "description": "Realizar a auditoria final de ponta a ponta do código implementado do MVP em relação à especificação e associar os símbolos e testes reais aos nós correspondentes.",
        "level": 1,
        "status": "in_progress",
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "verificação final do MVP"},
        "checklist_state": {"test": True, "implementation": False},
        "branch": {"id": "system:final", "position": 1},
        "branches": [{"id": "system:final", "position": 1}],
    }


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


def _normalize_test_ref(node: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Normaliza test_ref/test_refs para um arquivo e funções de teste.
    Aceita os dois formatos públicos, mas rejeita cobertura espalhada por arquivos.
    """
    raw_refs: list[Any] = []
    if "test_ref" in node:
        raw_refs.append(node.get("test_ref"))
    if "test_refs" in node:
        raw_value = node.get("test_refs")
        if not isinstance(raw_value, list):
            return None, "test_refs deve ser uma lista"
        raw_refs.extend(raw_value)
    if not raw_refs:
        return None, "test_ref ausente"

    files: set[str] = set()
    symbols: set[str] = set()
    for reference in raw_refs:
        if not isinstance(reference, dict):
            return None, "cada referência de teste deve ser um objeto"
        file = reference.get("file")
        if not isinstance(file, str) or not file.strip():
            return None, "referência de teste precisa de file"
        files.add(file.strip())
        raw_symbols = reference.get("symbols")
        if not isinstance(raw_symbols, list):
            return None, "referência de teste precisa de symbols como lista"
        symbols.update(symbol.strip() for symbol in raw_symbols if isinstance(symbol, str) and symbol.strip())
    if len(files) != 1:
        return None, "a cobertura de teste deve usar um único arquivo"
    if not symbols:
        return None, "referência de teste precisa de ao menos uma função em symbols"
    return {"file": next(iter(files)), "symbols": sorted(symbols)}, None


def _static_test_symbols(root: Path) -> list[dict[str, Any]] | None:
    """Lê o inventário de símbolos produzido pela análise estática atual."""
    path = root / ".stdd" / "adapters" / "static-analysis-kpis.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    details = payload.get("details") if isinstance(payload, dict) else None
    symbols = details.get("symbols") if isinstance(details, dict) else None
    return symbols if isinstance(symbols, list) else None


def _test_reference_status(root: Path, test_ref: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    """Comprova arquivo e funções de teste sem afirmar cobertura não analisada."""
    if error or test_ref is None:
        return {"status": "missing", "file": test_ref.get("file") if test_ref else None, "symbols": test_ref.get("symbols", []) if test_ref else [], "reason": error or "test_ref ausente"}
    file_value = test_ref["file"]
    file_path = Path(file_value)
    if file_path.is_absolute() or ".." in file_path.parts:
        return {"status": "missing", **deepcopy(test_ref), "reason": "arquivo de teste precisa ser relativo ao projeto"}
    if not (root / file_path).is_file():
        return {"status": "missing", **deepcopy(test_ref), "reason": "arquivo de teste não existe"}
    available = _static_test_symbols(root)
    if available is None:
        return {"status": "missing", **deepcopy(test_ref), "reason": "análise estática de testes não disponível"}
    available_symbols = {
        (item.get("qualified_name"), item.get("file"))
        for item in available
        if isinstance(item, dict)
    }
    missing = [symbol for symbol in test_ref["symbols"] if (symbol, file_value) not in available_symbols]
    if missing:
        return {"status": "missing", **deepcopy(test_ref), "missing_symbols": missing, "reason": "função(ões) de teste não encontrada(s) na análise estática"}
    return {"status": "done", **deepcopy(test_ref), "missing_symbols": [], "reason": "arquivo e funções comprovados"}


def _default_checklist_state(task: dict[str, Any]) -> dict[str, bool]:
    """Cria os estados de checklist para backlogs antigos ou tasks novas."""
    return {
        "test": task.get("test_status") == "done",
        "implementation": task.get("status") == "done",
    }


def _valid_checklist_state(value: Any) -> dict[str, bool] | None:
    """Aceita somente os dois marcadores booleanos persistidos pelo viewer."""
    if not isinstance(value, dict):
        return None
    if not isinstance(value.get("test"), bool) or not isinstance(value.get("implementation"), bool):
        return None
    return {"test": value["test"], "implementation": value["implementation"]}


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


def _task_for_node(root: Path, document: dict[str, Any], node: dict[str, Any], branch: dict[str, Any], position: int, checklist_ids: set[str], parent_task_id: str | None = None, test_owner_task_id: str | None = None) -> dict[str, Any]:
    draw_id = str(document["id"])
    node_id = node["id"]
    symbols, dependencies, code_refs = _reference_symbols(node)
    level = document.get("_hierarchy", {}).get("level")
    item_id = f"task:{draw_id}:node:{node_id}"
    occurrence = _branch_occurrence(draw_id, branch, position, node_id)
    test_ref, test_ref_error = _normalize_test_ref(node) if level == 2 else (None, None)
    owner_id = item_id if level == 2 else test_owner_task_id
    return {
        "id": item_id,
        "draw_id": draw_id,
        "backlog_id": draw_id,
        "parent_task_id": parent_task_id,
        "draw_title": document.get("title", draw_id),
        "node_id": node_id,
        "level": level,
        "label": node.get("label", ""),
        "description": node.get("description", ""),
        "questions": deepcopy(node.get("questions", [])) if isinstance(node.get("questions", []), list) else [],
        "code_refs": code_refs,
        "symbols": symbols,
        "source_dependencies": dependencies,
        "traceability": _traceability(root, draw_id, node_id, symbols),
        "test_ref": test_ref,
        "test_ref_error": test_ref_error,
        "test_owner_task_id": owner_id,
        "test_status": "missing" if owner_id else "not-required",
        "test_evidence": _test_reference_status(root, test_ref, test_ref_error) if level == 2 else {"status": "not-required", "reason": "coberto pela task de nível 2"},
        "checklist_state": {"test": False, "implementation": False},
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
                child_task = _task_for_node(
                    root,
                    child_document,
                    child_node,
                    child_branch,
                    position,
                    context["checklist_ids"],
                    parent_task["id"],
                    parent_task.get("test_owner_task_id"),
                )
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


def _refresh_test_statuses(root: Path, tasks: list[dict[str, Any]]) -> None:
    """Atualiza a evidência do teste do nível 2 e propaga-a aos subfluxos."""
    owners = {
        task["id"]: task
        for task in tasks
        if task.get("level") == 2
    }
    for task in owners.values():
        reference, error = _normalize_test_ref(task)
        error = task.get("test_ref_error") or error
        evidence = _test_reference_status(root, reference, error)
        task["test_ref"] = reference
        task["test_ref_error"] = error
        task["test_status"] = evidence["status"]
        task["test_evidence"] = evidence
    for task in tasks:
        owner_id = task.get("test_owner_task_id")
        if task.get("level") == 2 or not owner_id:
            continue
        owner = owners.get(owner_id)
        if owner is None:
            task["test_status"] = "missing"
            task["test_evidence"] = {"status": "missing", "reason": "task proprietária de teste não encontrada"}
            continue
        task["test_ref"] = deepcopy(owner.get("test_ref"))
        task["test_status"] = owner.get("test_status", "missing")
        task["test_evidence"] = deepcopy(owner.get("test_evidence", {}))


def _refresh_checklist_states(tasks: list[dict[str, Any]], previous_tasks: dict[str, dict[str, Any]]) -> None:
    """Preserva marcações manuais e inicializa o estado dos subfluxos."""
    owners = {task["id"]: task for task in tasks if task.get("level") == 2}
    for task in tasks:
        previous = previous_tasks.get(task.get("id"), {})
        state = _valid_checklist_state(previous.get("checklist_state"))
        if state is None:
            state = _default_checklist_state(task)
            owner = owners.get(task.get("test_owner_task_id"))
            if task.get("level") != 2 and owner is not None:
                state["test"] = _valid_checklist_state(owner.get("checklist_state")) is not None and owner["checklist_state"]["test"]
        task["checklist_state"] = state


def _phase_checklists(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Materializa os dois checklists centrais a partir das tasks atuais."""
    result = {"test": [], "implementation": []}
    for task in tasks:
        state = task.get("checklist_state", {})
        base = {
            "task_id": task["id"],
            "draw_id": task.get("draw_id"),
            "node_id": task.get("node_id"),
            "label": task.get("label", ""),
            "parent_task_id": task.get("parent_task_id"),
        }
        result["test"].append({"id": f"check:test:{task['id']}", **base, "checked": bool(state.get("test")), "evidence_status": task.get("test_evidence", {}).get("status")})
        result["implementation"].append({"id": f"check:implementation:{task['id']}", **base, "checked": bool(state.get("implementation")), "status": task.get("status")})
    return result


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
    _refresh_test_statuses(root, tasks)
    _refresh_checklist_states(tasks, previous_tasks)
    previous_execution = previous.get("execution", {}) if isinstance(previous.get("execution", {}), dict) else {}
    execution_config = _execution_config(root)
    current_phase = previous_execution.get("current_phase")
    valid_task_ids = {task["id"] for task in tasks}
    prev_id = previous_execution.get("current_task_id")
    is_injected_id = bool(prev_id and (prev_id == "task:bootstrap" or prev_id.startswith("task:verify:") or prev_id == "task:final:verification"))
    current_task_id = prev_id if (prev_id in valid_task_ids or is_injected_id) else None
    if current_task_id and current_phase != "test" and not is_injected_id and next((task for task in tasks if task["id"] == current_task_id), {}).get("status") == "done":
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
        "level_semantics": _level_semantics(root),
        "checklists": checklists,
        "phase_checklists": _phase_checklists(tasks),
        "backlogs": backlogs,
        "tasks": tasks,
        "execution": {
            "current_task_id": current_task_id,
            "current_backlog_id": current_task.get("backlog_id") if current_task else previous_execution.get("current_backlog_id"),
            "current_branch_id": previous_execution.get("current_branch_id"),
            "branch_position": previous_execution.get("branch_position"),
            "current_phase": current_phase,
            "current_parent_task_id": previous_execution.get("current_parent_task_id"),
            "current_subtask_id": previous_execution.get("current_subtask_id"),
            "bootstrap_done": previous_execution.get("bootstrap_done", False),
            "verified_l2_task_ids": previous_execution.get("verified_l2_task_ids", []),
            "current_verified_batch_node_ids": previous_execution.get("current_verified_batch_node_ids", []),
            "current_association_node_ids": previous_execution.get("current_association_node_ids", []),
            "final_verification_done": previous_execution.get("final_verification_done", False),
            "lease_id": previous_execution.get("lease_id"),
            "lease_started_at": previous_execution.get("lease_started_at"),
            "lease_expires_at": previous_execution.get("lease_expires_at"),
            "last_claim_at": previous_execution.get("last_claim_at"),
            "last_transition_at": previous_execution.get("last_transition_at"),
            "lease_seconds": execution_config["lease_seconds"],
            "task_batch_size": execution_config["task_batch_size"],
            "task_batch_scope": execution_config["task_batch_scope"],
            "task_delivery_scope": execution_config["task_delivery_scope"],
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
            if isinstance(task, dict):
                test_status = task.get("test_status")
                if test_status is not None and test_status not in VALID_TEST_STATUSES | {"not-required"}:
                    violations.append(f"tasks[{index}].test_status inválido")
                test_ref = task.get("test_ref")
                if test_ref is not None:
                    if not isinstance(test_ref, dict):
                        violations.append(f"tasks[{index}].test_ref deve ser um objeto")
                    else:
                        if not isinstance(test_ref.get("file"), str) or not test_ref["file"].strip():
                            violations.append(f"tasks[{index}].test_ref.file é obrigatório")
                        symbols = test_ref.get("symbols")
                        if not isinstance(symbols, list) or not all(isinstance(symbol, str) and symbol.strip() for symbol in symbols):
                            violations.append(f"tasks[{index}].test_ref.symbols deve ser uma lista de nomes")
                checklist_state = task.get("checklist_state")
                if checklist_state is not None and _valid_checklist_state(checklist_state) is None:
                    violations.append(f"tasks[{index}].checklist_state inválido")
    if not isinstance(payload.get("execution"), dict):
        violations.append("execution deve ser um objeto")
    elif payload["execution"].get("current_phase") not in VALID_EXECUTION_PHASES:
        violations.append("execution.current_phase inválido")
    phase_checklists = payload.get("phase_checklists")
    if phase_checklists is not None:
        if not isinstance(phase_checklists, dict):
            violations.append("phase_checklists deve ser um objeto")
        else:
            for phase in VALID_CHECKLIST_PHASES:
                if not isinstance(phase_checklists.get(phase), list):
                    violations.append(f"phase_checklists.{phase} deve ser uma lista")
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
            "missing_tests": 0,
            "missing_test_task_ids": [],
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
            "missing_tests": 0,
            "missing_test_task_ids": [],
            "current_task_id": None,
            "errors": [str(error)],
        }
    tasks = [task for task in payload.get("tasks", []) if isinstance(task, dict)]
    remaining = [task for task in tasks if task.get("status") != "done"]
    missing_tests = _pending_test_tasks(payload)
    execution = payload.get("execution", {}) if isinstance(payload.get("execution"), dict) else {}
    blocked_by_tests = bool(missing_tests)
    
    config = _get_backlog_config(root)
    bootstrap_pending = bool(tasks and _bootstrap_enabled(config) and not execution.get("bootstrap_done", False))
    final_pending = bool(tasks and config.get("final_verification_task", config.get("final_verification_enabled", False)) and not execution.get("final_verification_done", False))
    
    interval = config.get("l2_verification_interval", config.get("verification_interval", 0))
    l2_pending = False
    if interval > 0:
        tasks_by_id = {t.get("id"): t for t in tasks}
        l2_tasks = [t for t in tasks if t.get("level") == 2]
        verified_ids = set(execution.get("verified_l2_task_ids", []))
        completed_l2 = [
            t for t in l2_tasks
            if t.get("status") == "done" and all(tasks_by_id.get(cid, {}).get("status") == "done" for cid in t.get("child_task_ids", []))
        ]
        unverified = [t for t in completed_l2 if t.get("id") not in verified_ids]
        if unverified and (len(unverified) >= interval or not remaining):
            l2_pending = True

    injected_pending_count = (1 if bootstrap_pending else 0) + (1 if final_pending else 0) + (1 if l2_pending else 0)
    has_pending = bool(remaining or blocked_by_tests or injected_pending_count > 0)

    return {
        "name": "backlog",
        "status": "blocked" if has_pending else "passed",
        "reason": "tasks_missing_tests" if blocked_by_tests else "tasks_pending" if has_pending else "all_tasks_complete",
        "total": len(tasks),
        "done": len(tasks) - len(remaining),
        "remaining": len(remaining) + injected_pending_count,
        "remaining_task_ids": [task.get("id") for task in remaining[:10]],
        "missing_tests": len(missing_tests),
        "missing_test_task_ids": [task.get("id") for task in missing_tests[:10]],
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


def _clear_execution_cursor(execution: dict[str, Any]) -> None:
    """Limpa a reserva atual sem apagar o histórico das branches."""
    execution["current_task_id"] = None
    execution["current_backlog_id"] = None
    execution["current_branch_id"] = None
    execution["branch_position"] = None
    execution["current_phase"] = None
    execution["current_parent_task_id"] = None
    execution["current_subtask_id"] = None
    execution["lease_id"] = None
    execution["lease_started_at"] = None
    execution["lease_expires_at"] = None
    execution["last_transition_at"] = datetime.now(timezone.utc).isoformat()


def _mark_claim(execution: dict[str, Any]) -> None:
    """Registra lease/cursor de uma reserva sem esconder o histórico."""
    now = datetime.now(timezone.utc)
    lease_seconds = int(execution.get("lease_seconds", 900) or 900)
    execution["lease_id"] = f"lease:{now.timestamp():.6f}"
    execution["lease_started_at"] = now.isoformat()
    execution["lease_expires_at"] = (now.timestamp() + lease_seconds)
    execution["last_claim_at"] = now.isoformat()


def _enforce_claim_window(execution: dict[str, Any], config: dict[str, Any]) -> None:
    """Bloqueia somente avanço rápido configurado; reler a task atual é seguro."""
    minimum = int(config.get("min_task_interval_seconds", 0) or 0)
    previous = execution.get("last_transition_at")
    if minimum <= 0 or not isinstance(previous, str):
        return
    try:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(previous)).total_seconds()
    except ValueError:
        return
    if elapsed < minimum:
        raise ValueError(f"janela mínima entre tasks ainda não terminou ({minimum} segundos)")


def _parent_task(tasks: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    """Encontra a task pai raiz que contextualiza uma subtask."""
    by_id = {item.get("id"): item for item in tasks}
    current = task
    visited: set[str] = set()
    while isinstance(current.get("parent_task_id"), str) and current["parent_task_id"] not in visited:
        visited.add(current["id"])
        parent = by_id.get(current["parent_task_id"])
        if parent is None:
            break
        current = parent
    return current


def _task_context(root: Path, payload: dict[str, Any], task: dict[str, Any], phase: str, kind: str, instruction: str | None = None) -> dict[str, Any]:
    """Retorna a task atual com pai e subtasks para o agente manter contexto."""
    tasks = payload.get("tasks", [])
    parent = _parent_task(tasks, task)
    descendants = [
        item for item in tasks
        if item.get("id") in parent.get("child_task_ids", [])
    ]
    subtask = task if task.get("id") != parent.get("id") else next(
        (item for item in descendants if item.get("status") != "done"),
        None,
    )
    
    origin_nodes = []
    origin_edges = []
    access_paths = []
    predecessor: dict[str, Any] | None = None
    connection: dict[str, Any] | None = None
    
    draw_id = task.get("backlog_id")
    node_id = task.get("node_id")
    
    if draw_id is not None and node_id is not None:
        try:
            document = read_draw(root, draw_id)
            nodes = {n.get("id"): n for n in document.get("nodes", [])}
            for edge in document.get("edges", []):
                if edge.get("to") == node_id:
                    origin_edges.append(edge)
                    from_id = edge.get("from")
                    if from_id in nodes:
                        from_node = nodes[from_id]
                        origin_nodes.append(from_node)
                        label = from_node.get("label") or str(from_id)
                        condition = EDGE_CONDITIONS.get(edge.get("condition"), "então")
                        access_paths.append(f"Nó {label} → {condition} → Nó atual")
                        if predecessor is None:
                            predecessor = {
                                "node_id": from_id,
                                "label": from_node.get("label", ""),
                                "description": from_node.get("description", ""),
                                "questions": deepcopy(from_node.get("questions", [])),
                                "symbols": _reference_symbols(from_node)[0],
                            }
                            connection = {
                                "condition": edge.get("condition"),
                                "condition_label": condition,
                                "label": edge.get("label", ""),
                                "description": edge.get("description", ""),
                            }
        except Exception:
            pass

    if phase == "bootstrap":
        state = "bootstrap_in_progress"
    elif phase == "test":
        state = "tests_in_progress"
    elif task.get("test_status") in {"missing", "in_progress"}:
        state = "tests_missing"
    elif task.get("status") == "in_progress":
        state = "implementation_in_progress"
    elif task.get("status") == "done":
        state = "backlog_complete" if not any(item.get("status") != "done" for item in tasks) else "tests_ready"
    else:
        state = "tests_ready"

    response: dict[str, Any] = {
        "kind": kind,
        "phase": phase,
        "state": state,
        "task": task,
        "parent_task": parent,
        "subtask": subtask,
        "subtasks": descendants,
        "origin_nodes": origin_nodes,
        "origin_edges": origin_edges,
        "access_paths": access_paths,
        "previous_node": predecessor,
        "connection": connection,
        "condition": connection.get("condition_label") if connection else None,
        "path": access_paths[0] if access_paths else None,
    }
    level_context = payload.get("level_semantics", {}).get(str(task.get("level"))) if isinstance(payload.get("level_semantics"), dict) else None
    if isinstance(level_context, dict):
        response["level_context"] = deepcopy(level_context)
    response["task_delivery_scope"] = _task_delivery_scope(payload)
    if response["task_delivery_scope"] == "node" and task.get("id") == parent.get("id"):
        response["delivery_subtasks"] = deepcopy(descendants)
    options = _execution_config(root)
    if options["task_batch_size"] > 1 and task.get("id") in [item.get("id") for item in tasks]:
        start = next(index for index, item in enumerate(tasks) if item.get("id") == task.get("id"))
        candidates = [item for item in tasks[start:] if item.get("status") != "done"]
        if options["task_batch_scope"] == "node":
            candidates = [item for item in candidates if item.get("node_id") == task.get("node_id")]
        response["batch"] = [{"id": item.get("id"), "label": item.get("label", "")} for item in candidates[:options["task_batch_size"]]]
        response["batch_size"] = len(response["batch"])
    if instruction is not None:
        response["instruction"] = instruction
    return response


def _task_for_update(payload: dict[str, Any], task_id: str) -> dict[str, Any]:
    """Obtém uma task do backlog ou retorna um erro acionável."""
    task = next((item for item in payload.get("tasks", []) if item.get("id") == task_id), None)
    if task is None:
        raise ValueError("task-id não existe no backlog")
    return task


def _test_scope_tasks(payload: dict[str, Any], task: dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna o pai e todos os subfluxos cobertos pelo teste agregado."""
    parent = _parent_task(payload.get("tasks", []), task)
    return [parent] + [
        item for item in payload.get("tasks", [])
        if item.get("id") in parent.get("child_task_ids", [])
    ]


def _task_delivery_scope(payload: dict[str, Any]) -> str:
    """Retorna o escopo comum de entrega das fases de teste e implementação."""
    scope = payload.get("execution", {}).get("task_delivery_scope")
    if scope not in VALID_TASK_DELIVERY_SCOPES:
        scope = payload.get("execution", {}).get("test_task_scope", "task")
    return scope if scope in VALID_TASK_DELIVERY_SCOPES else "task"


def _test_scope_complete(payload: dict[str, Any], task: dict[str, Any]) -> bool:
    """Verifica evidência e marcação de teste para pai e todos os subfluxos."""
    if _task_delivery_scope(payload) == "task":
        return task.get("checklist_state", {}).get("test") is True
    scope = _test_scope_tasks(payload, task)
    return all(
        item.get("checklist_state", {}).get("test") is True
        for item in scope
    )


def _pending_test_tasks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna as tasks que ainda precisam passar pela fase de testes."""
    if _task_delivery_scope(payload) == "task":
        return [
            item for item in payload.get("tasks", [])
            if item.get("level") in {2, 3} and not _test_scope_complete(payload, item)
        ]
    return [
        item for item in payload.get("tasks", [])
        if item.get("level") == 2 and not _test_scope_complete(payload, item)
    ]


def _implementation_delivery_task(payload: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Agrupa subfluxos na task pai quando o escopo de entrega é `node`."""
    if _task_delivery_scope(payload) != "node":
        return task
    parent = _parent_task(payload.get("tasks", []), task)
    return parent if parent.get("status") != "done" else task


def _refresh_task_checklist_items(payload: dict[str, Any]) -> None:
    """Sincroniza checklist, task status e branches depois de uma edição."""
    payload["phase_checklists"] = _phase_checklists(payload.get("tasks", []))
    for checklist in payload.get("checklists", []):
        for item in checklist.get("items", []):
            task = next((task for task in payload.get("tasks", []) if task.get("id") == item.get("task_id")), None)
            if task is not None:
                item["status"] = task.get("status", "pending")
                item["task"] = task
    _refresh_branch_completion(payload)


def update_backlog_checklist(root: Path, task_id: str, phase: str, checked: bool) -> dict[str, Any]:
    """Atualiza um checkbox do backlog pela API local do viewer."""
    if phase not in VALID_CHECKLIST_PHASES:
        raise ValueError("fase de checklist inválida")
    if not isinstance(checked, bool):
        raise ValueError("checked deve ser booleano")
    payload = generate_backlog(root)
    task = _task_for_update(payload, task_id)
    state = task.setdefault("checklist_state", _default_checklist_state(task))
    if phase == "implementation" and checked and not _test_scope_complete(payload, task):
        raise ValueError("checklist de teste do nó e dos subfluxos ainda não foi concluído")
    state[phase] = checked
    if phase == "implementation":
        task["status"] = "done" if checked else "pending"
    elif not checked:
        parent = _parent_task(payload.get("tasks", []), task)
        scope_ids = {parent.get("id"), *parent.get("child_task_ids", [])}
        for item in payload.get("tasks", []):
            if item.get("id") in scope_ids:
                item.setdefault("checklist_state", _default_checklist_state(item))["implementation"] = False
                item["status"] = "pending"
    _refresh_task_checklist_items(payload)
    write_backlog(root, payload)
    return {"kind": "backlog-checklist-updated", "phase": phase, "checked": checked, "task": task, "backlog": payload}


def next_backlog_test(root: Path) -> dict[str, Any]:
    """Entrega a próxima task de teste antes da implementação.
    Mantém a reserva incremental e agrega os subfluxos na task de nível 2.
    """
    payload = generate_backlog(root)
    execution = payload["execution"]
    current_id = execution.get("current_task_id")
    current = next((task for task in payload["tasks"] if task["id"] == current_id), None)
    if current_id == "task:bootstrap":
        return _task_context(root, payload, _create_injected_bootstrap_task(), "bootstrap", "backlog-bootstrap-task", _bootstrap_instruction())

    # Um backlog gerado por uma versão anterior pode ter uma task de produto
    # reservada antes do bootstrap, deixando `bootstrap_done` falso e o cursor
    # na fase de testes. O bootstrap é uma barreira global e precisa recuperar
    # esse estado antes de devolver a task antiga.
    config = _get_backlog_config(root)
    bootstrap_enabled = _bootstrap_enabled(config)
    if payload["tasks"] and bootstrap_enabled and not execution.get("bootstrap_done", False):
        if current is not None:
            previous_status = current.pop("test_previous_status", None)
            if previous_status in VALID_TASK_STATUSES:
                current["status"] = previous_status
            elif current.get("status") == "in_progress":
                current["status"] = "pending"
            if current.get("test_status") == "in_progress":
                current["test_status"] = "missing"
        execution["current_task_id"] = None
        execution["current_backlog_id"] = None
        execution["current_branch_id"] = None
        execution["branch_position"] = None
        execution["current_parent_task_id"] = None
        execution["current_subtask_id"] = None
        execution["lease_id"] = None
        execution["lease_started_at"] = None
        execution["lease_expires_at"] = None
        task = _create_injected_bootstrap_task()
        task["checks"] = bootstrap_report(root)
        execution["current_task_id"] = task["id"]
        _mark_claim(execution)
        execution["current_backlog_id"] = "system"
        execution["current_phase"] = "bootstrap"
        write_backlog(root, payload)
        return _task_context(root, payload, task, "bootstrap", "backlog-bootstrap-task", _bootstrap_instruction())

    if execution.get("current_phase") == "test" and current is not None:
        return _task_context(root, payload, current, "test", "backlog-test-task")
    if execution.get("current_phase") in {"bootstrap", "implementation"} and current is not None:
        raise ValueError("a task atual já está na fase de implementação")
    task = next(iter(_pending_test_tasks(payload)), None)
    if task is None:
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        return {"kind": "backlog-test-empty", "status": "complete", "remaining": 0}
    task["test_status"] = "in_progress"
    task["test_previous_status"] = task.get("status")
    if task.get("status") == "pending":
        task["status"] = "in_progress"
    execution["current_task_id"] = task["id"]
    _mark_claim(execution)
    execution["current_backlog_id"] = task.get("backlog_id")
    execution["current_branch_id"] = task.get("branch", {}).get("id")
    execution["branch_position"] = task.get("branch", {}).get("position")
    execution["current_phase"] = "test"
    execution["current_parent_task_id"] = _parent_task(payload["tasks"], task).get("id")
    execution["current_subtask_id"] = task.get("id") if task.get("parent_task_id") else None
    write_backlog(root, payload)
    return _task_context(root, payload,
        task,
        "test",
        "backlog-test-task",
        (
            "Crie os testes deste nó ou subfluxo; não implemente produção."
            if _task_delivery_scope(payload) == "task"
            else "Crie os testes do nó de nível 2 e de todos os seus subfluxos; não implemente produção."
        ),
    )


def next_backlog_task(root: Path, verification_interval: int | None = None) -> dict[str, Any]:
    """Entrega e persiste a próxima task da ordem de branches."""
    payload = generate_backlog(root)
    execution = payload["execution"]
    current_id = execution.get("current_task_id")
    current_phase = execution.get("current_phase")
    config = _get_backlog_config(root)
    execution_options = _execution_config(root)
    if verification_interval is not None:
        config = {**config, "l2_verification_interval": int(verification_interval)}
    if not current_id:
        _enforce_claim_window(execution, execution_options)

    # 1. Se já há uma task em andamento no cursor:
    if current_id:
        if current_id == "task:bootstrap":
            task = _create_injected_bootstrap_task()
            task["checks"] = bootstrap_report(root)
            bootstrap_phase = current_phase if current_phase == "bootstrap" else "implementation"
            bootstrap_kind = "backlog-bootstrap-task" if bootstrap_phase == "bootstrap" else "backlog-task"
            return _task_context(
                root,
                payload,
                task,
                bootstrap_phase,
                bootstrap_kind,
                _bootstrap_instruction(),
            )
        if current_id.startswith("task:verify:"):
            batch_node_ids = execution.get("current_verified_batch_node_ids", [])
            tasks_by_id = {t["id"]: t for t in payload["tasks"]}
            target_nodes = [tasks_by_id[nid] for nid in batch_node_ids if nid in tasks_by_id]
            if not target_nodes:
                for t in payload["tasks"]:
                    if t.get("level") == 2 and (f"task:verify:{t.get('draw_id')}:node:{t.get('node_id')}" == current_id or str(t.get("node_id")) in current_id):
                        target_nodes.append(t)
            if target_nodes:
                task = _create_injected_l2_batch_verify_task(target_nodes)
                labels_str = ", ".join(f"'{n.get('label')}'" for n in target_nodes)
                return _task_context(
                    root,
                    payload,
                    task,
                    "implementation",
                    "backlog-task",
                    f"Audite o código implementado para os nós ({labels_str}) e seus subfluxos. Valide se a implementação de produção cumpre fielmente a especificação (regras, persistência, validações e integração real); não altere o fluxo nem o desenho.",
                )
        if current_id.startswith("task:associate:"):
            batch_node_ids = execution.get("current_association_node_ids", [])
            tasks_by_id = {t["id"]: t for t in payload["tasks"]}
            target_nodes = [tasks_by_id[nid] for nid in batch_node_ids if nid in tasks_by_id]
            task = _create_injected_l2_association_task(target_nodes) if target_nodes else {"id": current_id, "label": "Associação de símbolos", "status": "in_progress"}
            return _task_context(root, payload, task, "implementation", "backlog-task", "Associe símbolos, arquivos e testes reais no nó correspondente e valide as referências.")
        if current_id == "task:final:verification":
            task = _create_injected_final_task()
            return _task_context(
                root,
                payload,
                task,
                "implementation",
                "backlog-task",
                "Audite a implementação de ponta a ponta do MVP completo em relação à especificação, execute os testes para garantir estabilidade e associe os símbolos e testes aos nós L2 e L3 correspondentes.",
            )

        current = next((task for task in payload["tasks"] if task["id"] == current_id), None)
        if current_phase == "test" and current and not _test_scope_complete(payload, current):
            response = _task_context(root, payload, current, "test", "backlog-test-required")
            response.update({"status": "blocked", "reason": "test_in_progress"})
            return response
        if current_phase == "implementation" and current and current.get("status") == "in_progress":
            return _task_context(root, payload, current, "implementation", "backlog-task")
        if current and current.get("status") == "in_progress":
            return _task_context(root, payload, current, "implementation", "backlog-task")

    # 2. O bootstrap agnóstico é sempre a primeira task operacional, salvo opt-out explícito.
    has_tasks = len(payload["tasks"]) > 0
    bootstrap_enabled = _bootstrap_enabled(config)
    if has_tasks and bootstrap_enabled and not execution.get("bootstrap_done", False):
        task = _create_injected_bootstrap_task()
        task["checks"] = bootstrap_report(root)
        execution["current_task_id"] = task["id"]
        _mark_claim(execution)
        execution["current_backlog_id"] = "system"
        execution["current_phase"] = "implementation"
        write_backlog(root, payload)
        return _task_context(root, payload, task, "implementation", "backlog-task", _bootstrap_instruction())

    # 3. Se o próximo nó L2 ainda não tem testes comprovados, bloqueia avisando backlog-test-required
    pending_task = next((item for item in payload["tasks"] if item.get("status") != "done"), None)
    if pending_task and not _test_scope_complete(payload, pending_task):
        response = _task_context(root, payload, pending_task, "test", "backlog-test-required")
        response.update({"status": "blocked", "reason": "test_missing" if pending_task.get("test_status") == "missing" else "test_not_complete"})
        return response

    # 4. Verifica se há verificação de nó L2 pendente que deve rodar antes das próximas tasks
    interval = config.get("l2_verification_interval", config.get("verification_interval", 0))
    if interval > 0:
        tasks_by_id = {t["id"]: t for t in payload["tasks"]}
        l2_tasks = [t for t in payload["tasks"] if t.get("level") == 2]
        verified_ids = set(execution.get("verified_l2_task_ids", []))
        completed_l2 = [
            t for t in l2_tasks
            if t.get("status") == "done" and all(tasks_by_id.get(cid, {}).get("status") == "done" for cid in t.get("child_task_ids", []))
        ]
        unverified = [t for t in completed_l2 if t["id"] not in verified_ids]
        all_normal_tasks_done = not any(item.get("status") != "done" for item in payload["tasks"])
        if unverified and (len(unverified) >= interval or all_normal_tasks_done):
            batch_count = interval if len(unverified) >= interval else len(unverified)
            target_nodes = unverified[:batch_count]
            task = _create_injected_l2_batch_verify_task(target_nodes)
            execution["current_task_id"] = task["id"]
            _mark_claim(execution)
            execution["current_verified_batch_node_ids"] = [n["id"] for n in target_nodes]
            execution["current_backlog_id"] = target_nodes[0].get("backlog_id")
            execution["current_phase"] = "implementation"
            write_backlog(root, payload)
            labels_str = ", ".join(f"'{n.get('label')}'" for n in target_nodes)
            return _task_context(
                root,
                payload,
                task,
                "implementation",
                "backlog-task",
                f"Audite o código implementado para os nós ({labels_str}) e seus subfluxos. Valide se a implementação de produção cumpre fielmente a especificação (regras, persistência, validações e integração real); não altere o fluxo nem o desenho.",
            )

    # 5. Busca a próxima task normal do backlog
    task = next((item for item in payload["tasks"] if item.get("status") != "done"), None)
    if task is None:
        # Se todas as tasks normais foram concluídas, verifica se precisamos da Task Final
        final_enabled = config.get("final_verification_task", config.get("final_verification_enabled", False))
        if has_tasks and final_enabled and not execution.get("final_verification_done", False):
            final_task = _create_injected_final_task()
            execution["current_task_id"] = final_task["id"]
            _mark_claim(execution)
            execution["current_backlog_id"] = "system"
            execution["current_phase"] = "implementation"
            write_backlog(root, payload)
            return _task_context(
                root,
                payload,
                final_task,
                "implementation",
                "backlog-task",
                "Audite a implementação de ponta a ponta do MVP completo em relação à especificação, execute os testes para garantir estabilidade e associe os símbolos e testes aos nós L2 e L3 correspondentes.",
            )

        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        return {"kind": "backlog-empty", "status": "complete", "remaining": 0}

    task = _implementation_delivery_task(payload, task)

    # 6. Se for nó L2 sem teste comprovado, bloqueia avisando
    if not _test_scope_complete(payload, task):
        response = _task_context(root, payload, task, "test", "backlog-test-required")
        response.update({"status": "blocked", "reason": "test_missing" if task.get("test_status") == "missing" else "test_not_complete"})
        return response

    # 7. Reserva a task normal de implementação
    task["status"] = "in_progress"
    execution["current_task_id"] = task["id"]
    _mark_claim(execution)
    execution["current_backlog_id"] = task.get("backlog_id")
    execution["current_branch_id"] = task["branch"]["id"]
    execution["branch_position"] = task["branch"]["position"]
    execution["current_phase"] = "implementation"
    execution["current_parent_task_id"] = _parent_task(payload["tasks"], task).get("id")
    execution["current_subtask_id"] = task.get("id") if task.get("parent_task_id") else None
    for checklist in payload["checklists"]:
        for item in checklist.get("items", []):
            if item.get("id") == task["id"]:
                item["status"] = "in_progress"
    write_backlog(root, payload)
    return _task_context(root, payload, task, "implementation", "backlog-task")


def complete_backlog_task(root: Path, task_id: str) -> dict[str, Any]:
    """Conclui somente a task atualmente reservada para o agente."""
    payload = generate_backlog(root)
    execution = payload["execution"]
    current_id = execution.get("current_task_id")

    # Tratamento para Bootstrap Task
    if task_id == "task:bootstrap":
        if current_id != "task:bootstrap":
            raise ValueError("task atual não está em andamento")
        config = _get_backlog_config(root)
        checks = bootstrap_report(root)
        if config.get("bootstrap_strict", False) and checks["status"] != "passed":
            raise ValueError("bootstrap bloqueado: " + ", ".join(checks["failures"]))
        bootstrap_phase = execution.get("current_phase") if execution.get("current_phase") in {"bootstrap", "implementation"} else "implementation"
        execution["bootstrap_done"] = True
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = _create_injected_bootstrap_task()
        task["status"] = "done"
        task["checklist_state"] = {"test": True, "implementation": True}
        response = _task_context(root, payload, task, bootstrap_phase, "backlog-bootstrap-complete")
        response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
        return response

    # Tratamento para Verificação de Nó L2 (individual ou em lote)
    if task_id.startswith("task:verify:"):
        if current_id != task_id:
            raise ValueError("task atual não está em andamento")
        batch_node_ids = execution.get("current_verified_batch_node_ids", [])
        tasks_by_id = {t["id"]: t for t in payload["tasks"]}
        target_nodes = [tasks_by_id[nid] for nid in batch_node_ids if nid in tasks_by_id]
        if not target_nodes:
            for t in payload["tasks"]:
                if t.get("level") == 2 and (f"task:verify:{t.get('draw_id')}:node:{t.get('node_id')}" == task_id or str(t.get("node_id")) in task_id):
                    target_nodes.append(t)

        verified = execution.setdefault("verified_l2_task_ids", [])
        for n in target_nodes:
            if n["id"] not in verified:
                verified.append(n["id"])

        execution.pop("current_verified_batch_node_ids", None)
        if _get_backlog_config(root).get("l2_post_verification_tasks", False):
            association = _create_injected_l2_association_task(target_nodes)
            execution["current_task_id"] = association["id"]
            execution["current_association_node_ids"] = [node["id"] for node in target_nodes]
            execution["current_phase"] = "implementation"
            _mark_claim(execution)
            write_backlog(root, payload)
            response = _task_context(root, payload, association, "implementation", "backlog-task", "Associe símbolos, arquivos e testes reais no nó correspondente e valide as referências.")
            response.update({"status": "in_progress"})
            return response
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = _create_injected_l2_batch_verify_task(target_nodes) if target_nodes else {
            "id": task_id, "label": "Verificação Funcional", "level": 2, "status": "done"
        }
        task["status"] = "done"
        task["checklist_state"] = {"test": True, "implementation": True}
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
        return response

    if task_id.startswith("task:associate:"):
        if current_id != task_id:
            raise ValueError("task atual não está em andamento")
        execution.pop("current_association_node_ids", None)
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = {"id": task_id, "label": "Associação de símbolos, arquivos e testes", "status": "done", "level": 2}
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
        return response

    # Tratamento para Task Final
    if task_id == "task:final:verification":
        if current_id != "task:final:verification":
            raise ValueError("task atual não está em andamento")
        execution["final_verification_done"] = True
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = _create_injected_final_task()
        task["status"] = "done"
        task["checklist_state"] = {"test": True, "implementation": True}
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({"status": "done", "remaining": 0})
        return response

    current = next((item for item in payload["tasks"] if item["id"] == current_id), None)
    requested = next((item for item in payload["tasks"] if item["id"] == task_id), None)
    if requested is None:
        raise ValueError("task-id não existe no backlog")
    if current_id != task_id:
        if current is None or requested.get("id") not in current.get("child_task_ids", []):
            raise ValueError("task-id não corresponde à task atual ou a uma subtask do contexto atual")
        if execution.get("current_phase") == "test":
            requested.setdefault("checklist_state", _default_checklist_state(requested))["test"] = True
        else:
            if not _test_scope_complete(payload, current):
                raise ValueError("teste do nó e dos subfluxos ainda não foi concluído")
            requested["status"] = "done"
            requested.setdefault("checklist_state", _default_checklist_state(requested))["implementation"] = True
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, current, execution.get("current_phase") or "implementation", "backlog-subtask-complete")
        response.update({"status": "test-done" if execution.get("current_phase") == "test" else "done", "completed_task_id": task_id})
        return response
    task = next((item for item in payload["tasks"] if item["id"] == task_id), None)
    if task is None:
        raise ValueError("task atual não está em andamento")
    if execution.get("current_phase") == "test":
        previous_status = task.pop("test_previous_status", None)
        task["test_status"] = "done"
        scope_tasks = [task] if _task_delivery_scope(payload) == "task" else _test_scope_tasks(payload, task)
        for scope_task in scope_tasks:
            scope_task.setdefault("checklist_state", _default_checklist_state(scope_task))["test"] = True
        if previous_status == "pending":
            task["status"] = "pending"
        _clear_execution_cursor(execution)
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, task, "test", "backlog-test-complete")
        response.update({"status": "test-done", "remaining": len(_pending_test_tasks(payload))})
        return response
    if task.get("status") != "in_progress":
        raise ValueError("task atual não está em andamento")
    if not _test_scope_complete(payload, task):
        raise ValueError("teste da task ainda não foi comprovado")
    if _task_delivery_scope(payload) == "node":
        scope_tasks = _test_scope_tasks(payload, task)
        for scope_task in scope_tasks:
            scope_task["status"] = "done"
            scope_task.setdefault("checklist_state", _default_checklist_state(scope_task))["implementation"] = True
        _clear_execution_cursor(execution)
        _refresh_branch_completion(payload)
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({
            "status": "done",
            "completed_task_ids": [scope_task.get("id") for scope_task in scope_tasks],
            "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done"),
        })
        return response
    task["status"] = "done"
    task.setdefault("checklist_state", _default_checklist_state(task))["implementation"] = True
    for checklist in payload["checklists"]:
        for item in checklist.get("items", []):
            if item.get("id") == task_id:
                item["status"] = "done"
    _clear_execution_cursor(execution)
    _refresh_branch_completion(payload)
    _refresh_task_checklist_items(payload)
    write_backlog(root, payload)
    response = _task_context(root, payload, task, "implementation", "backlog-complete")
    response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
    return response

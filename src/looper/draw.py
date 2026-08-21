"""Criação de JSONs e servidor local do viewer Draw.
Mantém os dados dos desenhos separados do HTML reutilizável e carregado sob demanda.
"""

from __future__ import annotations

import json
import mimetypes
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import unquote, urlparse

DRAW_VERSION = 1
DRAW_TEMPLATE_VERSION = "5"
EDGE_CONDITIONS = {1: "então", 2: "ou", 3: "se"}
QUESTION_TYPES = {"choice", "boolean", "open"}
HIERARCHY_ROLES = {"architecture", "journey", "implementation", "codebase"}
HIERARCHY_ROLE_BY_LEVEL = {1: "architecture", 2: "journey", 3: "implementation", 4: "codebase"}
DRAW_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
DRAW_ASSETS = Path(__file__).parent / "draw_assets"
DRAW_EXAMPLE_TEMPLATE = Path(__file__).parent / "templates" / "draw" / "example.json"
LEGACY_DRAW_VIEWER = Path(".looper") / "draw.html"
PRESENTATION_KEYS = {"color", "colors", "position", "style", "styles", "layout", "viewport", "theme", "x", "y", "width", "height"}
DRAW_ANALYSIS_SIMILARITY_THRESHOLD = 0.85
DRAW_LEVEL2_CODE_REF_RULE = "draw.level2_missing_code_ref"
DRAW_LEVEL3_CODE_REF_RULE = "draw.level3_missing_code_ref"
DRAW_LEVEL4_CODE_REF_RULE = "draw.level4_missing_code_ref"
DRAW_EMPTY_NODE_SYMBOL_RULE = "draw.empty_node_symbol"
DRAW_DUPLICATE_NODE_SYMBOL_RULE = "draw.duplicate_node_symbol"
UNNAMED_SYMBOL_PATTERNS = {
    "",
    "unnamed",
    "anonymous",
    "(sem nome)",
    "sem nome",
    "sem_nome",
    "none",
    "null",
    "undefined",
    "<unnamed>",
    "placeholder",
    "todo",
    "tbd",
}



def _is_numeric_id(value: Any) -> bool:
    """Valida IDs internos numéricos de nós e relações.
    Inteiros não negativos mantêm referências compactas dentro do fluxo.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_draw_id(value: Any) -> bool:
    """Valida o identificador descritivo que também será o nome do arquivo.
    Usa slug seguro para permitir carregamento de subdesenhos sem caminhos arbitrários.
    """
    return isinstance(value, str) and bool(DRAW_ID_PATTERN.fullmatch(value))


def logical_draw_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove metadados visuais e temporais do documento lógico.
    Layout, cores, dimensões, rotas e datas são responsabilidade do renderer e do índice.
    """
    document = deepcopy(payload)
    for key in PRESENTATION_KEYS | {"created_at", "updated_at"}:
        document.pop(key, None)
    # Draws antigos podem ainda carregar a chave, mas ela nunca volta a ser
    # persistida no contrato atual.
    document.pop("tradeoffs", None)
    for collection in ("groups", "nodes", "edges"):
        for item in document.get(collection, []):
            if isinstance(item, dict):
                for key in PRESENTATION_KEYS:
                    item.pop(key, None)
    for node in document.get("nodes", []):
        if isinstance(node, dict):
            node.pop("type", None)
    return document


def _answer_is_filled(answer: Any) -> bool:
    """Considera false e zero como respostas válidas; só vazio textual falta."""
    return answer is not None and not (isinstance(answer, str) and not answer.strip())


def _draw_question_entries(document: dict[str, Any]):
    """Percorre perguntas de nós e perguntas gerais sem inventar um node_id."""
    general_questions = document.get("questions", [])
    if isinstance(general_questions, list):
        for question in general_questions:
            if isinstance(question, dict):
                yield None, None, question
    for node in document.get("nodes", []):
        if not isinstance(node, dict):
            continue
        questions = node.get("questions", [])
        if not isinstance(questions, list):
            continue
        for question in questions:
            if isinstance(question, dict):
                yield node, node.get("id"), question


def draw_directory(root: Path) -> Path:
    """Retorna o diretório de dados dos desenhos do projeto.
    Mantém todos os JSONs gerados pelo framework dentro de .looper/draws.
    """
    return root / ".looper" / "draws"


def facts_directory(root: Path) -> Path:
    """Retorna o diretório separado dos relatórios derivados de análise."""
    return root / ".looper" / "facts"


def draw_index_path(root: Path) -> Path:
    """Retorna o caminho do índice leve de desenhos.
    O índice contém somente metadados para evitar carregar grafos completos.
    """
    return draw_directory(root) / "index.json"


def validate_draw_payload(payload: Any) -> list[str]:
    """Valida o contrato agnóstico de um desenho antes da persistência.
    Confere IDs, referências de relações, fluxos e a forma básica das coleções.
    """
    if not isinstance(payload, dict):
        return ["o desenho deve ser um objeto JSON"]
    violations: list[str] = []
    if "tradeoffs" in payload:
        violations.append("tradeoffs não faz parte do contrato ativo; use questions")
    draw_id = payload.get("id")
    if not _is_draw_id(draw_id):
        violations.append("id do desenho deve ser descritivo, minúsculo e seguro; use números somente nas entidades internas")
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        violations.append("title é obrigatório")

    hierarchy = payload.get("hierarchy")
    if payload.get("kind") == "system" and hierarchy is None:
        violations.append("desenho kind system deve declarar hierarchy")
    if hierarchy is not None:
        if not isinstance(hierarchy, dict):
            violations.append("hierarchy deve ser um objeto")
            hierarchy = {}
        level = hierarchy.get("level")
        role = hierarchy.get("role")
        parent_draw_ref = hierarchy.get("parent_draw_ref")
        parent_node_id = hierarchy.get("parent_node_id")
        root_draw_ref = hierarchy.get("root_draw_ref")
        if level not in HIERARCHY_ROLE_BY_LEVEL:
            violations.append("hierarchy.level deve ser 1, 2, 3 ou 4")
        if role not in HIERARCHY_ROLES:
            violations.append("hierarchy.role deve ser architecture, journey, implementation ou codebase")
        elif level in HIERARCHY_ROLE_BY_LEVEL and role != HIERARCHY_ROLE_BY_LEVEL[level]:
            violations.append("hierarchy.role não corresponde ao hierarchy.level")
        if not _is_draw_id(root_draw_ref):
            violations.append("hierarchy.root_draw_ref deve ser um ID de desenho seguro")
        if level == 1:
            if parent_draw_ref is not None or parent_node_id is not None:
                violations.append("a raiz de hierarchy não pode declarar pai")
            if root_draw_ref != draw_id:
                violations.append("hierarchy.root_draw_ref da raiz deve ser o próprio id")
        elif level in HIERARCHY_ROLE_BY_LEVEL:
            if not _is_draw_id(parent_draw_ref):
                violations.append("desenho hierárquico descendente deve declarar parent_draw_ref")
            if not _is_numeric_id(parent_node_id):
                violations.append("desenho hierárquico descendente deve declarar parent_node_id numérico")

    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        violations.append("nodes deve ser uma lista")
        nodes = []
    node_ids: set[Any] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or not _is_numeric_id(node.get("id")):
            violations.append(f"nodes[{index}] precisa de id numérico; use label para o nome descritivo")
            continue
        if node["id"] in node_ids:
            violations.append(f"nó duplicado: {node['id']}")
        node_ids.add(node["id"])
        if not isinstance(node.get("label"), str) or not node["label"].strip():
            violations.append(f"nodes[{index}] precisa de label")
        draw_ref = node.get("draw_ref")
        if draw_ref is not None and not _is_draw_id(draw_ref):
            violations.append(f"nodes[{index}].draw_ref deve ser o ID descritivo de outro desenho")
        questions = node.get("questions", [])
        if not isinstance(questions, list):
            violations.append(f"nodes[{index}].questions deve ser uma lista")
            questions = []
        question_ids: set[int] = set()
        for question_index, question in enumerate(questions):
            prefix = f"nodes[{index}].questions[{question_index}]"
            if not isinstance(question, dict) or not _is_numeric_id(question.get("id")):
                violations.append(f"{prefix} precisa de id numérico")
                continue
            question_id = question["id"]
            if question_id in question_ids:
                violations.append(f"pergunta duplicada no nó {node['id']}: {question_id}")
            question_ids.add(question_id)
            question_type = question.get("type")
            if question_type not in QUESTION_TYPES:
                violations.append(f"{prefix}.type deve ser choice, boolean ou open")
            if not isinstance(question.get("prompt"), str) or not question["prompt"].strip():
                violations.append(f"{prefix}.prompt é obrigatório")
            if "required" in question and not isinstance(question["required"], bool):
                violations.append(f"{prefix}.required deve ser booleano")
            answer = question.get("answer")
            if question_type == "choice":
                options = question.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    violations.append(f"{prefix}.options deve conter pelo menos duas opções")
                    options = []
                option_ids: set[int] = set()
                for option_index, option in enumerate(options):
                    option_prefix = f"{prefix}.options[{option_index}]"
                    if not isinstance(option, dict) or not _is_numeric_id(option.get("id")):
                        violations.append(f"{option_prefix} precisa de id numérico")
                        continue
                    option_id = option["id"]
                    if option_id in option_ids:
                        violations.append(f"opção duplicada em {prefix}: {option_id}")
                    option_ids.add(option_id)
                    if not isinstance(option.get("label"), str) or not option["label"].strip():
                        violations.append(f"{option_prefix}.label é obrigatório")
                if answer is not None:
                    is_selected_option = _is_numeric_id(answer) and answer in option_ids
                    is_custom_answer = isinstance(answer, str)
                    if not is_selected_option and not is_custom_answer:
                        violations.append(f"{prefix}.answer deve apontar para uma opção existente ou conter uma resposta livre")
            elif question_type == "boolean":
                if "options" in question:
                    violations.append(f"{prefix} boolean não deve declarar options")
                if answer is not None and not (
                    isinstance(answer, bool) or (isinstance(answer, str) and bool(answer.strip()))
                ):
                    violations.append(f"{prefix}.answer deve ser booleano ou conter uma resposta livre")
            elif question_type == "open":
                if "options" in question:
                    violations.append(f"{prefix} open não deve declarar options")
                if answer is not None and not isinstance(answer, str):
                    violations.append(f"{prefix}.answer deve ser texto ou nulo")

        changes = node.get("changes", [])
        if not isinstance(changes, list):
            violations.append(f"nodes[{index}].changes deve ser uma lista")
            changes = []
        change_ids: set[int] = set()
        for change_index, change in enumerate(changes):
            prefix = f"nodes[{index}].changes[{change_index}]"
            if not isinstance(change, dict) or not _is_numeric_id(change.get("id")):
                violations.append(f"{prefix} precisa de id numérico")
                continue
            if change["id"] in change_ids:
                violations.append(f"alteração duplicada no nó {node['id']}: {change['id']}")
            change_ids.add(change["id"])
            if not isinstance(change.get("prompt"), str) or not change["prompt"].strip():
                violations.append(f"{prefix}.prompt é obrigatório")
            if change.get("status", "pending") not in {"pending", "in_progress", "done"}:
                violations.append(f"{prefix}.status deve ser pending, in_progress ou done")

    general_questions = payload.get("questions", [])
    if not isinstance(general_questions, list):
        violations.append("questions deve ser uma lista")
        general_questions = []
    general_question_ids: set[int] = set()
    for question_index, question in enumerate(general_questions):
        prefix = f"questions[{question_index}]"
        if not isinstance(question, dict) or not _is_numeric_id(question.get("id")):
            violations.append(f"{prefix} precisa de id numérico")
            continue
        question_id = question["id"]
        if question_id in general_question_ids:
            violations.append(f"pergunta geral duplicada: {question_id}")
        general_question_ids.add(question_id)
        question_type = question.get("type")
        if question_type not in QUESTION_TYPES:
            violations.append(f"{prefix}.type deve ser choice, boolean ou open")
        if not isinstance(question.get("prompt"), str) or not question["prompt"].strip():
            violations.append(f"{prefix}.prompt é obrigatório")
        if "required" in question and not isinstance(question["required"], bool):
            violations.append(f"{prefix}.required deve ser booleano")
        answer = question.get("answer")
        if question_type == "choice":
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                violations.append(f"{prefix}.options deve conter pelo menos duas opções")
                options = []
            option_ids: set[int] = set()
            for option_index, option in enumerate(options):
                option_prefix = f"{prefix}.options[{option_index}]"
                if not isinstance(option, dict) or not _is_numeric_id(option.get("id")):
                    violations.append(f"{option_prefix} precisa de id numérico")
                    continue
                option_id = option["id"]
                if option_id in option_ids:
                    violations.append(f"opção duplicada em {prefix}: {option_id}")
                option_ids.add(option_id)
                if not isinstance(option.get("label"), str) or not option["label"].strip():
                    violations.append(f"{option_prefix}.label é obrigatório")
            if answer is not None and not (_is_numeric_id(answer) and answer in option_ids) and not isinstance(answer, str):
                violations.append(f"{prefix}.answer deve apontar para uma opção existente ou conter uma resposta livre")
        elif question_type == "boolean":
            if "options" in question:
                violations.append(f"{prefix} boolean não deve declarar options")
            if answer is not None and not (isinstance(answer, bool) or (isinstance(answer, str) and bool(answer.strip()))):
                violations.append(f"{prefix}.answer deve ser booleano ou conter uma resposta livre")
        elif question_type == "open":
            if "options" in question:
                violations.append(f"{prefix} open não deve declarar options")
            if answer is not None and not isinstance(answer, str):
                violations.append(f"{prefix}.answer deve ser texto ou nulo")

    groups = payload.get("groups", [])
    if not isinstance(groups, list):
        violations.append("groups deve ser uma lista")
        groups = []
    group_ids: set[int] = set()
    for index, group in enumerate(groups):
        if not isinstance(group, dict) or not _is_numeric_id(group.get("id")):
            violations.append(f"groups[{index}] precisa de id numérico")
            continue
        group_ids.add(group["id"])
    for node in nodes:
        if isinstance(node, dict) and node.get("group") is not None and node["group"] not in group_ids:
            violations.append(f"grupo inexistente: {node['group']}")

    edges = payload.get("edges", [])
    if not isinstance(edges, list):
        violations.append("edges deve ser uma lista")
        edges = []
    edge_ids: set[Any] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            violations.append(f"edges[{index}] deve ser um objeto")
            continue
        if "source" in edge or "target" in edge:
            violations.append(f"edges[{index}] deve usar from/to; source/target não fazem parte do schema")
        if "from" not in edge or "to" not in edge:
            violations.append(f"edges[{index}] deve declarar as chaves from e to")
        source, target = edge.get("from"), edge.get("to")
        if "from" in edge and "to" in edge and (source not in node_ids or target not in node_ids):
            violations.append(f"relação {index} aponta para nó que não existe")
        edge_id = edge.get("id")
        if not _is_numeric_id(edge_id):
            violations.append(f"edges[{index}].id deve ser numérico")
            continue
        if edge_id in edge_ids:
            violations.append(f"relação duplicada: {edge_id}")
        edge_ids.add(edge_id)
        if edge.get("condition") not in EDGE_CONDITIONS:
            violations.append(f"edges[{index}].condition deve ser um código: 1 (então), 2 (ou) ou 3 (se)")

    flows = payload.get("flows", [])
    if not isinstance(flows, list):
        violations.append("flows deve ser uma lista")
        flows = []
    for flow_index, flow in enumerate(flows):
        if not isinstance(flow, dict) or not _is_numeric_id(flow.get("id")):
            violations.append(f"flows[{flow_index}] precisa de id numérico")
            continue
        if not isinstance(flow.get("steps", []), list):
            violations.append(f"flows[{flow_index}] deve possuir steps como lista")
            continue
        for step_index, step in enumerate(flow["steps"]):
            if not isinstance(step, dict) or step.get("node") not in node_ids:
                violations.append(f"flows[{flow_index}].steps[{step_index}] aponta para nó que não existe")
    return violations


def _analysis_text(value: Any) -> str:
    """Normaliza texto para comparar estruturas sem diferenças cosméticas."""
    if not isinstance(value, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", without_accents.lower())).strip()


def _analysis_group_labels(payload: dict[str, Any]) -> dict[Any, str]:
    """Mapeia grupos para rótulos estáveis, ignorando IDs internos."""
    return {
        group.get("id"): _analysis_text(group.get("label")) or "group"
        for group in payload.get("groups", [])
        if isinstance(group, dict)
    }


def _analysis_node_tokens(payload: dict[str, Any]) -> dict[Any, str]:
    """Cria tokens de nó baseados no conteúdo, não no ID numérico."""
    groups = _analysis_group_labels(payload)
    tokens: dict[Any, str] = {}
    for node in payload.get("nodes", []):
        if not isinstance(node, dict):
            continue
        label = _analysis_text(node.get("label")) or "node"
        group = groups.get(node.get("group"), "")
        tokens[node.get("id")] = f"{label}|{group}"
    return tokens


def _analysis_edge_tokens(payload: dict[str, Any], node_tokens: dict[Any, str]) -> list[str]:
    """Representa conexões com endpoints sem depender dos IDs internos."""
    tokens = []
    for edge in payload.get("edges", []):
        if not isinstance(edge, dict):
            continue
        source = node_tokens.get(edge.get("from"), "unknown")
        target = node_tokens.get(edge.get("to"), "unknown")
        tokens.append("|".join((source, target, _analysis_text(edge.get("kind")), str(edge.get("condition", "")), _analysis_text(edge.get("label")))))
    return sorted(tokens)


def _analysis_flow_signature(payload: dict[str, Any], flow: dict[str, Any]) -> dict[str, Any]:
    """Calcula fingerprint lógico de um fluxo sem IDs, posições ou estilos."""
    node_tokens = _analysis_node_tokens(payload)
    steps = flow.get("steps", []) if isinstance(flow.get("steps", []), list) else []
    step_nodes = [node_tokens.get(step.get("node"), "unknown") for step in steps if isinstance(step, dict)]
    edge_by_pair = {
        (edge.get("from"), edge.get("to")): edge
        for edge in payload.get("edges", [])
        if isinstance(edge, dict)
    }
    connections = []
    for first, second in zip(steps, steps[1:]):
        if not isinstance(first, dict) or not isinstance(second, dict):
            continue
        edge = edge_by_pair.get((first.get("node"), second.get("node")))
        if edge is None:
            edge = edge_by_pair.get((second.get("node"), first.get("node")))
        connections.append(
            "|".join((
                _analysis_text(edge.get("kind")) if edge else "unresolved",
                str(edge.get("condition", "")) if edge else "",
                _analysis_text(edge.get("label")) if edge else "",
            ))
        )
    return {
        "title": _analysis_text(flow.get("title") or flow.get("label")),
        "nodes": step_nodes,
        "connections": connections,
    }


def _analysis_draw_signature(payload: dict[str, Any]) -> dict[str, Any]:
    """Calcula fingerprint lógico do desenho sem metadados de apresentação."""
    node_tokens = _analysis_node_tokens(payload)
    nodes = sorted(
        (token, _analysis_text(node.get("description")))
        for node in payload.get("nodes", [])
        if isinstance(node, dict)
        for token in [node_tokens.get(node.get("id"), "unknown")]
    )
    flows = [
        _analysis_flow_signature(payload, flow)
        for flow in payload.get("flows", [])
        if isinstance(flow, dict)
    ]
    flows.sort(key=_analysis_fingerprint)
    return {
        "title": _analysis_text(payload.get("title")),
        "subtitle": _analysis_text(payload.get("subtitle")),
        "kind": _analysis_text(payload.get("kind")),
        "groups": sorted(_analysis_text(group.get("label")) for group in payload.get("groups", []) if isinstance(group, dict)),
        "nodes": nodes,
        "edges": _analysis_edge_tokens(payload, node_tokens),
        "flows": flows,
    }


def _analysis_fingerprint(value: Any) -> str:
    """Serializa uma estrutura canônica para igualdade e similaridade estáveis."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _analysis_documents(root: Path) -> list[tuple[str, dict[str, Any]]]:
    """Carrega desenhos existentes para comparação sem interromper a criação."""
    try:
        entries = read_draw_index(root).get("draws", [])
    except ValueError:
        return []
    documents: list[tuple[str, dict[str, Any]]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not _is_draw_id(entry.get("id")):
            continue
        path = draw_directory(root) / f"{entry['id']}.json"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(document, dict):
            documents.append((entry["id"], document))
    return documents


def _analysis_entity(kind: str, label: str, source: str, signature: Any) -> dict[str, Any]:
    """Monta entidade comparável e legível no diagnóstico do Draw."""
    return {
        "kind": kind,
        "label": label or "(sem título)",
        "source": source,
        "normalized_label": _analysis_text(label),
        "signature": _analysis_fingerprint(signature),
    }


def _analysis_entities(draw_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai desenho e fluxos do payload em entidades comparáveis."""
    entities = [_analysis_entity("draw", str(payload.get("title", "")), draw_id, _analysis_draw_signature(payload))]
    for flow in payload.get("flows", []):
        if isinstance(flow, dict):
            label = str(flow.get("title") or flow.get("label") or "")
            entities.append(_analysis_entity("flow", label, f"{draw_id}:flow:{flow.get('id')}", _analysis_flow_signature(payload, flow)))
    return entities


def _analysis_subflow_entities(draw_id: str, payload: dict[str, Any], documents: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Extrai títulos e fingerprints dos subfluxos referenciados por nós."""
    entities = []
    for node in payload.get("nodes", []):
        if not isinstance(node, dict) or node.get("draw_ref") not in documents:
            continue
        child_id = node["draw_ref"]
        child = documents[child_id]
        entities.append(_analysis_entity("subflow", str(child.get("title", "")), f"{draw_id}:node:{node.get('id')}->{child_id}", _analysis_draw_signature(child)))
    return entities


def _analysis_isolated_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Identifica nós sem qualquer aresta incidente, em qualquer direção."""
    nodes = [node for node in payload.get("nodes", []) if isinstance(node, dict)]
    node_ids = {node.get("id") for node in nodes}
    degrees = {node_id: 0 for node_id in node_ids}
    for edge in payload.get("edges", []):
        if not isinstance(edge, dict):
            continue
        for endpoint in (edge.get("from"), edge.get("to")):
            if endpoint in degrees:
                degrees[endpoint] += 1
    return [
        {"id": node.get("id"), "label": node.get("label", ""), "degree": degrees.get(node.get("id"), 0)}
        for node in nodes
        if degrees.get(node.get("id"), 0) == 0
    ]


def _analysis_warning(
    kind: str,
    rule: str,
    left: dict[str, Any],
    right: dict[str, Any],
    similarity: float,
    seen: set[tuple[str, str, str]],
) -> dict[str, Any] | None:
    """Cria um warning estrutural uma única vez para um par de entidades."""
    pair = tuple(sorted((left["source"], right["source"])))
    marker = (kind, rule, "|".join(pair))
    if marker in seen:
        return None
    seen.add(marker)
    return {
        "kind": rule,
        "severity": "warning",
        "structure": kind,
        "similarity": round(similarity, 4),
        "left": {key: left[key] for key in ("source", "label")},
        "right": {key: right[key] for key in ("source", "label")},
        "evidence": "estrutura lógica repetida" if similarity == 1.0 else "estrutura lógica muito próxima",
        "message": "suspeita de repetição ou geração automatizada; revisar personalização por caso de uso",
    }


def _analysis_entity_pairs(
    current_entities: list[dict[str, Any]],
    other_entities: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Monta pares: desenhos atuais contra existentes; fluxos contra todos."""
    pairs = []
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for entity in [*current_entities, *other_entities]:
        by_kind.setdefault(entity["kind"], []).append(entity)
    for kind, entities in by_kind.items():
        current = [entity for entity in current_entities if entity["kind"] == kind]
        candidates = other_entities if kind == "draw" else entities
        for left in current:
            for right in candidates:
                if left["source"] != right["source"]:
                    pairs.append((left, right))
    return pairs


def _analysis_compare_entities(
    current_entities: list[dict[str, Any]],
    other_entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compara entidades e produz somente diagnósticos não bloqueantes."""
    warnings = []
    seen: set[tuple[str, str, str]] = set()
    for left, right in _analysis_entity_pairs(current_entities, other_entities):
        if left["normalized_label"] and left["normalized_label"] == right["normalized_label"]:
            warning = _analysis_warning(left["kind"], "duplicate_title", left, right, 1.0, seen)
            if warning:
                warnings.append(warning)
        similarity = SequenceMatcher(None, left["signature"], right["signature"]).ratio()
        if similarity >= DRAW_ANALYSIS_SIMILARITY_THRESHOLD:
            rule = "duplicate_structure" if similarity == 1.0 else "similar_structure"
            warning = _analysis_warning(left["kind"], rule, left, right, similarity, seen)
            if warning:
                warnings.append(warning)
    return sorted(warnings, key=lambda item: (item["kind"], item["structure"], item["left"]["source"], item["right"]["source"]))


def analyze_draw_structure(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Analisa conectividade, repetição e similaridade sem bloquear por repetição."""
    draw_id = str(payload.get("id", "(novo desenho)"))
    isolated_nodes = _analysis_isolated_nodes(payload)
    existing = {
        existing_id: document
        for existing_id, document in _analysis_documents(root)
        if existing_id != draw_id
    }
    current_entities = _analysis_entities(draw_id, payload)
    current_entities.extend(_analysis_subflow_entities(draw_id, payload, {**existing, draw_id: payload}))
    other_entities: list[dict[str, Any]] = []
    for existing_id, document in existing.items():
        other_entities.extend(_analysis_entities(existing_id, document))
        other_entities.extend(_analysis_subflow_entities(existing_id, document, existing))

    warnings = _analysis_compare_entities(current_entities, other_entities)
    return {
        "status": "warning" if warnings else "passed",
        "isolated_nodes": isolated_nodes,
        "warnings": warnings,
        "summary": {
            "isolated_nodes": len(isolated_nodes),
            "warnings": len(warnings),
            "exact_duplicates": sum(1 for warning in warnings if warning["similarity"] == 1.0),
            "near_duplicates": sum(1 for warning in warnings if warning["similarity"] < 1.0),
        },
    }


def _is_empty_or_unnamed_symbol(symbol: Any) -> bool:
    """Verifica se o símbolo do nó está ausente, vazio ou possui um nome genérico sem referência a uma função."""
    if not isinstance(symbol, str):
        return True
    cleaned = symbol.strip().lower()
    return not cleaned or cleaned in UNNAMED_SYMBOL_PATTERNS


def _extract_node_symbols(node: dict[str, Any]) -> list[str]:
    """Extrai nomes de símbolos válidos (não vazios e não genéricos) de um nó."""
    references = node.get("code_refs")
    if not isinstance(references, list):
        return []
    symbols = []
    for ref in references:
        if isinstance(ref, dict):
            sym = ref.get("symbol") or ref.get("qualified_name")
            if isinstance(sym, str) and not _is_empty_or_unnamed_symbol(sym):
                symbols.append(sym.strip())
    return symbols


def _has_code_reference(node: dict[str, Any]) -> bool:
    """Confere se o nó possui ao menos uma referência estrutural válida."""
    return bool(_extract_node_symbols(node))


def analyze_draw_contract(payload: dict[str, Any], source: str = "(novo desenho)") -> list[dict[str, Any]]:
    """Produz warnings de contratos estáticos específicos da hierarquia Draw e da qualidade dos símbolos dos nós."""
    draw_id = str(payload.get("id", "(novo desenho)"))
    findings: list[dict[str, Any]] = []

    hierarchy = payload.get("hierarchy")
    level = hierarchy.get("level") if isinstance(hierarchy, dict) else None

    if level in (2, 3, 4):
        rule_map = {
            2: DRAW_LEVEL2_CODE_REF_RULE,
            3: DRAW_LEVEL3_CODE_REF_RULE,
            4: DRAW_LEVEL4_CODE_REF_RULE,
        }
        rule_name = rule_map[level]
        for node in payload.get("nodes", []):
            if not isinstance(node, dict) or _has_code_reference(node):
                continue
            node_id = node.get("id")
            findings.append({
                "kind": rule_name,
                "rule": rule_name,
                "severity": "blocking",
                "file": source,
                "draw_id": draw_id,
                "node_id": node_id,
                "value": 0,
                "limit": 1,
                "evidence": f"nó {node_id!r} não possui code_refs",
                "source": "builtin_draw_contract",
            })

    for node in payload.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        references = node.get("code_refs")
        if isinstance(references, list):
            for ref in references:
                if isinstance(ref, dict):
                    sym = ref.get("symbol") or ref.get("qualified_name")
                    if _is_empty_or_unnamed_symbol(sym):
                        display_sym = repr(sym) if sym is not None else "ausente"
                        findings.append({
                            "kind": DRAW_EMPTY_NODE_SYMBOL_RULE,
                            "rule": DRAW_EMPTY_NODE_SYMBOL_RULE,
                            "severity": "blocking",
                            "file": source,
                            "draw_id": draw_id,
                            "node_id": node_id,
                            "value": 0,
                            "limit": 1,
                            "evidence": f"nó {node_id!r} possui símbolo sem nome ou vazio em code_refs: {display_sym}",
                            "source": "builtin_draw_contract",
                        })

    symbol_node_map: dict[str, list[Any]] = {}
    for node in payload.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        valid_symbols = set(_extract_node_symbols(node))
        for sym in valid_symbols:
            symbol_node_map.setdefault(sym, []).append(node_id)

    for sym, node_ids in sorted(symbol_node_map.items()):
        if len(node_ids) > 4:
            findings.append({
                "kind": DRAW_DUPLICATE_NODE_SYMBOL_RULE,
                "rule": DRAW_DUPLICATE_NODE_SYMBOL_RULE,
                "severity": "warning",
                "file": source,
                "draw_id": draw_id,
                "symbol": sym,
                "node_ids": node_ids,
                "value": len(node_ids),
                "limit": 4,
                "evidence": f"símbolo {sym!r} aparece mais de 4 vezes ({len(node_ids)} ocorrências) nos nós {node_ids}",
                "source": "builtin_draw_contract",
            })

    return findings



def scan_draw_contracts(root: Path) -> list[dict[str, Any]]:
    """Analisa todos os desenhos persistidos sem transformar warning em bloqueio."""
    findings = []
    directory = draw_directory(root)
    if not directory.is_dir():
        return findings
    for path in sorted(directory.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            findings.extend(analyze_draw_contract(payload, path.relative_to(root).as_posix()))
    return findings


def collect_draw_symbols(root: Path) -> dict[str, Any]:
    """Lista símbolos declarados nos nós implementáveis sem executar suítes.
    Mantém a verificação rápida do CLI separada da análise estática completa e do backlog.
    """
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    directory = draw_directory(root)
    if not directory.is_dir():
        return {
            "status": "passed",
            "draws": [],
            "errors": [],
            "summary": {"nodes": 0, "associated": 0, "missing": 0, "draws": 0},
        }

    draw_count = 0
    for path in sorted(directory.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            errors.append({"file": path.relative_to(root).as_posix(), "reason": error.__class__.__name__})
            continue
        if not isinstance(payload, dict):
            errors.append({"file": path.relative_to(root).as_posix(), "reason": "document_not_object"})
            continue
        hierarchy = payload.get("hierarchy")
        level = hierarchy.get("level") if isinstance(hierarchy, dict) else None
        if level not in (2, 3, 4):
            continue
        draw_count += 1
        for node in payload.get("nodes", []):
            if not isinstance(node, dict):
                continue
            symbols = _extract_node_symbols(node)
            entries.append({
                "draw_id": payload.get("id", path.stem),
                "file": path.relative_to(root).as_posix(),
                "level": level,
                "node_id": node.get("id"),
                "label": node.get("label", ""),
                "status": "associated" if symbols else "missing",
                "symbols": symbols,
            })

    missing = sum(item["status"] == "missing" for item in entries)
    return {
        "status": "blocked" if missing or errors else "passed",
        "draws": entries,
        "errors": errors,
        "summary": {
            "nodes": len(entries),
            "associated": len(entries) - missing,
            "missing": missing,
            "draws": draw_count,
        },
    }


def validate_hierarchy_parent(root: Path, payload: dict[str, Any]) -> list[str]:
    """Confere o vínculo pai-filho de um desenho hierárquico persistido.
    Exige que o pai exista, declare a mesma raiz e exponha a cápsula apontada pelo filho.
    """
    hierarchy = payload.get("hierarchy")
    if not isinstance(hierarchy, dict) or hierarchy.get("level") == 1:
        return []
    parent_id = hierarchy.get("parent_draw_ref")
    parent_node_id = hierarchy.get("parent_node_id")
    parent_path = draw_directory(root) / f"{parent_id}.json"
    if not parent_path.is_file():
        return [f"hierarchy.parent_draw_ref não encontrado: {parent_id}"]
    try:
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [f"desenho pai inválido: {parent_id}"]
    if not isinstance(parent, dict):
        return [f"desenho pai inválido: {parent_id}"]
    parent_hierarchy = parent.get("hierarchy")
    if not isinstance(parent_hierarchy, dict):
        return [f"desenho pai sem hierarchy: {parent_id}"]
    if parent_hierarchy.get("root_draw_ref") != hierarchy.get("root_draw_ref"):
        return ["hierarchy.root_draw_ref diverge entre pai e filho"]
    parent_level = parent_hierarchy.get("level")
    child_level = hierarchy.get("level")
    if not isinstance(parent_level, int) or not isinstance(child_level, int) or parent_level >= child_level:
        return ["hierarchy deve avançar para um nível descendente"]
    parent_node = next((node for node in parent.get("nodes", []) if isinstance(node, dict) and node.get("id") == parent_node_id), None)
    if parent_node is None:
        return [f"hierarchy.parent_node_id não encontrado no pai: {parent_node_id}"]
    if parent_node.get("draw_ref") != payload.get("id"):
        return ["o nó pai deve apontar para o filho com draw_ref"]
    return []


def _validate_index_metadata(entry: dict[str, Any], payload: dict[str, Any], draw_id: str, prefix: str) -> list[str]:
    """Compara os contadores leves do índice com o JSON carregado.
    Impede que a biblioteca exiba uma chave antiga que não corresponda ao documento atual.
    """
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    counts = {
        "node_count": len(nodes) if isinstance(nodes, list) else None,
        "edge_count": len(edges) if isinstance(edges, list) else None,
        "subdraw_count": sum(1 for node in nodes if isinstance(node, dict) and node.get("draw_ref") is not None)
        if isinstance(nodes, list) else None,
    }
    return [
        f"{prefix}.{field} diverge do desenho {draw_id} (esperado {expected})"
        for field, expected in counts.items()
        if entry.get(field) != expected
    ]


def _load_indexed_draw(root: Path, entry_index: int, entry: Any) -> tuple[list[str], str | None, dict[str, Any] | None]:
    """Carrega e valida um desenho anunciado pelo índice.
    Retorna violações, ID válido e payload para as verificações cruzadas do workspace.
    """
    prefix = f".looper/draws/index.json draws[{entry_index}]"
    if not isinstance(entry, dict):
        return [f"{prefix} deve ser um objeto"], None, None
    draw_id = entry.get("id")
    if not _is_draw_id(draw_id):
        return [f"{prefix}.id deve ser um ID de desenho seguro"], None, None
    expected_file = f"{draw_id}.json"
    violations = [] if entry.get("file") == expected_file else [f"{prefix}.file deve ser {expected_file}"]
    path = draw_directory(root) / expected_file
    if not path.is_file():
        return [*violations, f"{prefix} aponta para desenho inexistente: {draw_id}"], draw_id, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [*violations, f"{expected_file}: JSON inválido ({error.__class__.__name__})"], draw_id, None
    if not isinstance(payload, dict):
        return [*violations, f"{expected_file}: desenho deve ser um objeto JSON"], draw_id, None
    violations.extend(
        [f"{expected_file}: {item}" for item in validate_draw_payload(payload)]
        + [f"{expected_file}: {item}" for item in validate_hierarchy_parent(root, payload)]
        + _validate_index_metadata(entry, payload, draw_id, prefix)
    )
    if payload.get("id") != draw_id:
        violations.append(f"{expected_file}: id do JSON diverge do índice ({draw_id})")
    return violations, draw_id, payload


def validate_draw_workspace(root: Path) -> list[str]:
    """Valida todos os desenhos e referências antes de iniciar o viewer.
    Detecta schema incompatível, índice desatualizado e cápsulas quebradas antes de qualquer fetch HTTP.
    """
    draws_path = draw_directory(root)
    if not draws_path.is_dir():
        return []
    try:
        entries = read_draw_index(root).get("draws", [])
    except ValueError as error:
        return [f".looper/draws/index.json: {error}"]

    violations: list[str] = []
    indexed_ids: set[str] = set()
    documents: dict[str, dict[str, Any]] = {}
    for entry_index, entry in enumerate(entries):
        entry_violations, draw_id, payload = _load_indexed_draw(root, entry_index, entry)
        violations.extend(entry_violations)
        if draw_id is None or draw_id in indexed_ids:
            if draw_id in indexed_ids:
                violations.append(f".looper/draws/index.json draws[{entry_index}].id duplicado: {draw_id}")
            continue
        indexed_ids.add(draw_id)
        if payload is not None:
            documents[draw_id] = payload

    file_ids = {path.stem for path in draws_path.glob("*.json") if path.name != "index.json"}
    violations.extend(f".looper/draws/{draw_id}.json não está presente no índice" for draw_id in sorted(file_ids - indexed_ids))
    available_ids = set(documents)
    for draw_id, payload in documents.items():
        for node_index, node in enumerate(payload.get("nodes", [])):
            if isinstance(node, dict) and node.get("draw_ref") is not None and node["draw_ref"] not in available_ids:
                violations.append(f"{draw_id}.json nodes[{node_index}].draw_ref aponta para desenho inexistente: {node['draw_ref']}")
    return violations


def ensure_draw_workspace(root: Path, include_example: bool = False) -> list[Path]:
    """Cria somente o armazenamento dos desenhos no projeto.
    Remove o viewer legado e opcionalmente instala um desenho demonstrativo.
    """
    looper_path = root / ".looper"
    draws_path = draw_directory(root)
    facts_path = facts_directory(root)
    created: list[Path] = []
    for directory in (looper_path, draws_path, facts_path):
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
    viewer = root / LEGACY_DRAW_VIEWER
    if viewer.exists():
        viewer.unlink()
        created.append(viewer)
    index = draw_index_path(root)
    if not index.exists():
        index.write_text(json.dumps({"version": DRAW_VERSION, "draws": []}, indent=2) + "\n", encoding="utf-8")
        created.append(index)
    if include_example:
        created.extend(ensure_example_draw(root))
    return created


def ensure_example_draw(root: Path) -> list[Path]:
    """Garante um JSON demonstrativo idempotente no projeto inicializado.
    Lê o fixture empacotado e usa o mesmo contrato de validação e índice dos desenhos reais.
    """
    if not DRAW_EXAMPLE_TEMPLATE.is_file():
        raise RuntimeError("fixture do desenho de exemplo não está instalado no pacote")
    try:
        payload = json.loads(DRAW_EXAMPLE_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("fixture do desenho de exemplo está inválido") from error
    example_id = payload.get("id") if isinstance(payload, dict) else None
    index = read_draw_index(root)
    example_path = draw_directory(root) / f"{example_id}.json"
    if any(str(entry.get("id")) == str(example_id) for entry in index["draws"]) and example_path.exists():
        return []
    return [create_draw(root, payload)]


def read_draw_index(root: Path) -> dict[str, Any]:
    """Lê o índice leve de desenhos ou retorna uma lista vazia.
    Nunca carrega os JSONs individuais nesta operação de navegação.
    """
    index_path = draw_index_path(root)
    if not index_path.exists():
        return {"version": DRAW_VERSION, "draws": []}
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"índice de desenhos inválido: {error.__class__.__name__}") from error
    if not isinstance(index, dict) or not isinstance(index.get("draws"), list):
        raise ValueError("índice de desenhos deve conter draws como lista")
    return index


def find_addressed_questions(
    root: Path,
    tag: str | None = None,
    *,
    answered: bool = False,
) -> list[dict[str, Any]]:
    """Localiza marcações endereçadas respeitando tags e estado da resposta.

    O filtro padrão é o trabalho acionável do agente e do desenvolvedor.
    Observações respondidas só entram quando ``tag=obs`` e ``answered=True``;
    isso evita consumir contexto humano duas vezes por acidente.
    """
    clean_tag = (tag or "").lower().lstrip("@").strip()
    if not clean_tag or clean_tag in ("all", "default"):
        pattern = r"@(looper|obs|developer)"
    elif clean_tag in ("dev", "developer"):
        pattern = r"@developer"
    elif clean_tag == "obs":
        pattern = r"@obs"
    elif clean_tag == "looper":
        pattern = r"@looper"
    else:
        pattern = rf"@{re.escape(clean_tag)}"

    questions: list[dict[str, Any]] = []
    for entry in read_draw_index(root).get("draws", []):
        draw_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(draw_id, str):
            continue
        document = read_draw(root, draw_id)
        for node in document.get("nodes", []):
            if not isinstance(node, dict):
                continue
            for question in node.get("questions", []):
                if not isinstance(question, dict):
                    continue
                prompt = question.get("prompt")
                answer = question.get("answer")
                is_answered = _answer_is_filled(answer)
                # O comando canônico de pendências não consome @obs. Para
                # inspeção explícita, --tag obs --answered recupera a dupla.
                include = is_answered if answered else not is_answered
                if (
                    isinstance(prompt, str)
                    and re.search(pattern, prompt, re.IGNORECASE)
                    and include
                    and not (not clean_tag and re.search(r"@obs", prompt, re.IGNORECASE))
                ):
                    node_code_refs = deepcopy(node.get("code_refs", []))
                    symbols = []
                    source_dependencies = []
                    for reference in node_code_refs:
                        if isinstance(reference, str):
                            reference = {"symbol": reference}
                        if not isinstance(reference, dict):
                            continue
                        symbol = reference.get("qualified_name") or reference.get("symbol")
                        if isinstance(symbol, str) and symbol.strip():
                            symbols.append(symbol.strip())
                        dependencies = reference.get("source_dependencies", [])
                        if isinstance(dependencies, list):
                            source_dependencies.extend(
                                item.strip() for item in dependencies if isinstance(item, str) and item.strip()
                            )
                    questions.append({
                        "draw_id": draw_id,
                        "draw_title": document.get("title", draw_id),
                        "draw_file": f".looper/draws/{draw_id}.json",
                        "node_id": node.get("id"),
                        "node_label": node.get("label", ""),
                        "node_code_refs": node_code_refs,
                        "symbols": list(dict.fromkeys(symbols)),
                        "source_dependencies": list(dict.fromkeys(source_dependencies)),
                        "question_id": question.get("id"),
                        "type": question.get("type"),
                        "question": prompt,
                        "prompt": prompt,
                        "answer": answer,
                        "destination": "node",
                    })
    # Perguntas gerais criadas por uma skill de arquitetura pertencem ao
    # painel de melhorias e não a um nó visual.
    for entry in read_draw_index(root).get("draws", []):
        draw_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(draw_id, str):
            continue
        document = read_draw(root, draw_id)
        for node, node_id, question in _draw_question_entries({"questions": document.get("questions", [])}):
            if node_id is not None:
                continue
            prompt = question.get("prompt")
            answer = question.get("answer")
            is_answered = _answer_is_filled(answer)
            if not isinstance(prompt, str) or not re.search(pattern, prompt, re.IGNORECASE):
                continue
            if is_answered != answered:
                continue
            if not clean_tag and re.search(r"@obs", prompt, re.IGNORECASE):
                continue
            questions.append({
                "draw_id": draw_id,
                "draw_title": document.get("title", draw_id),
                "draw_file": f".looper/draws/{draw_id}.json",
                "node_id": None,
                "node_label": None,
                "node_code_refs": [],
                "symbols": [],
                "source_dependencies": [],
                "question_id": question.get("id"),
                "type": question.get("type"),
                "question": prompt,
                "prompt": prompt,
                "answer": answer,
                "destination": "improvement",
            })
    return questions


def format_draw_answers(questions: list[dict[str, Any]], tag: str | None = None) -> str:
    """Apresenta perguntas e observações do Draw agrupadas em uma leitura humana.
    Inclui o nó, cada símbolo associado, arquivos e limitações sem imprimir JSON bruto.
    """
    clean_tag = (tag or "").lower().lstrip("@").strip()
    if not questions:
        if clean_tag == "looper":
            return "Nenhuma pergunta @looper pendente."
        if clean_tag == "obs":
            return "Nenhuma anotação @obs pendente."
        return "Nenhuma pergunta ou observação pendente."

    grouped: dict[str, list[dict[str, Any]]] = {}
    for question in questions:
        draw_id = str(question.get("draw_id", "desenho desconhecido"))
        grouped.setdefault(draw_id, []).append(question)

    if clean_tag == "obs":
        header = "Observações (@obs) dos Draws"
    elif clean_tag == "looper":
        header = "Perguntas do Draw Interaction"
    else:
        header = "Perguntas e Observações dos Draws"

    lines = [header, ""]
    for draw_id, draw_questions in grouped.items():
        draw_title = draw_questions[0].get("draw_title") or draw_id
        lines.extend([f"Draw: {draw_title} ({draw_id})", ""])
        for index, question in enumerate(draw_questions):
            raw_prompt = str(question.get("prompt") or question.get("question") or "").strip()
            if re.search(r"@obs", raw_prompt, re.IGNORECASE):
                label_prefix = "Observação"
            elif re.search(r"@developer", raw_prompt, re.IGNORECASE):
                label_prefix = "Ação do Desenvolvedor"
            else:
                label_prefix = "Pergunta"

            prompt = re.sub(r"@(looper|obs|developer)\s*", "", raw_prompt, count=1, flags=re.IGNORECASE).strip()
            node_label = question.get("node_label") or "Nó sem nome"
            node_id = question.get("node_id")
            question_id = question.get("question_id")
            lines.extend([
                f"{label_prefix}: {prompt}",
                f"ID da pergunta: {question_id}",
                f"Nó: {node_label} (id {node_id})",
            ])

            references = question.get("node_code_refs")
            references = references if isinstance(references, list) else []
            valid_references = []
            for reference in references:
                if not isinstance(reference, dict):
                    continue
                symbol = reference.get("qualified_name") or reference.get("symbol")
                if not isinstance(symbol, str) or not symbol.strip():
                    continue
                valid_references.append((symbol.strip(), reference.get("file")))
            if valid_references:
                for symbol, file in valid_references:
                    lines.append(f"Símbolo associado ao nó: {symbol}")
                    if isinstance(file, str) and file.strip():
                        lines.append(f"Arquivo: {file.strip()}")
                lines.append("Evidências: referência(s) registrada(s) no próprio nó.")
                lines.append("Limitações: nenhuma limitação relevante encontrada.")
            else:
                lines.append("Símbolo associado ao nó: não comprovado")
                lines.append("Evidências: o nó ainda não possui um símbolo válido em code_refs.")
                lines.append("Limitações: a associação precisa ser investigada antes de concluir a resposta.")
            lines.append("Status: aguardando investigação do Draw Interaction.")
            if index < len(draw_questions) - 1:
                lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip()


def _atomic_write(path: Path, content: str) -> None:
    """Escreve um arquivo por substituição atômica no mesmo diretório.
    Evita deixar JSON parcial quando o processo é interrompido durante a gravação.
    """
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _strip_answered_tags(nodes: list[dict]) -> list[dict]:
    """Remove marcações de perguntas que já foram respondidas."""
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for question in node.get("questions", []):
            if not isinstance(question, dict):
                continue
            answer = question.get("answer")
            is_answered = answer is not None and (not isinstance(answer, str) or bool(answer.strip()))
            if is_answered:
                prompt = question.get("prompt")
                if isinstance(prompt, str):
                    prompt = re.sub(r'@(?:Looper|developer)\s*', '', prompt, flags=re.IGNORECASE)
                    question["prompt"] = prompt.strip()
    return nodes


def _strip_answered_question_tags(questions: list[dict]) -> list[dict]:
    """Remove somente tags de ação após resposta; @obs exige consumo explícito."""
    for question in questions:
        if not isinstance(question, dict) or not _answer_is_filled(question.get("answer")):
            continue
        prompt = question.get("prompt")
        if isinstance(prompt, str):
            question["prompt"] = re.sub(r'@(?:Looper|developer)\s*', '', prompt, flags=re.IGNORECASE).strip()
    return questions


def consume_observation(root: Path, draw_id: str, question_id: int, node_id: int | None = None) -> dict[str, Any]:
    """Recupera uma observação respondida e remove apenas a menção ``@obs``.

    A resposta permanece no histórico do Draw; o retorno contém a pergunta e
    a resposta para o agente incorporar ao contexto antes da remoção.
    """
    document = read_draw(root, draw_id)
    selected: dict[str, Any] | None = None
    for node, current_node_id, question in _draw_question_entries(document):
        if current_node_id != node_id or question.get("id") != question_id:
            continue
        prompt = question.get("prompt")
        if not isinstance(prompt, str) or not re.search(r"@obs", prompt, re.IGNORECASE):
            raise ValueError("a pergunta indicada não possui @obs")
        if not _answer_is_filled(question.get("answer")):
            raise ValueError("a observação precisa estar respondida antes do consumo")
        selected = {"draw_id": draw_id, "node_id": node_id, "question_id": question_id, "prompt": prompt, "answer": question.get("answer")}
        question["prompt"] = re.sub(r"@obs\s*", "", prompt, count=1, flags=re.IGNORECASE).strip()
        break
    if selected is None:
        raise ValueError("observação não encontrada")
    create_draw(root, document)
    return selected


def create_draw(root: Path, payload: dict[str, Any], *, allow_disconnected_nodes: bool = False) -> Path:
    """Valida e grava um desenho JSON, atualizando somente o índice leve.
    Sobrescreve o mesmo ID de forma atômica e nunca produz HTML individual.

    A CLI mantém a regra de conectividade por padrão. O editor visual pode
    gravar um rascunho durante uma edição estrutural (por exemplo, depois de
    excluir um nó e antes de religar seus vizinhos), mas continua sujeito a
    toda a validação de schema e referências.
    """
    logical_payload = logical_draw_payload(payload)
    if isinstance(logical_payload.get("nodes"), list):
        logical_payload["nodes"] = _strip_answered_tags(logical_payload["nodes"])
    if isinstance(logical_payload.get("questions"), list):
        logical_payload["questions"] = _strip_answered_question_tags(logical_payload["questions"])
    violations = validate_draw_payload(logical_payload)
    if violations:
        raise ValueError("Desenho inválido: " + "; ".join(violations))
    structural_analysis = analyze_draw_structure(root, logical_payload)
    if structural_analysis["isolated_nodes"] and not allow_disconnected_nodes:
        isolated = ", ".join(
            f"id={node['id']} label={node['label']!r}"
            for node in structural_analysis["isolated_nodes"]
        )
        raise ValueError(f"Desenho inválido: nó(s) sem conexão: {isolated}")
    ensure_draw_workspace(root)
    hierarchy_violations = validate_hierarchy_parent(root, logical_payload)
    if hierarchy_violations:
        raise ValueError("Desenho inválido: " + "; ".join(hierarchy_violations))
    draw_id = logical_payload["id"]
    timestamp = datetime.now(timezone.utc).isoformat()
    document = {"version": DRAW_VERSION, **logical_payload}
    output = draw_directory(root) / f"{draw_id}.json"
    index = read_draw_index(root)
    existing_entry = next((entry for entry in index["draws"] if str(entry.get("id")) == str(draw_id)), None)
    if output.exists() and existing_entry is not None:
        try:
            existing_document = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_document = None
        if isinstance(existing_document, dict) and logical_draw_payload(existing_document) == document:
            return output

    _atomic_write(output, json.dumps(document, indent=2, ensure_ascii=False) + "\n")

    metadata = {
        "id": draw_id,
        "file": output.name,
        "title": logical_payload["title"],
        "subtitle": logical_payload.get("subtitle", ""),
        "kind": logical_payload.get("kind", "feature"),
        "updated_at": timestamp,
        "node_count": len(logical_payload["nodes"]),
        "edge_count": len(logical_payload.get("edges", [])),
        "subdraw_count": sum(1 for node in logical_payload["nodes"] if node.get("draw_ref") is not None),
    }
    entries = [entry for entry in index["draws"] if str(entry.get("id")) != str(draw_id)]
    entries.append(metadata)
    entries.sort(key=lambda entry: (str(entry.get("title", "")).lower(), str(entry.get("id", ""))))
    _atomic_write(draw_index_path(root), json.dumps({"version": DRAW_VERSION, "draws": entries}, indent=2, ensure_ascii=False) + "\n")
    return output


def read_draw(root: Path, draw_id: str) -> dict[str, Any]:
    """Lê um desenho individual pelo ID validado.
    Carrega somente o JSON solicitado e rejeita caminhos fora de draws.
    """
    draw_id_text = str(draw_id)
    if not _is_draw_id(draw_id_text):
        raise ValueError("id de desenho inválido")
    path = draw_directory(root) / f"{draw_id_text}.json"
    if not path.exists():
        raise ValueError(f"desenho não encontrado: {draw_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"desenho inválido: {error.__class__.__name__}") from error
    if isinstance(payload, dict) and "tradeoffs" in payload:
        # Compatibilidade de leitura: Draws antigos são migrados no primeiro
        # acesso, mas a chave nunca volta a fazer parte do JSON persistido.
        payload.pop("tradeoffs", None)
        _atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    violations = validate_draw_payload(payload)
    if violations:
        raise ValueError("Desenho inválido: " + "; ".join(violations))
    hierarchy_violations = validate_hierarchy_parent(root, payload)
    if hierarchy_violations:
        raise ValueError("Desenho inválido: " + "; ".join(hierarchy_violations))
    return payload


def create_server(root: Path, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Cria um servidor HTTP local para permitir fetch dos JSONs pelo viewer.
    Serve a raiz do projeto sem expor o servidor para interfaces externas por padrão.
    """
    if not (0 <= port <= 65535):
        raise ValueError("port deve estar entre 0 e 65535")
    if not DRAW_ASSETS.is_dir():
        raise RuntimeError("assets do viewer Draw não estão instalados no pacote")
    workspace_violations = validate_draw_workspace(root)
    if workspace_violations:
        raise ValueError("Workspace de desenhos inválido: " + "; ".join(workspace_violations))
    from .improvements import ensure_improvement_workspace

    ensure_improvement_workspace(root)

    class ProjectHandler(SimpleHTTPRequestHandler):
        """Serve somente o viewer empacotado e a API de desenhos locais."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
            """Envia conteúdo HTTP com tipo e tamanho explícitos.
            Evita expor arquivos arbitrários do projeto pelo servidor do viewer.
            """
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            if content_type.startswith("text/html"):
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(content)

        def _send_file(self, path: Path) -> None:
            """Envia um asset validado pertencente ao pacote do Looper.
            Retorna 404 quando o asset solicitado não existe.
            """
            try:
                resolved = path.resolve()
                assets_root = DRAW_ASSETS.resolve()
                resolved.relative_to(assets_root)
                content = resolved.read_bytes()
            except (OSError, ValueError):
                self.send_error(404, "asset não encontrado")
                return
            content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
            self._send_bytes(content, content_type)

        def _send_json_error(self, status: int, message: str) -> None:
            """Retorna erro da API em JSON para consumo acionável pelo viewer.
            Mantém o corpo sem traceback ou caminho interno do servidor.
            """
            body = json.dumps({"status": "blocked", "error": message}, ensure_ascii=False).encode("utf-8")
            self._send_bytes(body, "application/json; charset=utf-8", status)

        def do_GET(self) -> None:
            """Serve assets empacotados e desenhos selecionados sob demanda.
            Nunca transforma a raiz do projeto em um servidor de arquivos.
            """
            path = urlparse(self.path).path
            if path == "/":
                self.send_response(302)
                self.send_header("Location", "/.looper/draw.html")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if path in {"/.looper/draw.html", "/draw.html", "/index.html"}:
                self._send_file(DRAW_ASSETS / "index.html")
                return
            if path in {"/favicon.svg", "/favicon.ico"}:
                self._send_file(DRAW_ASSETS / "favicon.svg")
                return
            if path == "/icons.svg":
                self._send_file(DRAW_ASSETS / "icons.svg")
                return
            if path.startswith("/assets/"):
                asset_name = unquote(path[len("/assets/"):])
                self._send_file(DRAW_ASSETS / "assets" / asset_name)
                return
            if path == "/.looper/draws/index.json":
                try:
                    body = json.dumps(read_draw_index(root), ensure_ascii=False).encode("utf-8")
                except ValueError as error:
                    self._send_json_error(500, str(error))
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            if path == "/.looper/improvements/index.json":
                from .improvements import read_improvement_index

                try:
                    body = json.dumps(read_improvement_index(root), ensure_ascii=False).encode("utf-8")
                except ValueError as error:
                    self._send_json_error(500, str(error))
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            if path == "/.looper/backlog.json":
                from .backlog import read_backlog

                try:
                    body = json.dumps(read_backlog(root), ensure_ascii=False).encode("utf-8")
                except ValueError:
                    self._send_json_error(404, "backlog não encontrado")
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            if path == "/.looper/runs/index.json":
                runs_index = root / ".looper" / "runs" / "index.json"
                try:
                    body = runs_index.read_bytes() if runs_index.exists() else b'{"version": 1, "days": []}'
                except OSError:
                    self._send_json_error(500, "índice de runs indisponível")
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            if path == "/.looper/adapters/static-analysis-kpis.json":
                kpi_path = root / ".looper" / "adapters" / "static-analysis-kpis.json"
                try:
                    body = kpi_path.read_bytes() if kpi_path.exists() else b'{"status":"unavailable","indicators":[],"details":{}}'
                except OSError:
                    self._send_json_error(404, "indicadores de análise estática não encontrados")
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            runs_prefix = "/.looper/runs/"
            if path.startswith(runs_prefix) and path.endswith(".json"):
                relative_run_path = unquote(path[len(runs_prefix):])
                runs_root = (root / ".looper" / "runs").resolve()
                run_path = (runs_root / relative_run_path).resolve()
                try:
                    run_path.relative_to(runs_root)
                    if run_path.name not in {"index.json"} and not run_path.name.endswith(("_summary.json", "_snapshot.json")):
                        raise ValueError("arquivo de run não permitido")
                    body = run_path.read_bytes()
                except (OSError, ValueError):
                    self._send_json_error(404, "registro de run não encontrado")
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            facts_prefix = "/.looper/facts/"
            facts_suffix = ".facts.json"
            if path.startswith(facts_prefix) and path.endswith(facts_suffix):
                draw_id = unquote(path[len(facts_prefix):-len(facts_suffix)])
                facts_path = facts_directory(root) / f"{draw_id}{facts_suffix}"
                try:
                    if not _is_draw_id(draw_id):
                        raise ValueError("id de desenho inválido")
                    resolved = facts_path.resolve()
                    resolved.relative_to(facts_directory(root).resolve())
                    body = resolved.read_bytes()
                except (OSError, ValueError):
                    self._send_json_error(404, "facts do desenho não encontrados")
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            draws_prefix = "/.looper/draws/"
            if path.startswith(draws_prefix) and path.endswith(".json"):
                draw_id = unquote(path[len(draws_prefix):-5])
                try:
                    body = json.dumps(read_draw(root, draw_id), ensure_ascii=False).encode("utf-8")
                except ValueError:
                    self._send_json_error(404, "desenho não encontrado")
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            improvements_prefix = "/.looper/improvements/"
            if path.startswith(improvements_prefix) and path.endswith(".json"):
                from .improvements import read_improvement

                improvement_id = unquote(path[len(improvements_prefix):-5])
                try:
                    body = json.dumps(read_improvement(root, improvement_id), ensure_ascii=False).encode("utf-8")
                except ValueError:
                    self._send_json_error(404, "sessão de melhoria não encontrada")
                    return
                self._send_bytes(body, "application/json; charset=utf-8")
                return
            self.send_error(404, "endpoint inexistente")

        def _allow_local_origin(self) -> None:
            """Autoriza somente origens HTTP locais para o endpoint de salvamento.
            Permite usar o viewer via Live Server sem abrir a API para origens externas.
            """
            origin = self.headers.get("Origin", "")
            if origin == "null":
                self.send_header("Access-Control-Allow-Origin", "*")
            elif origin.startswith(("http://127.0.0.1:", "http://localhost:")):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def end_headers(self) -> None:
            """Adiciona CORS às respostas locais, inclusive leituras via file://.
            Mantém o viewer aberto como arquivo comum sem expor a API a origens externas.
            """
            self._allow_local_origin()
            super().end_headers()

        def do_OPTIONS(self) -> None:
            """Responde ao preflight CORS do salvamento local via Live Server.
            Aceita somente o endpoint de desenhos e o método PUT necessário pelo viewer.
            """
            path = urlparse(self.path).path
            if not (
                path.startswith("/__looper/api/draws/")
                or path.startswith("/__looper/api/improvements/")
                or path.startswith("/__looper/api/backlog")
            ):
                self.send_error(404, "endpoint inexistente")
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Looper-Editor-Draft")
            self.end_headers()

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            """Envia uma resposta JSON curta para as operações do backlog."""
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            """Reserva ou conclui uma task do backlog pelo servidor local."""
            from .backlog import complete_backlog_task, generate_backlog, next_backlog_change, next_backlog_task, next_backlog_test, update_backlog_checklist

            path = urlparse(self.path).path
            if path == "/__looper/api/backlog/task":
                try:
                    self._send_json(next_backlog_task(root))
                except (OSError, ValueError) as error:
                    self._send_json({"status": "blocked", "error": str(error)}, 400)
                return
            if path == "/__looper/api/backlog/test":
                try:
                    self._send_json(next_backlog_test(root))
                except (OSError, ValueError) as error:
                    self._send_json({"status": "blocked", "error": str(error)}, 400)
                return
            if path == "/__looper/api/backlog/change":
                try:
                    self._send_json(next_backlog_change(root))
                except (OSError, ValueError) as error:
                    self._send_json({"status": "blocked", "error": str(error)}, 400)
                return
            if path == "/__looper/api/backlog/refresh":
                try:
                    self._send_json({"kind": "backlog-refreshed", "backlog": generate_backlog(root)})
                except (OSError, ValueError) as error:
                    self._send_json({"status": "blocked", "error": str(error)}, 400)
                return
            if path == "/__looper/api/backlog/checklist":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 100_000:
                        raise ValueError("payload de checklist inválido")
                    body = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(body, dict):
                        raise ValueError("payload de checklist deve ser um objeto")
                    result = update_backlog_checklist(
                        root,
                        body.get("task_id"),
                        body.get("phase"),
                        body.get("checked"),
                    )
                    self._send_json(result)
                except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    self._send_json({"status": "blocked", "error": str(error)}, 400)
                return
            prefix = "/__looper/api/backlog/tasks/"
            suffix = "/complete"
            if path.startswith(prefix) and path.endswith(suffix):
                task_id = unquote(path[len(prefix):-len(suffix)])
                try:
                    self._send_json(complete_backlog_task(root, task_id))
                except (OSError, ValueError) as error:
                    self._send_json({"status": "blocked", "error": str(error)}, 400)
                return
            self.send_error(404, "endpoint inexistente")

        def do_PUT(self) -> None:
            """Salva um JSON editado pelo viewer através de endpoint local.
            Aceita somente o ID do desenho na rota e delega validação ao contrato canônico.
            """
            path = urlparse(self.path).path
            improvement_prefix = "/__looper/api/improvements/"
            if path.startswith(improvement_prefix):
                from .improvements import create_improvement

                improvement_id = unquote(path[len(improvement_prefix):])
                if improvement_id.endswith(".json"):
                    improvement_id = improvement_id[:-5]
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 200_000:
                        raise ValueError("payload deve ter entre 1 e 200000 bytes")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(payload, dict) or str(payload.get("id")) != improvement_id:
                        raise ValueError("id da rota e do JSON devem ser iguais")
                    output = create_improvement(root, payload)
                    body = json.dumps({"status": "saved", "path": str(output.relative_to(root))}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    self._send_json_error(400, str(error))
                return
            prefix = "/__looper/api/draws/"
            if not path.startswith(prefix):
                self.send_error(404, "endpoint inexistente")
                return
            draw_id = unquote(path[len(prefix):])
            if draw_id.endswith(".json"):
                draw_id = draw_id[:-5]
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 2_000_000:
                    raise ValueError("payload deve ter entre 1 e 2000000 bytes")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict) or str(payload.get("id")) != draw_id:
                    raise ValueError("id da rota e do JSON devem ser iguais")
                editor_draft = self.headers.get("X-Looper-Editor-Draft", "").lower() == "true"
                output = create_draw(root, payload, allow_disconnected_nodes=editor_draft)
                body = json.dumps({"status": "saved", "path": str(output.relative_to(root))}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
                body = json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

    return ThreadingHTTPServer((host, port), ProjectHandler)


def serve_draw(root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Serve o viewer Draw até receber interrupção do processo.
    Garante o workspace e informa a URL local antes de iniciar o loop HTTP.
    """
    ensure_draw_workspace(root, include_example=True)
    server = create_server(root, host, port)
    print(f"Draw disponível em http://{server.server_address[0]}:{server.server_address[1]}/.looper/draw.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def start_server_for_test(root: Path, port: int = 0) -> tuple[ThreadingHTTPServer, Thread]:
    """Inicia um servidor Draw em thread para testes de integração HTTP.
    Usa porta zero por padrão para evitar colisões entre execuções paralelas.
    """
    server = create_server(root, port=port)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread

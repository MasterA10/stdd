"""Criação de JSONs e servidor local do viewer Draw.
Mantém os dados dos desenhos separados do HTML reutilizável e carregado sob demanda.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import unquote, urlparse


DRAW_VERSION = 1
DRAW_TEMPLATE_VERSION = "4"
EDGE_CONDITIONS = {1: "então", 2: "ou", 3: "se"}
QUESTION_TYPES = {"choice", "boolean", "open"}
DRAW_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
DRAW_TEMPLATE = Path(__file__).parent / "templates" / "draw" / "draw.html"
PRESENTATION_KEYS = {"color", "colors", "position", "style", "styles", "layout", "viewport", "theme", "x", "y", "width", "height"}


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
    for collection in ("groups", "nodes", "edges"):
        for item in document.get(collection, []):
            if isinstance(item, dict):
                for key in PRESENTATION_KEYS:
                    item.pop(key, None)
    return document


def draw_directory(root: Path) -> Path:
    """Retorna o diretório de dados dos desenhos do projeto.
    Mantém todos os JSONs gerados pelo framework dentro de .stdd/draws.
    """
    return root / ".stdd" / "draws"


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
    draw_id = payload.get("id")
    if not _is_draw_id(draw_id):
        violations.append("id do desenho deve ser descritivo, minúsculo e seguro; use números somente nas entidades internas")
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        violations.append("title é obrigatório")

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
                if answer is not None and (not _is_numeric_id(answer) or answer not in option_ids):
                    violations.append(f"{prefix}.answer deve apontar para uma opção existente")
            elif question_type == "boolean":
                if "options" in question:
                    violations.append(f"{prefix} boolean não deve declarar options")
                if answer is not None and not isinstance(answer, bool):
                    violations.append(f"{prefix}.answer deve ser booleano ou nulo")
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
        source, target = edge.get("from"), edge.get("to")
        if source not in node_ids or target not in node_ids:
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


def ensure_draw_workspace(root: Path) -> list[Path]:
    """Cria o viewer único e o índice vazio do projeto.
    É idempotente e não cria um HTML por desenho.
    """
    stdd_path = root / ".stdd"
    draws_path = draw_directory(root)
    created: list[Path] = []
    for directory in (stdd_path, draws_path):
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
    viewer = stdd_path / "draw.html"
    template = DRAW_TEMPLATE.read_text(encoding="utf-8")
    if not viewer.exists() or viewer.read_text(encoding="utf-8") != template:
        viewer.write_text(template, encoding="utf-8")
        created.append(viewer)
    index = draw_index_path(root)
    if not index.exists():
        index.write_text(json.dumps({"version": DRAW_VERSION, "draws": []}, indent=2) + "\n", encoding="utf-8")
        created.append(index)
    return created


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


def _atomic_write(path: Path, content: str) -> None:
    """Escreve um arquivo por substituição atômica no mesmo diretório.
    Evita deixar JSON parcial quando o processo é interrompido durante a gravação.
    """
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def create_draw(root: Path, payload: dict[str, Any]) -> Path:
    """Valida e grava um desenho JSON, atualizando somente o índice leve.
    Sobrescreve o mesmo ID de forma atômica e nunca produz HTML individual.
    """
    logical_payload = logical_draw_payload(payload)
    violations = validate_draw_payload(logical_payload)
    if violations:
        raise ValueError("Desenho inválido: " + "; ".join(violations))
    ensure_draw_workspace(root)
    draw_id = logical_payload["id"]
    timestamp = datetime.now(timezone.utc).isoformat()
    document = {"version": DRAW_VERSION, **logical_payload}
    output = draw_directory(root) / f"{draw_id}.json"
    _atomic_write(output, json.dumps(document, indent=2, ensure_ascii=False) + "\n")

    index = read_draw_index(root)
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
    violations = validate_draw_payload(payload)
    if violations:
        raise ValueError("Desenho inválido: " + "; ".join(violations))
    return payload


def create_server(root: Path, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Cria um servidor HTTP local para permitir fetch dos JSONs pelo viewer.
    Serve a raiz do projeto sem expor o servidor para interfaces externas por padrão.
    """
    if not (0 <= port <= 65535):
        raise ValueError("port deve estar entre 0 e 65535")

    class ProjectHandler(SimpleHTTPRequestHandler):
        """Serve arquivos do projeto sem registrar requisições no stderr."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_PUT(self) -> None:
            """Salva um JSON editado pelo viewer através de endpoint local.
            Aceita somente o ID do desenho na rota e delega validação ao contrato canônico.
            """
            path = urlparse(self.path).path
            prefix = "/__stdd/api/draws/"
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
                output = create_draw(root, payload)
                body = json.dumps({"status": "saved", "path": str(output.relative_to(root))}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
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
    ensure_draw_workspace(root)
    server = create_server(root, host, port)
    print(f"Draw disponível em http://{server.server_address[0]}:{server.server_address[1]}/.stdd/draw.html")
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

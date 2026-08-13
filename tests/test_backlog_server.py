import json
from pathlib import Path
from urllib.request import Request, urlopen

from stdd.backlog import generate_backlog
from stdd.draw import create_draw, start_server_for_test


def _create_hierarchical_fixture(root: Path) -> None:
    """Cria uma jornada mínima para o teste HTTP do backlog.
    Mantém dois terminais e um self-loop sem depender de fixtures externas.
    """
    create_draw(root, {
        "id": "sistema", "title": "Sistema", "kind": "system",
        "hierarchy": {"level": 1, "role": "architecture", "root_draw_ref": "sistema"},
        "groups": [], "nodes": [
            {"id": 1, "label": "Jornada", "description": "Jornada principal.", "draw_ref": "jornada"},
            {"id": 2, "label": "Fim", "description": "Fim da arquitetura."},
        ], "edges": [{"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 1}], "flows": [],
    })
    create_draw(root, {
        "id": "jornada", "title": "Jornada", "kind": "flow",
        "hierarchy": {"level": 2, "role": "journey", "parent_draw_ref": "sistema", "parent_node_id": 1, "root_draw_ref": "sistema"},
        "groups": [], "nodes": [
            {"id": 1, "label": "Iniciar", "description": "Usuário inicia.", "questions": [{"id": 1, "type": "open", "prompt": "Entrada?", "answer": "botão"}], "code_refs": [{"symbol": "Journey.start", "file": "src/journey.py"}]},
            {"id": 2, "label": "Sucesso", "description": "Jornada concluída.", "code_refs": [{"symbol": "Journey.success"}]},
            {"id": 3, "label": "Retry", "description": "Aguarda retry.", "code_refs": [{"symbol": "Journey.retry"}]},
        ], "edges": [
            {"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 2},
            {"id": 2, "from": 1, "to": 3, "kind": "flow", "condition": 2},
            {"id": 3, "from": 3, "to": 3, "kind": "flow", "condition": 1},
        ], "flows": [],
    })


def test_draw_server_serves_backlog_and_claims_and_completes_task(tmp_path: Path):
    """Expõe o backlog e o ciclo de task pelo Draw Server.
    Consulta a task, conclui pelo ID e confirma o estado persistido.
    """
    _create_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)
    server, thread = start_server_for_test(tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        document = json.loads(urlopen(f"{base_url}/.stdd/backlog.json").read())
        assert document["tasks"][0]["questions"]
        request = Request(f"{base_url}/__stdd/api/backlog/task", method="POST")
        task = json.loads(urlopen(request).read())
        assert task["kind"] == "backlog-task"
        complete = Request(
            f"{base_url}/__stdd/api/backlog/tasks/{task['task']['id']}/complete",
            method="POST",
        )
        assert json.loads(urlopen(complete).read())["status"] == "done"
        saved = json.loads(urlopen(f"{base_url}/.stdd/backlog.json").read())
        assert saved["tasks"][0]["status"] == "done"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

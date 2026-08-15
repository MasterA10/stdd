import json
from pathlib import Path

from typer.testing import CliRunner

from stdd.backlog import build_backlog, check_backlog, complete_backlog_task, generate_backlog, next_backlog_task, read_backlog
from stdd.cli import app
from stdd.core import init_project, run_tests
from stdd.draw import create_draw


runner = CliRunner()


def _create_hierarchical_fixture(root: Path) -> None:
    """Cria uma raiz, uma jornada de nível 2 e duas ramificações.
    Inclui perguntas, símbolos, dependências e um self-loop terminal.
    """
    create_draw(
        root,
        {
            "id": "sistema",
            "title": "Sistema",
            "kind": "system",
            "hierarchy": {"level": 1, "role": "architecture", "root_draw_ref": "sistema"},
            "groups": [],
            "nodes": [
                {"id": 1, "label": "Jornada", "description": "Jornada principal.", "draw_ref": "jornada"},
                {"id": 2, "label": "Fim", "description": "Fim da arquitetura."},
            ],
            "edges": [{"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 1}],
            "flows": [],
        },
    )
    create_draw(
        root,
        {
            "id": "jornada",
            "title": "Jornada do usuário",
            "kind": "flow",
            "hierarchy": {
                "level": 2,
                "role": "journey",
                "parent_draw_ref": "sistema",
                "parent_node_id": 1,
                "root_draw_ref": "sistema",
            },
            "groups": [],
            "nodes": [
                {
                    "id": 1,
                    "label": "Iniciar",
                    "description": "Usuário inicia a jornada.",
                    "questions": [
                        {"id": 1, "type": "open", "prompt": "Qual entrada?", "answer": "botão"},
                        {"id": 2, "type": "boolean", "prompt": "Está autenticado?", "answer": False},
                    ],
                    "code_refs": [
                        {"symbol": "Journey.start", "file": "src/journey.py", "source_dependencies": ["Session.read"]},
                        {"qualified_name": "Audit.record", "file": "src/audit.py"},
                    ],
                },
                {"id": 2, "label": "Sucesso", "description": "Jornada concluída com sucesso.", "code_refs": [{"symbol": "Journey.success"}]},
                {"id": 3, "label": "Retry", "description": "Jornada aguarda nova tentativa.", "code_refs": [{"symbol": "Journey.retry"}]},
            ],
            "edges": [
                {"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 2, "label": "sucesso"},
                {"id": 2, "from": 1, "to": 3, "kind": "flow", "condition": 2, "label": "retry"},
                {"id": 3, "from": 3, "to": 3, "kind": "flow", "condition": 1, "label": "fim"},
            ],
            "flows": [],
        },
    )


def _create_nested_hierarchical_fixture(root: Path) -> None:
    """Cria uma jornada com subfluxo associado a um nó pai.
    O filho possui duas etapas internas que devem entrar no backlog.
    """
    _create_hierarchical_fixture(root)
    parent_path = root / ".stdd" / "draws" / "jornada.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent["nodes"][0]["draw_ref"] = "subjornada"
    parent_path.write_text(json.dumps(parent), encoding="utf-8")
    create_draw(
        root,
        {
            "id": "subjornada",
            "title": "Subjornada interna",
            "kind": "flow",
            "hierarchy": {
                "level": 3,
                "role": "implementation",
                "parent_draw_ref": "jornada",
                "parent_node_id": 1,
                "root_draw_ref": "sistema",
            },
            "groups": [],
            "nodes": [
                {"id": 1, "label": "Preparar interno", "description": "Prepara o subfluxo."},
                {"id": 2, "label": "Concluir interno", "description": "Conclui o subfluxo."},
            ],
            "edges": [{"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 1}],
            "flows": [],
        },
    )


def test_build_backlog_copies_level_two_questions_symbols_and_branches(tmp_path: Path):
    """Gera tasks de nós de nível 2 com seus dados estruturados.
    Deriva duas branches, preserva perguntas e encerra self-loop como terminal.
    """
    _create_hierarchical_fixture(tmp_path)

    backlog = build_backlog(tmp_path, generated_at="2026-08-13T12:00:00+00:00")

    assert [task["id"] for task in backlog["tasks"]] == [
        "task:jornada:node:1",
        "task:jornada:node:2",
        "task:jornada:node:3",
    ]
    task = backlog["tasks"][0]
    assert task["level"] == 2
    assert task["questions"][1]["answer"] is False
    assert task["symbols"] == ["Audit.record", "Journey.start"]
    assert task["source_dependencies"] == ["Session.read"]
    assert len(backlog["execution"]["branches"]) == 2
    assert backlog["execution"]["branches"][1]["terminal_node_id"] == 3
    assert backlog["execution"]["branches"][1]["terminal_reason"] == "self-loop"


def test_backlog_keeps_shared_steps_in_every_branch_and_tracks_all_occurrences(tmp_path: Path):
    """Preserva prefixos compartilhados em cada caminho da jornada.
    Mantém uma task por nó, mas registra a ocorrência em todas as branches.
    """
    _create_hierarchical_fixture(tmp_path)

    backlog = build_backlog(tmp_path, generated_at="2026-08-13T12:00:00+00:00")

    branches = backlog["execution"]["branches"]
    assert [branch["task_ids"] for branch in branches] == [
        ["task:jornada:node:1", "task:jornada:node:2"],
        ["task:jornada:node:1", "task:jornada:node:3"],
    ]
    assert [branch["node_ids"] for branch in branches] == [[1, 2], [1, 3]]
    assert [occurrence["id"] for occurrence in backlog["tasks"][0]["branches"]] == [
        "jornada:branch:1",
        "jornada:branch:2",
    ]
    assert backlog["tasks"][2]["branches"][0]["terminal"] is True


def test_backlog_starts_child_backlog_after_parent_node(tmp_path: Path):
    """Inclui o nó pai e as tasks do subfluxo na sequência operacional.
    Só continua a branch principal depois de concluir o backlog interno.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)

    first = next_backlog_task(tmp_path)
    assert first["task"]["id"] == "task:jornada:node:1"
    assert first["task"]["child_backlog_id"] == "subjornada"
    assert first["task"]["child_task_ids"] == [
        "task:subjornada:node:1",
        "task:subjornada:node:2",
    ]
    complete_backlog_task(tmp_path, first["task"]["id"])

    internal = next_backlog_task(tmp_path)
    assert internal["task"]["id"] == "task:subjornada:node:1"
    assert internal["task"]["parent_task_id"] == "task:jornada:node:1"
    assert read_backlog(tmp_path)["execution"]["current_backlog_id"] == "subjornada"
    complete_backlog_task(tmp_path, internal["task"]["id"])

    internal_last = next_backlog_task(tmp_path)
    assert internal_last["task"]["id"] == "task:subjornada:node:2"
    complete_backlog_task(tmp_path, internal_last["task"]["id"])
    assert next_backlog_task(tmp_path)["task"]["id"] == "task:jornada:node:2"

    saved = read_backlog(tmp_path)
    assert saved["backlogs"][1]["id"] == "backlog:subjornada"
    assert saved["backlogs"][1]["parent_task_id"] == "task:jornada:node:1"


def test_backlog_preserves_shared_steps_in_explicit_flow_paths(tmp_path: Path):
    """Preserva todas as etapas quando as branches vêm de flows explícitos.
    Não remove um nó compartilhado só porque ele já apareceu em outro flow.
    """
    _create_hierarchical_fixture(tmp_path)
    draw_path = tmp_path / ".stdd" / "draws" / "jornada.json"
    document = json.loads(draw_path.read_text(encoding="utf-8"))
    document["flows"] = [
        {"id": 1, "label": "sucesso", "steps": [{"node": 1}, {"node": 2}]},
        {"id": 2, "label": "retry", "steps": [{"node": 1}, {"node": 3}]},
    ]
    draw_path.write_text(json.dumps(document), encoding="utf-8")

    backlog = build_backlog(tmp_path, generated_at="2026-08-13T12:00:00+00:00")

    assert [branch["node_ids"] for branch in backlog["execution"]["branches"]] == [[1, 2], [1, 3]]
    assert [branch["flow_id"] for branch in backlog["execution"]["branches"]] == [1, 2]
    assert backlog["tasks"][0]["branches"][1]["id"] == "jornada:branch:2"


def test_backlog_includes_nodes_missing_from_explicit_flows_and_children(tmp_path: Path):
    """Gera uma task para cada nó do fluxo e subfluxo.
    Mantém a associação pai-filho quando flows.steps omite nós.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    journey_path = tmp_path / ".stdd" / "draws" / "jornada.json"
    journey = json.loads(journey_path.read_text(encoding="utf-8"))
    journey["flows"] = [
        {"id": 1, "label": "sucesso", "steps": [{"node": 1}, {"node": 2}]},
    ]
    journey_path.write_text(json.dumps(journey), encoding="utf-8")
    child_path = tmp_path / ".stdd" / "draws" / "subjornada.json"
    child = json.loads(child_path.read_text(encoding="utf-8"))
    child["flows"] = [{"id": 1, "label": "interno", "steps": [{"node": 1}]}]
    child_path.write_text(json.dumps(child), encoding="utf-8")

    backlog = build_backlog(tmp_path, generated_at="2026-08-13T12:00:00+00:00")

    assert len(backlog["tasks"]) == 5
    assert {task["id"] for task in backlog["tasks"]} == {
        "task:jornada:node:1",
        "task:jornada:node:2",
        "task:jornada:node:3",
        "task:subjornada:node:1",
        "task:subjornada:node:2",
    }
    omitted_parent = next(task for task in backlog["tasks"] if task["id"] == "task:jornada:node:3")
    omitted_child = next(task for task in backlog["tasks"] if task["id"] == "task:subjornada:node:2")
    assert omitted_parent["branch"]["terminal_reason"] == "node-not-listed-in-flow"
    assert omitted_child["parent_task_id"] == "task:jornada:node:1"
    assert [backlog_item["task_ids"] for backlog_item in backlog["backlogs"]] == [
        ["task:jornada:node:1", "task:jornada:node:2", "task:jornada:node:3"],
        ["task:subjornada:node:1", "task:subjornada:node:2"],
    ]


def test_backlog_marks_every_branch_complete_when_shared_terminal_is_done(tmp_path: Path):
    """Conclui todos os caminhos que dependem da mesma etapa final.
    Atualiza branches derivadas mesmo quando a task pertence à primeira branch.
    """
    _create_hierarchical_fixture(tmp_path)
    draw_path = tmp_path / ".stdd" / "draws" / "jornada.json"
    document = json.loads(draw_path.read_text(encoding="utf-8"))
    document["flows"] = [
        {"id": 1, "label": "sucesso", "steps": [{"node": 1}, {"node": 2}, {"node": 3}]},
        {"id": 2, "label": "retry", "steps": [{"node": 1}, {"node": 3}]},
    ]
    draw_path.write_text(json.dumps(document), encoding="utf-8")
    generate_backlog(tmp_path)

    for _ in range(3):
        response = next_backlog_task(tmp_path)
        complete_backlog_task(tmp_path, response["task"]["id"])

    saved = read_backlog(tmp_path)
    assert len(saved["execution"]["completed_branches"]) == 2
    assert all(branch["completed"] for branch in saved["execution"]["branches"])


def test_backlog_task_and_complete_walk_one_branch_then_the_next(tmp_path: Path):
    """Entrega uma task por vez e alterna branches somente no terminal.
    Completa a jornada em ordem e confirma o retorno backlog-empty no fim.
    """
    _create_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)

    first = next_backlog_task(tmp_path)
    assert first["task"]["id"] == "task:jornada:node:1"
    complete_backlog_task(tmp_path, first["task"]["id"])
    second = next_backlog_task(tmp_path)
    assert second["task"]["id"] == "task:jornada:node:2"
    complete_backlog_task(tmp_path, second["task"]["id"])
    third = next_backlog_task(tmp_path)
    assert third["task"]["id"] == "task:jornada:node:3"
    complete_backlog_task(tmp_path, third["task"]["id"])
    assert next_backlog_task(tmp_path)["kind"] == "backlog-empty"


def test_backlog_complete_rejects_a_task_that_is_not_current(tmp_path: Path):
    """Impede conclusão fora da ordem controlada pelo cursor.
    Tenta concluir a segunda task antes da primeira e preserva o estado atual.
    """
    _create_hierarchical_fixture(tmp_path)
    build_backlog(tmp_path)
    next_backlog_task(tmp_path)

    try:
        complete_backlog_task(tmp_path, "task:jornada:node:2")
    except ValueError as error:
        assert "task atual" in str(error)
    else:
        raise AssertionError("task fora de ordem deveria ser rejeitada")
    assert read_backlog(tmp_path)["execution"]["current_task_id"] == "task:jornada:node:1"


def test_backlog_cli_generates_returns_missing_task_and_completes_by_id(tmp_path: Path, monkeypatch):
    """Expõe o ciclo operacional do backlog pela CLI.
    Executa generate, task e complete e valida respostas JSON estruturadas.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)

    generated = runner.invoke(app, ["backlog", "generate"])
    assert generated.exit_code == 0
    task = runner.invoke(app, ["backlog", "task"])
    assert task.exit_code == 0
    task_payload = json.loads(task.stdout)
    assert task_payload["kind"] == "backlog-task"
    completed = runner.invoke(app, ["backlog", "complete", task_payload["task"]["id"]])
    assert completed.exit_code == 0
    missing = runner.invoke(app, ["backlog", "missing"])
    assert missing.exit_code == 0
    assert all(item["status"] != "done" for item in json.loads(missing.stdout)["items"])


def test_stdd_test_blocks_when_backlog_has_unchecked_implementation(tmp_path: Path):
    """Bloqueia o teste global enquanto existir uma task sem check de conclusão.
    Libera o gate somente depois que o agente percorre e conclui todas as tasks.
    """
    (tmp_path / ".stdd").mkdir()
    (tmp_path / ".stdd/config.json").write_text(json.dumps({
        "test_commands": [{"name": "unit", "command": ["python", "-c", "print('ok')"]}],
        "static_analysis": {"enabled": False},
    }), encoding="utf-8")
    _create_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)

    blocked_process, blocked_report = run_tests(tmp_path)

    assert blocked_process.returncode != 0
    assert blocked_report["backlog"]["status"] == "blocked"
    assert blocked_report["backlog"]["remaining"] == 3

    while True:
        response = next_backlog_task(tmp_path)
        if response["kind"] == "backlog-empty":
            break
        complete_backlog_task(tmp_path, response["task"]["id"])
    passed_process, passed_report = run_tests(tmp_path)

    assert passed_process.returncode == 0
    assert check_backlog(tmp_path)["status"] == "passed"
    assert passed_report["backlog"]["remaining"] == 0

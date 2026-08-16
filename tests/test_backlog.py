import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from stdd.backlog import build_backlog, check_backlog, complete_backlog_task, generate_backlog, next_backlog_task, next_backlog_test, read_backlog, update_backlog_checklist
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
                    "test_ref": {"file": "tests/test_journey.py", "symbols": ["tests.test_journey.test_journey_flow"]},
                },
                {"id": 2, "label": "Sucesso", "description": "Jornada concluída com sucesso.", "code_refs": [{"symbol": "Journey.success"}], "test_ref": {"file": "tests/test_journey.py", "symbols": ["tests.test_journey.test_journey_flow"]}},
                {"id": 3, "label": "Retry", "description": "Jornada aguarda nova tentativa.", "code_refs": [{"symbol": "Journey.retry"}], "test_ref": {"file": "tests/test_journey.py", "symbols": ["tests.test_journey.test_journey_flow"]}},
            ],
            "edges": [
                {"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 2, "label": "sucesso"},
                {"id": 2, "from": 1, "to": 3, "kind": "flow", "condition": 2, "label": "retry"},
                {"id": 3, "from": 3, "to": 3, "kind": "flow", "condition": 1, "label": "fim"},
            ],
            "flows": [],
        },
    )
    _write_test_evidence(root)


def _write_test_evidence(root: Path) -> None:
    """Recria a evidência estática usada pelas fixtures do backlog.
    Mantém o teste independente de um adapter real ou de rede.
    """
    test_file = root / "tests" / "test_journey.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('def test_journey_flow():\n    """Exercita a jornada criada pela fixture.\n    Confirma o caminho principal sem depender da aplicação.\n    """\n    assert True\n', encoding="utf-8")
    kpi_path = root / ".stdd" / "adapters" / "static-analysis-kpis.json"
    kpi_path.parent.mkdir(parents=True, exist_ok=True)
    kpi_path.write_text(json.dumps({"details": {"symbols": [{"qualified_name": "tests.test_journey.test_journey_flow", "file": "tests/test_journey.py", "kind": "function"}]}}), encoding="utf-8")


def _remove_test_refs(root: Path) -> None:
    """Remove as associações de teste para exercitar o bloqueio do backlog.
    Regrava somente o Draw de nível 2 e preserva o restante da fixture.
    """
    path = root / ".stdd" / "draws" / "jornada.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for node in payload["nodes"]:
        node.pop("test_ref", None)
        node.pop("test_refs", None)
    create_draw(root, payload)


def _add_test_refs(root: Path, as_list: bool = False) -> None:
    """Adiciona referências válidas de teste ao Draw de nível 2.
    Permite validar o formato singular e o formato compatível em lista.
    """
    path = root / ".stdd" / "draws" / "jornada.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for node in payload["nodes"]:
        reference = {"file": "tests/test_journey.py", "symbols": ["tests.test_journey.test_journey_flow"]}
        if as_list:
            node["test_refs"] = [reference]
        else:
            node["test_ref"] = reference
    create_draw(root, payload)


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
    assert task["test_ref"] == {"file": "tests/test_journey.py", "symbols": ["tests.test_journey.test_journey_flow"]}
    assert task["test_status"] == "done"
    assert len(backlog["execution"]["branches"]) == 2
    assert backlog["execution"]["branches"][1]["terminal_node_id"] == 3
    assert backlog["execution"]["branches"][1]["terminal_reason"] == "self-loop"


def test_backlog_task_reports_missing_test_without_claiming_implementation(tmp_path: Path):
    """Bloqueia implementação quando a task não possui teste comprovado.
    Retorna a task estruturada sem reservar o cursor de implementação.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)

    response = next_backlog_task(tmp_path)

    assert response["kind"] == "backlog-test-required"
    assert response["status"] == "blocked"
    assert response["task"]["test_status"] == "missing"
    assert read_backlog(tmp_path)["execution"]["current_task_id"] is None


def test_backlog_test_creates_test_phase_then_releases_same_task_for_implementation(tmp_path: Path):
    """Executa a fase de testes antes da fase de implementação da mesma task.
    Completa o teste, reserva a implementação e mantém o ID operacional.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)

    test_task = next_backlog_test(tmp_path)

    assert test_task["kind"] == "backlog-test-task"
    assert test_task["phase"] == "test"
    task_id = test_task["task"]["id"]
    _add_test_refs(tmp_path)
    test_done = complete_backlog_task(tmp_path, task_id)
    assert test_done["kind"] == "backlog-test-complete"
    assert test_done["task"]["test_status"] == "done"

    implementation = next_backlog_task(tmp_path)

    assert implementation["kind"] == "backlog-task"
    assert implementation["phase"] == "implementation"
    assert implementation["task"]["id"] == task_id


def test_backlog_test_accepts_test_refs_list_and_requires_one_file(tmp_path: Path):
    """Aceita a forma em lista quando ela aponta para um único arquivo.
    Rejeita uma associação que espalha a cobertura por mais de um arquivo.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    _add_test_refs(tmp_path, as_list=True)

    valid = build_backlog(tmp_path)
    assert valid["tasks"][0]["test_status"] == "done"

    path = tmp_path / ".stdd" / "draws" / "jornada.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["nodes"][0]["test_refs"] = [
        {"file": "tests/test_journey.py", "symbols": ["tests.test_journey.test_journey_flow"]},
        {"file": "tests/test_other.py", "symbols": ["tests.test_other.test_other"]},
    ]
    create_draw(tmp_path, payload)
    invalid = build_backlog(tmp_path)
    assert invalid["tasks"][0]["test_status"] == "missing"
    assert "um único arquivo" in invalid["tasks"][0]["test_evidence"]["reason"]


def test_check_backlog_blocks_missing_test_evidence(tmp_path: Path):
    """Inclui testes faltantes no gate global do backlog.
    Diferencia tarefas pendentes de implementação das tarefas sem evidência de teste.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    generate_backlog(tmp_path)

    report = check_backlog(tmp_path)

    assert report["status"] == "blocked"
    assert report["missing_tests"] == 3
    assert report["reason"] == "tasks_missing_tests"


def test_backlog_builds_test_before_implementation_checklists_and_context(tmp_path: Path):
    """Gera os dois checklists centrais na ordem correta.
    Entrega a task pai com a primeira subtask como contexto operacional.
    """
    _create_nested_hierarchical_fixture(tmp_path)

    backlog = build_backlog(tmp_path)
    assert list(backlog["phase_checklists"]) == ["test", "implementation"]
    assert len(backlog["phase_checklists"]["test"]) == len(backlog["tasks"])
    assert all(item["checked"] for item in backlog["phase_checklists"]["test"])
    assert not any(item["checked"] for item in backlog["phase_checklists"]["implementation"])

    response = next_backlog_task(tmp_path)
    assert response["parent_task"]["id"] == "task:jornada:node:1"
    assert response["subtask"]["id"] == "task:subjornada:node:1"
    assert response["subtasks"][0]["id"] == "task:subjornada:node:1"


def test_backlog_checklist_can_mark_without_static_evidence_and_uncheck(tmp_path: Path):
    """Permite marcar manualmente um fluxo pronto sem análise estática.
    Mantém a possibilidade de desmarcar e retorna a task para implementação.
    """
    _create_hierarchical_fixture(tmp_path)
    task_id = "task:jornada:node:1"

    update_backlog_checklist(tmp_path, task_id, "test", False)
    saved = read_backlog(tmp_path)
    task = next(item for item in saved["tasks"] if item["id"] == task_id)
    assert task["checklist_state"]["test"] is False
    assert task["checklist_state"]["implementation"] is False

    _remove_test_refs(tmp_path)
    for node_id in (1, 2, 3):
        update_backlog_checklist(tmp_path, f"task:jornada:node:{node_id}", "test", True)
    assert read_backlog(tmp_path)["tasks"][0]["checklist_state"]["test"] is True
    assert next_backlog_task(tmp_path)["kind"] == "backlog-task"


def test_backlog_parent_and_subtask_can_be_completed_independently(tmp_path: Path):
    """Permite concluir o pai e a subtask pelo próprio ID.
    Depois da primeira subtask, a resposta avança para a segunda mantendo o pai.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    first = next_backlog_task(tmp_path)
    parent_id = first["task"]["id"]
    first_subtask_id = first["subtask"]["id"]
    complete_backlog_task(tmp_path, parent_id)
    second = next_backlog_task(tmp_path)
    assert second["task"]["id"] == first_subtask_id
    complete_backlog_task(tmp_path, first_subtask_id)
    third = next_backlog_task(tmp_path)
    assert third["parent_task"]["id"] == parent_id
    assert third["subtask"]["id"] == "task:subjornada:node:2"


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
    Executa generate, task e complete e valida o modo JSON estruturado.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)

    generated = runner.invoke(app, ["backlog", "generate"])
    assert generated.exit_code == 0
    task = runner.invoke(app, ["backlog", "task", "--json"])
    assert task.exit_code == 0
    task_payload = json.loads(task.stdout)
    assert task_payload["kind"] == "backlog-task"
    completed = runner.invoke(app, ["backlog", "complete", task_payload["task"]["id"]])
    assert completed.exit_code == 0
    missing = runner.invoke(app, ["backlog", "missing"])
    assert missing.exit_code == 0
    assert all(item["status"] != "done" for item in json.loads(missing.stdout)["items"])


def test_backlog_cli_exposes_test_phase_and_structured_missing_test(tmp_path: Path, monkeypatch):
    """Expõe `backlog test` e o bloqueio legível de `backlog task`.
    Mantém ambas as respostas em JSON para consumo incremental pelo agente.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)

    human = runner.invoke(app, ["backlog", "task"])
    assert human.exit_code == 0
    assert "Teste necessário antes da implementação" in human.stdout
    assert "test_missing" not in human.stdout

    missing = runner.invoke(app, ["backlog", "task", "--json"])
    assert missing.exit_code == 0
    assert json.loads(missing.stdout)["kind"] == "backlog-test-required"
    testing = runner.invoke(app, ["backlog", "test"])

    assert testing.exit_code == 0
    test_payload = json.loads(testing.stdout)
    assert test_payload["kind"] == "backlog-test-task"
    assert test_payload["phase"] == "test"


def test_backlog_cli_task_has_a_concise_human_output(tmp_path: Path, monkeypatch):
    """Exibe somente o contexto acionável da task no modo padrão.
    Mantém uma decisão, os símbolos e o ID, sem alternativas ou payload duplicado.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)

    result = runner.invoke(app, ["backlog", "task"])

    assert result.exit_code == 0
    assert "Task: Iniciar" in result.stdout
    assert "Fluxo: Jornada do usuário" in result.stdout
    assert "ID: task:jornada:node:1" in result.stdout
    assert "Símbolos: Audit.record, Journey.start" in result.stdout
    assert "Qual entrada? → botão" in result.stdout
    assert "Está autenticado?" not in result.stdout
    assert "options" not in result.stdout


def test_stdd_test_blocks_when_backlog_has_unchecked_implementation(tmp_path: Path):
    """Bloqueia o teste global enquanto existir uma task sem check de conclusão.
    Libera o gate somente depois que o agente percorre e conclui todas as tasks.
    """
    (tmp_path / ".stdd").mkdir()
    analysis = {
        "contract_version": "1",
        "status": "passed",
        "capabilities": {"symbols": True},
        "symbols": [{"qualified_name": "tests.test_journey.test_journey_flow", "file": "tests/test_journey.py", "kind": "function"}],
        "dependencies": [], "technologies": [], "external_logic": [], "complexity": [],
        "structural_metrics": [], "quality_findings": [], "changes": [], "warnings": [], "errors": [],
    }
    analysis_code = f"import json; print({json.dumps(analysis)!r})"
    (tmp_path / ".stdd/config.json").write_text(json.dumps({
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('ok')"]}],
        "static_analysis": {"enabled": True, "adapter_command": [sys.executable, "-c", analysis_code]},
    }), encoding="utf-8")
    _create_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)

    blocked_process, blocked_report = run_tests(tmp_path)

    assert blocked_process.returncode != 0
    assert blocked_report["backlog"]["status"] == "blocked"
    assert blocked_report["backlog"]["remaining"] == 3
    _write_test_evidence(tmp_path)

    while True:
        response = next_backlog_task(tmp_path)
        if response["kind"] == "backlog-empty":
            break
        complete_backlog_task(tmp_path, response["task"]["id"])
    passed_process, passed_report = run_tests(tmp_path)

    assert passed_process.returncode == 0
    assert check_backlog(tmp_path)["status"] == "passed"
    assert passed_report["backlog"]["remaining"] == 0

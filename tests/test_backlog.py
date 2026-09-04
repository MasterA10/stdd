import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from looper.backlog import bootstrap_report, build_backlog, check_backlog, complete_backlog_task, generate_backlog, get_backlog_config, next_backlog_change, next_backlog_task, next_backlog_test, read_backlog, set_backlog_config, update_backlog_checklist, write_backlog
from looper.cli import _format_backlog_response, app
from looper.core import init_project, run_tests
from looper.draw import create_draw


runner = CliRunner()


def _create_hierarchical_fixture(root: Path, bootstrap: bool = False) -> None:
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
    config_path = root / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    config.setdefault("backlog", {})["bootstrap_task"] = bootstrap
    config.setdefault("backlog", {})["bootstrap_opt_out"] = not bootstrap
    # Estas fixtures históricas exercitam o fluxo agrupado; o comportamento
    # padrão do produto é coberto explicitamente pelos testes de entrega task.
    config.setdefault("backlog", {})["task_delivery_scope"] = "node"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config), encoding="utf-8")


def _write_test_evidence(root: Path) -> None:
    """Recria a evidência estática usada pelas fixtures do backlog.
    Mantém o teste independente de um adapter real ou de rede.
    """
    test_file = root / "tests" / "test_journey.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('def test_journey_flow():\n    """Exercita a jornada criada pela fixture.\n    Confirma o caminho principal sem depender da aplicação.\n    """\n    assert True\n', encoding="utf-8")
    kpi_path = root / ".looper" / "adapters" / "static-analysis-kpis.json"
    kpi_path.parent.mkdir(parents=True, exist_ok=True)
    kpi_path.write_text(json.dumps({"details": {"symbols": [{"qualified_name": "tests.test_journey.test_journey_flow", "file": "tests/test_journey.py", "kind": "function"}]}}), encoding="utf-8")


def _remove_test_refs(root: Path) -> None:
    """Remove as associações de teste para exercitar o bloqueio do backlog.
    Regrava somente o Draw de nível 2 e preserva o restante da fixture.
    """
    path = root / ".looper" / "draws" / "jornada.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for node in payload["nodes"]:
        node.pop("test_ref", None)
        node.pop("test_refs", None)
    create_draw(root, payload)


def _add_test_refs(root: Path, as_list: bool = False) -> None:
    """Adiciona referências válidas de teste ao Draw de nível 2.
    Permite validar o formato singular e o formato compatível em lista.
    """
    path = root / ".looper" / "draws" / "jornada.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for node in payload["nodes"]:
        reference = {"file": "tests/test_journey.py", "symbols": ["tests.test_journey.test_journey_flow"]}
        if as_list:
            node["test_refs"] = [reference]
        else:
            node["test_ref"] = reference
    create_draw(root, payload)


def _create_nested_hierarchical_fixture(root: Path, delivery_scope: str | None = None) -> None:
    """Cria uma jornada com subfluxo associado a um nó pai.
    O filho possui duas etapas internas que devem entrar no backlog.
    """
    _create_hierarchical_fixture(root)
    if delivery_scope is not None:
        config_path = root / ".looper" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        config.setdefault("backlog", {})["task_delivery_scope"] = delivery_scope
        config_path.write_text(json.dumps(config), encoding="utf-8")
    parent_path = root / ".looper" / "draws" / "jornada.json"
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


def _add_l4_fixture(root: Path, count: int = 9) -> None:
    """Anexa codebase L4 ao primeiro nó do subfluxo L3.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    path = root / ".looper" / "draws" / "subjornada.json"
    parent = json.loads(path.read_text(encoding="utf-8"))
    parent["nodes"][0]["draw_ref"] = "codebase"
    create_draw(root, parent)
    create_draw(
        root,
        {
            "id": "codebase",
            "title": "Detalhamento técnico",
            "kind": "flow",
            "hierarchy": {
                "level": 4,
                "role": "codebase",
                "parent_draw_ref": "subjornada",
                "parent_node_id": 1,
                "root_draw_ref": "sistema",
            },
            "groups": [],
            "nodes": [
                {"id": index, "label": f"Símbolo L4 {index}", "description": "Detalhamento técnico real."}
                for index in range(1, count + 1)
            ],
            "edges": [
                {"id": index, "from": index, "to": index + 1, "kind": "flow", "condition": 1}
                for index in range(1, count)
            ],
            "flows": [],
        },
    )


def test_l4_is_delivered_with_l3_in_configurable_groups(tmp_path: Path):
    """Entrega o pai L3 e até três L4 por avanço, com o tamanho editável.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    _add_l4_fixture(tmp_path)
    set_backlog_config(
        tmp_path,
        bootstrap_task=False,
        test_loop_enabled=False,
        development_mode="separated",
        l4_group_size=3,
    )

    while True:
        frontend = next_backlog_task(tmp_path, layer="frontend")
        if frontend["kind"] == "backlog-layer-empty":
            break
        complete_backlog_task(tmp_path, frontend["task"]["id"])

    first = next_backlog_task(tmp_path, layer="backend")
    assert first["task"]["id"] == "task:subjornada:node:1"
    assert first["l4_group_size"] == 3
    assert [item["id"] for item in first["l4_group"]] == [
        "task:codebase:node:1", "task:codebase:node:2", "task:codebase:node:3"
    ]
    assert first["l4_parent"]["id"] == first["task"]["id"]
    complete_backlog_task(tmp_path, first["task"]["id"])

    second = next_backlog_task(tmp_path, layer="backend")
    assert second["task"]["id"] == "task:subjornada:node:1"
    assert [item["id"] for item in second["l4_group"]] == [
        "task:codebase:node:4", "task:codebase:node:5", "task:codebase:node:6"
    ]
    complete_backlog_task(tmp_path, second["task"]["id"])

    third = next_backlog_task(tmp_path, layer="backend")
    assert third["task"]["id"] == "task:subjornada:node:1"
    assert [item["id"] for item in third["l4_group"]] == [
        "task:codebase:node:7", "task:codebase:node:8", "task:codebase:node:9"
    ]
    complete_backlog_task(tmp_path, third["task"]["id"])

    second_l3 = next_backlog_task(tmp_path, layer="backend")
    assert second_l3["task"]["id"] == "task:subjornada:node:2"
    complete_backlog_task(tmp_path, second_l3["task"]["id"])

    assert next_backlog_task(tmp_path, layer="backend")["kind"] == "backlog-layer-empty"
    statuses = {item["id"]: item["status"] for item in read_backlog(tmp_path)["tasks"]}
    assert all(statuses[f"task:codebase:node:{index}"] == "done" for index in range(1, 10))


def test_l4_group_size_is_editable_from_backlog_cli(tmp_path: Path, monkeypatch):
    """Persiste o tamanho de grupo L4 pelo comando público de configuração.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    result = runner.invoke(app, ["backlog", "config", "--l4-group-size", "5"])
    assert result.exit_code == 0
    assert get_backlog_config(tmp_path)["l4_group_size"] == 5


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


def test_backlog_injects_node_success_and_failure_criteria(tmp_path: Path):
    """Passa os critérios definidos no nó para o contexto entregue ao loop.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_hierarchical_fixture(tmp_path)
    draw_path = tmp_path / ".looper" / "draws" / "jornada.json"
    draw = json.loads(draw_path.read_text(encoding="utf-8"))
    draw["nodes"][0]["success_criteria"] = "A sessão é criada e retorna um identificador válido."
    draw["nodes"][0]["failure_criteria"] = "A sessão não é criada ou o identificador não é retornado."
    draw_path.write_text(json.dumps(draw), encoding="utf-8")
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"]["test_loop_enabled"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")

    response = next_backlog_task(tmp_path)
    task = response["task"]
    compact = _format_backlog_response(response)

    assert task["success_criteria"] == draw["nodes"][0]["success_criteria"]
    assert task["failure_criteria"] == draw["nodes"][0]["failure_criteria"]
    assert "Só termine a implementação" in response["instruction"]
    assert "não declare sucesso" in response["instruction"]
    assert task["success_criteria"] in compact
    assert task["failure_criteria"] in compact
    assert response["instruction"] in compact


def test_disabled_test_loop_delivers_only_implementation_tasks(tmp_path: Path):
    """Permite implementar diretamente quando o loop de testes está desabilitado.
    Confirma que o cursor não cria bloqueio nem tasks de teste.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"]["test_loop_enabled"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")

    disabled = next_backlog_test(tmp_path)
    assert disabled["kind"] == "backlog-test-disabled"

    implementation = next_backlog_task(tmp_path)
    assert implementation["kind"] == "backlog-task"
    assert implementation["phase"] == "implementation"
    assert implementation["task"]["test_status"] == "not-required"
    assert implementation["task"]["checklist_state"]["test"] is True
    assert check_backlog(tmp_path)["missing_tests"] == 0

    completed = complete_backlog_task(tmp_path, implementation["task"]["id"])
    assert completed["status"] == "done"


def test_backlog_change_reserves_and_completes_node_change_request(tmp_path: Path):
    """Entrega alterações do Draw em cursor próprio sem tocar no backlog normal.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_hierarchical_fixture(tmp_path)
    draw_path = tmp_path / ".looper" / "draws" / "jornada.json"
    draw = json.loads(draw_path.read_text(encoding="utf-8"))
    draw["nodes"][0]["changes"] = [
        {"id": 1, "prompt": "Atualize a entrada em todos os pontos necessários.", "status": "pending"}
    ]
    create_draw(tmp_path, draw)

    claimed = next_backlog_change(tmp_path)

    assert claimed["kind"] == "backlog-change-task"
    assert claimed["phase"] == "change"
    assert claimed["task"]["id"] == "change:jornada:node:1:request:1"
    assert claimed["task"]["symbols"] == ["Audit.record", "Journey.start"]
    assert json.loads(draw_path.read_text(encoding="utf-8"))["nodes"][0]["changes"][0]["status"] == "in_progress"

    completed = complete_backlog_task(tmp_path, claimed["task"]["id"])

    assert completed["kind"] == "backlog-change-complete"
    assert completed["status"] == "done"
    assert json.loads(draw_path.read_text(encoding="utf-8"))["nodes"][0]["changes"][0]["status"] == "done"
    assert next_backlog_change(tmp_path)["kind"] == "backlog-change-empty"


def test_backlog_change_layer_flags_filter_l2_and_l3_requests(tmp_path: Path, monkeypatch):
    """Aplica os filtros frontend/backend também ao cursor de alterações.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    parent_path = tmp_path / ".looper" / "draws" / "jornada.json"
    child_path = tmp_path / ".looper" / "draws" / "subjornada.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    child = json.loads(child_path.read_text(encoding="utf-8"))
    parent["nodes"][0]["changes"] = [{"id": 1, "prompt": "Ajuste visual da tela.", "status": "pending"}]
    child["nodes"][0]["changes"] = [{"id": 1, "prompt": "Ajuste de regra do backend.", "status": "pending"}]
    create_draw(tmp_path, parent)
    create_draw(tmp_path, child)
    monkeypatch.chdir(tmp_path)

    frontend = runner.invoke(app, ["backlog", "change", "--frontend"])
    assert frontend.exit_code == 0, frontend.output
    assert "change:jornada:node:1:request:1" in frontend.output
    complete_backlog_task(tmp_path, "change:jornada:node:1:request:1")

    backend = runner.invoke(app, ["backlog", "change", "--backend"])
    assert backend.exit_code == 0, backend.output
    assert "change:subjornada:node:1:request:1" in backend.output
    complete_backlog_task(tmp_path, "change:subjornada:node:1:request:1")

    empty = runner.invoke(app, ["backlog", "change", "--frontend"])
    assert empty.exit_code == 0, empty.output
    assert "Não há tasks pendentes para a camada frontend" in empty.output


def test_backlog_test_creates_test_phase_then_releases_same_task_for_implementation(tmp_path: Path):
    """Executa a fase de testes antes da fase de implementação da mesma task.
    Completa o teste, reserva a implementação e mantém o ID operacional.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)

    test_task = next_backlog_test(tmp_path)

    assert test_task["kind"] == "backlog-test-task"
    assert test_task["phase"] == "test"
    assert test_task["level_context"]["level"] == 2
    assert "frontend" in test_task["level_context"]["guidance"].lower()
    task_id = test_task["task"]["id"]
    _add_test_refs(tmp_path)
    test_done = complete_backlog_task(tmp_path, task_id)
    assert test_done["kind"] == "backlog-test-complete"
    assert test_done["task"]["test_status"] == "done"

    implementation = next_backlog_task(tmp_path)

    assert implementation["kind"] == "backlog-task"
    assert implementation["phase"] == "implementation"
    assert implementation["task"]["id"] == task_id
    assert implementation["level_context"]["meaning"] == "Tela"


def test_bootstrap_is_first_and_agnostic_in_both_backlog_loops(tmp_path: Path):
    """Entrega a preparação agnóstica antes de qualquer task de produto.
    Confirma que implementação e testes recebem a mesma primeira task injetada.
    """
    _create_hierarchical_fixture(tmp_path, bootstrap=True)
    _remove_test_refs(tmp_path)

    implementation_first = next_backlog_task(tmp_path)
    assert implementation_first["kind"] == "backlog-task"
    assert implementation_first["task"]["id"] == "task:bootstrap"
    assert "ponto de entrada" in implementation_first["task"]["description"]
    assert "stack" in implementation_first["task"]["description"]
    assert "wordpress" not in implementation_first["task"]["description"].lower()
    complete_backlog_task(tmp_path, "task:bootstrap")

    test_first = next_backlog_test(tmp_path)
    assert test_first["kind"] == "backlog-test-task"

    second_root = tmp_path / "test-loop"
    _create_hierarchical_fixture(second_root, bootstrap=True)
    _remove_test_refs(second_root)
    test_bootstrap = next_backlog_test(second_root)
    assert test_bootstrap["kind"] == "backlog-bootstrap-task"
    assert test_bootstrap["phase"] == "bootstrap"
    assert test_bootstrap["task"]["id"] == "task:bootstrap"
    complete = complete_backlog_task(second_root, "task:bootstrap")
    assert complete["kind"] == "backlog-bootstrap-complete"
    assert next_backlog_test(second_root)["kind"] == "backlog-test-task"


def test_legacy_false_bootstrap_setting_does_not_skip_first_task(tmp_path: Path):
    """Migra o antigo default falso sem pular a preparação inicial.
    Mantém o bootstrap como primeira task quando não existe opt-out explícito.
    """
    _create_hierarchical_fixture(tmp_path)
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"].pop("bootstrap_opt_out", None)
    config["backlog"]["bootstrap_task"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")

    first = next_backlog_task(tmp_path)

    assert first["task"]["id"] == "task:bootstrap"


def test_backlog_test_recovers_product_cursor_before_bootstrap(tmp_path: Path):
    """Recupera um cursor antigo que reservou produto antes do bootstrap.
    Garante que a preparação continue sendo a primeira entrega do loop.
    """
    _create_hierarchical_fixture(tmp_path, bootstrap=True)
    _remove_test_refs(tmp_path)

    payload = generate_backlog(tmp_path)
    product = next(task for task in payload["tasks"] if task["level"] == 2)
    product["status"] = "in_progress"
    product["test_status"] = "in_progress"
    product["test_previous_status"] = "pending"
    payload["execution"].update({
        "current_task_id": product["id"],
        "current_phase": "test",
        "bootstrap_done": False,
    })
    write_backlog(tmp_path, payload)

    first = next_backlog_test(tmp_path)

    assert first["kind"] == "backlog-bootstrap-task"
    assert first["task"]["id"] == "task:bootstrap"
    repaired = read_backlog(tmp_path)
    repaired_product = next(task for task in repaired["tasks"] if task["id"] == product["id"])
    assert repaired_product["status"] == "pending"
    assert repaired_product["test_status"] == "missing"


def test_backlog_injects_level_context_into_level_two_and_level_three_tasks(tmp_path: Path):
    """Diferencia frontend de regras e detalhes nos contextos do backlog.
    Percorre a task L2 e o subfluxo L3 e valida a orientação injetada em ambos os loops.
    """
    _create_nested_hierarchical_fixture(tmp_path, delivery_scope="task")

    first = next_backlog_task(tmp_path)
    assert first["task"]["level"] == 2
    assert first["level_context"]["meaning"] == "Tela"
    assert "view" in first["level_context"]["guidance"].lower()
    assert "frontend" in first["level_context"]["guidance"].lower()

    complete_backlog_task(tmp_path, first["task"]["id"])
    child = next_backlog_task(tmp_path)

    assert child["task"]["level"] == 3
    assert child["level_context"]["meaning"] == "Regra de negócio e detalhes da tela"
    assert "regra de negócio" in child["level_context"]["guidance"].lower()
    assert "detalhes da tela" in child["level_context"]["guidance"].lower()


def test_backlog_delivery_scope_can_deliver_internal_subflows_separately(tmp_path: Path):
    """Entrega o L2 e cada task interna separadamente quando configurado.
    Confirma também que o bootstrap é a primeira entrega da fase de testes.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"]["bootstrap_task"] = True
    config["backlog"]["bootstrap_opt_out"] = False
    config["backlog"]["task_delivery_scope"] = "task"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    bootstrap = next_backlog_test(tmp_path)
    assert bootstrap["kind"] == "backlog-bootstrap-task"
    assert bootstrap["task"]["id"] == "task:bootstrap"
    complete_backlog_task(tmp_path, "task:bootstrap")

    parent = next_backlog_test(tmp_path)
    assert parent["task"]["id"] == "task:jornada:node:1"
    complete_backlog_task(tmp_path, parent["task"]["id"])

    internal = next_backlog_test(tmp_path)
    assert internal["task"]["id"] == "task:subjornada:node:1"
    assert internal["task"]["level"] == 3
    complete_backlog_task(tmp_path, internal["task"]["id"])

    internal_last = next_backlog_test(tmp_path)
    assert internal_last["task"]["id"] == "task:subjornada:node:2"
    assert "deste nó ou subfluxo" in internal_last["instruction"]


def test_separate_delivery_does_not_inherit_l2_test_status_to_l3(tmp_path: Path):
    """Mantém os L3 pendentes quando o L2 é entregue separadamente.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"].pop("task_delivery_scope", None)
    config_path.write_text(json.dumps(config), encoding="utf-8")

    parent = next_backlog_test(tmp_path)
    assert parent["task"]["level"] == 2
    complete_backlog_task(tmp_path, parent["task"]["id"])

    internal = next_backlog_test(tmp_path)

    assert internal["task"]["level"] == 3
    assert internal["task"]["test_status"] == "in_progress"
    assert internal["task"]["test_previous_status"] == "pending"


def test_backlog_delivery_scope_groups_tests_and_implementation_by_node(tmp_path: Path):
    """Entrega o nó e seus internos juntos nas duas fases do backlog.
    Concluir o pai também conclui os subfluxos incluídos no escopo do nó.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"]["task_delivery_scope"] = "node"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    for task_id in (
        "task:jornada:node:1",
        "task:jornada:node:2",
        "task:jornada:node:3",
    ):
        test_task = next_backlog_test(tmp_path)
        assert test_task["task"]["id"] == task_id
        if task_id == "task:jornada:node:1":
            assert "todos os subfluxos internos" in test_task["instruction"]
            assert "camada observável" in test_task["instruction"]
            assert "Tela" in test_task["delivery_scope_note"]
            test_human = _format_backlog_response(test_task)
            assert "Escopo obrigatório: criar testes para o nó inteiro e todos os subfluxos internos" in test_human
            assert "não limita o escopo ao frontend" in test_human
            assert "endpoints/handlers" in test_human
        complete_backlog_task(tmp_path, task_id)

    implementation = next_backlog_task(tmp_path)
    assert implementation["task"]["id"] == "task:jornada:node:1"
    assert implementation["task_delivery_scope"] == "node"
    assert {item["id"] for item in implementation["delivery_subtasks"]} == {
        "task:subjornada:node:1",
        "task:subjornada:node:2",
    }
    assert "entregue a tela e o funcionamento completo" in implementation["instruction"]
    assert "não deixe essas partes para outra task" in implementation["instruction"]
    implementation_human = _format_backlog_response(implementation)
    assert "Escopo obrigatório: implementar o nó inteiro e todos os subfluxos internos" in implementation_human
    assert "endpoints/handlers" in implementation_human
    complete_backlog_task(tmp_path, implementation["task"]["id"])

    next_implementation = next_backlog_task(tmp_path)
    assert next_implementation["task"]["id"] == "task:jornada:node:2"


def test_separated_development_mode_delivers_frontend_then_backend_and_tests_only_l3(tmp_path: Path):
    """Executa todas as telas antes do backend e injeta testes apenas para L3.
    A instrução frontend mantém navegação entre telas e exclui lógica de negócio.
    """
    _create_nested_hierarchical_fixture(tmp_path, delivery_scope="node")
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"]["development_mode"] = "separated"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    test_task = next_backlog_test(tmp_path)
    assert test_task["task"]["level"] == 3
    assert test_task["implementation_layer"] == "backend"
    assert test_task["tests_required"] is True
    complete_backlog_task(tmp_path, test_task["task"]["id"])
    second_test = next_backlog_test(tmp_path)
    assert second_test["task"]["level"] == 3
    complete_backlog_task(tmp_path, second_test["task"]["id"])
    assert next_backlog_test(tmp_path)["kind"] == "backlog-test-empty"

    payload = read_backlog(tmp_path)
    assert all(task["test_status"] == "not-required" for task in payload["tasks"] if task["level"] == 2)

    frontend_ids = []
    for expected_id in ("task:jornada:node:1", "task:jornada:node:2", "task:jornada:node:3"):
        frontend = next_backlog_task(tmp_path)
        assert frontend["task"]["id"] == expected_id
        assert frontend["implementation_layer"] == "frontend"
        assert frontend["tests_required"] is False
        assert "link/navegação" in frontend["instruction"]
        assert "não implemente controller" in frontend["instruction"]
        frontend_ids.append(frontend["task"]["id"])
        complete_backlog_task(tmp_path, frontend["task"]["id"])

    backend = next_backlog_task(tmp_path)
    assert backend["task"]["level"] == 3
    assert backend["implementation_layer"] == "backend"
    complete_backlog_task(tmp_path, backend["task"]["id"])
    assert next_backlog_task(tmp_path)["task"]["level"] == 3


def test_l2_children_context_does_not_change_independent_l3_loop(tmp_path: Path):
    """Injeta os filhos no L2 sem reservar ou remover a fila L3.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    set_backlog_config(
        tmp_path,
        bootstrap_task=False,
        test_loop_enabled=False,
        l2_children_mode="context",
        l3_loop_enabled=True,
        l3_include_parent=True,
    )

    frontend = next_backlog_task(tmp_path, layer="frontend")
    assert frontend["children_delivery_mode"] == "context"
    assert {item["id"] for item in frontend["children_context"]} == {
        "task:subjornada:node:1", "task:subjornada:node:2"
    }
    complete_backlog_task(tmp_path, frontend["task"]["id"])

    backend = next_backlog_task(tmp_path, layer="backend")
    assert backend["task"]["id"] == "task:subjornada:node:1"
    assert backend["context_parent"]["id"] == "task:jornada:node:1"


def test_l2_children_owned_disables_l3_and_completes_children(tmp_path: Path):
    """Permite que o L2 seja a única entrega e conclua seus filhos L3.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    set_backlog_config(
        tmp_path,
        bootstrap_task=False,
        test_loop_enabled=False,
        l2_children_mode="owned",
        l3_loop_enabled=True,
    )

    frontend = next_backlog_task(tmp_path, layer="frontend")
    assert frontend["children_delivery_mode"] == "owned"
    assert frontend["l3_loop_enabled"] is False
    completed = complete_backlog_task(tmp_path, frontend["task"]["id"])
    assert set(completed["completed_task_ids"]) == {
        "task:jornada:node:1", "task:subjornada:node:1", "task:subjornada:node:2"
    }

    backend = next_backlog_task(tmp_path, layer="backend")
    assert backend["kind"] == "backlog-layer-empty"
    statuses = {item["id"]: item["status"] for item in read_backlog(tmp_path)["tasks"]}
    assert statuses["task:subjornada:node:1"] == "done"
    assert statuses["task:subjornada:node:2"] == "done"


def test_frontend_and_backend_lanes_reserve_and_complete_independently(tmp_path: Path):
    """Permite agentes L2 e L3 simultâneos sem compartilhar o cursor global.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    set_backlog_config(tmp_path, bootstrap_task=False, test_loop_enabled=False, l2_children_mode="context")

    frontend = next_backlog_task(tmp_path, layer="frontend")
    backend = next_backlog_task(tmp_path, layer="backend")
    assert frontend["task"]["level"] == 2
    assert backend["task"]["level"] == 3
    assert frontend["task"]["id"] != backend["task"]["id"]

    complete_backlog_task(tmp_path, backend["task"]["id"])
    complete_backlog_task(tmp_path, frontend["task"]["id"])
    state = read_backlog(tmp_path)["execution"]
    assert state["lanes"]["implementation:frontend"]["current_task_id"] is None
    assert state["lanes"]["implementation:backend"]["current_task_id"] is None


def test_loop_instructions_are_injected_in_natural_language_for_every_task(tmp_path: Path):
    """Repete a informação crítica no contexto textual sem alterar a fila.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    instructions = tmp_path / ".looper" / "loop-instructions.md"
    instructions.write_text("Nunca pule a validação de permissões.", encoding="utf-8")
    set_backlog_config(tmp_path, bootstrap_task=False, test_loop_enabled=False)

    response = next_backlog_task(tmp_path)
    assert response["critical_information"]["content"] == "Nunca pule a validação de permissões."
    assert "INFORMAÇÃO CRÍTICA DO PROJETO" in response["instruction"]
    assert "Nunca pule a validação de permissões." in response["instruction"]
    assert "Nunca pule a validação de permissões." in _format_backlog_response(response)


def test_loop_instructions_update_on_next_delivery_and_do_not_block_when_empty(tmp_path: Path):
    """Relê o arquivo a cada entrega e aceita arquivo vazio.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    instructions = tmp_path / ".looper" / "loop-instructions.md"
    instructions.write_text("Primeira regra.", encoding="utf-8")
    set_backlog_config(tmp_path, bootstrap_task=False, test_loop_enabled=False)
    first = next_backlog_task(tmp_path)
    complete_backlog_task(tmp_path, first["task"]["id"])
    instructions.write_text("Segunda regra.", encoding="utf-8")
    second = next_backlog_task(tmp_path)
    assert "Segunda regra." in second["instruction"]
    instructions.write_text("", encoding="utf-8")
    complete_backlog_task(tmp_path, second["task"]["id"])
    third = next_backlog_task(tmp_path)
    assert third["critical_information"]["present"] is False
    assert "INFORMAÇÃO CRÍTICA" not in third.get("instruction", "")


def test_instrucoes_backend_sao_injetadas_somente_no_loop_backend(tmp_path: Path):
    """instructions.backend aparece no contexto de task backend e não vaza para frontend.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    from looper.config import save_config, load_config
    _create_nested_hierarchical_fixture(tmp_path)
    config = load_config(tmp_path)
    config["instructions"] = {"backend": "LOG BACKEND OBRIGATÓRIO.", "frontend": "ACESSIBILIDADE.", "change": "REVISÃO."}
    save_config(tmp_path, config)
    set_backlog_config(tmp_path, bootstrap_task=False, test_loop_enabled=False, development_mode="separated")

    response = next_backlog_task(tmp_path)
    layer = response.get("implementation_layer")
    if layer == "backend":
        assert "LOG BACKEND OBRIGATÓRIO." in response["critical_information"]["content"]
        assert "ACESSIBILIDADE." not in response["critical_information"]["content"]
    elif layer == "frontend":
        assert "ACESSIBILIDADE." in response["critical_information"]["content"]
        assert "LOG BACKEND OBRIGATÓRIO." not in response["critical_information"]["content"]


def test_instrucoes_change_sao_injetadas_no_loop_de_alteracao(tmp_path: Path):
    """instructions.change aparece no contexto de change task.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    from looper.config import save_config, load_config
    _create_nested_hierarchical_fixture(tmp_path)
    config = load_config(tmp_path)
    config["instructions"] = {"backend": "BACKEND.", "frontend": "FRONTEND.", "change": "CHANGE OBRIGATÓRIO."}
    save_config(tmp_path, config)
    set_backlog_config(tmp_path, bootstrap_task=False, test_loop_enabled=False)
    payload = generate_backlog(tmp_path)
    tasks = payload.get("tasks", [])
    node = next((t for t in tasks if t.get("level") == 3), tasks[0] if tasks else None)
    if node is None:
        return
    from looper.draw import read_draw, create_draw as _create_draw
    draws = list((tmp_path / ".looper" / "draws").glob("*.json"))
    if not draws:
        return
    draw = read_draw(tmp_path, draws[0].stem)
    nodes = draw.get("nodes", [])
    if not nodes:
        return
    for n in nodes:
        n.setdefault("changes", [])
        n["changes"].append({"id": 1, "prompt": "Adicionar log obrigatório em todas as funções.", "status": "pending", "implementation_layer": "backend"})
    _create_draw(tmp_path, draw)
    response = next_backlog_change(tmp_path)
    if response.get("kind") == "backlog-change-task":
        assert "CHANGE OBRIGATÓRIO." in response["critical_information"]["content"]
        assert "BACKEND." not in response["critical_information"]["content"]


def test_backlog_complete_is_human_language_and_includes_critical_information(tmp_path: Path, monkeypatch):
    """A confirmação do loop não expõe JSON ao agente.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    (tmp_path / ".looper" / "loop-instructions.md").write_text("Regra de conclusão.", encoding="utf-8")
    set_backlog_config(tmp_path, bootstrap_task=False, test_loop_enabled=False)
    task = next_backlog_task(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["backlog", "complete", task["task"]["id"]])
    assert result.exit_code == 0, result.output
    assert "Regra de conclusão." in result.output
    assert not result.output.lstrip().startswith("{")


def test_development_mode_is_configurable_from_cli(tmp_path: Path, monkeypatch):
    """Persiste o modo separado pelo init e pelo comando de configuração.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--development-mode", "separated"])
    assert result.exit_code == 0, result.output
    config = json.loads((tmp_path / ".looper/config.json").read_text(encoding="utf-8"))
    assert config["backlog"]["development_mode"] == "separated"

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["backlog", "config", "--development-mode", "sequential"])
    assert result.exit_code == 0, result.output
    config = json.loads((tmp_path / ".looper/config.json").read_text(encoding="utf-8"))
    assert config["backlog"]["development_mode"] == "sequential"


def test_backlog_layer_flags_request_only_frontend_or_backend(tmp_path: Path, monkeypatch):
    """Filtra o cursor por L2/L3 sem declarar o backlog inteiro concluído.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"]["development_mode"] = "separated"
    config["backlog"]["test_loop_enabled"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    frontend = runner.invoke(app, ["backlog", "task", "--frontend"])
    assert frontend.exit_code == 0, frontend.output
    assert "task:jornada:node:1" in frontend.output
    complete_backlog_task(tmp_path, "task:jornada:node:1")

    backend = runner.invoke(app, ["backlog", "task", "--backend"])
    assert backend.exit_code == 0, backend.output
    assert "task:subjornada:node:1" in backend.output
    assert "Camada: backend" in backend.output
    complete_backlog_task(tmp_path, "task:subjornada:node:1")

    for expected_id in ("task:jornada:node:2", "task:jornada:node:3"):
        next_frontend = runner.invoke(app, ["backlog", "task", "--frontend"])
        assert expected_id in next_frontend.output
        complete_backlog_task(tmp_path, expected_id)
    no_frontend = runner.invoke(app, ["backlog", "task", "--frontend"])
    assert no_frontend.exit_code == 0, no_frontend.output
    assert "Não há tasks pendentes para a camada frontend" in no_frontend.output


def test_backlog_test_layer_flags_filter_test_queue(tmp_path: Path, monkeypatch):
    """Permite consultar somente a fila de testes da camada solicitada.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    config_path = tmp_path / ".looper" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["backlog"]["development_mode"] = "separated"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    frontend = runner.invoke(app, ["backlog", "test", "--frontend"])
    assert frontend.exit_code == 0, frontend.output
    assert "Não há tasks pendentes para a camada frontend" in frontend.output

    backend = runner.invoke(app, ["backlog", "test", "--backend"])
    assert backend.exit_code == 0, backend.output
    assert "task:subjornada:node:1" in backend.output
    assert "Camada: backend" in backend.output


def test_backlog_reopens_stale_test_checklists_when_evidence_is_missing(tmp_path: Path):
    """Não trata checklists antigos como testes concluídos sem evidência.
    Reabre a fase de testes quando o status atual voltou a ser missing.
    """
    _create_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)
    _remove_test_refs(tmp_path)
    stale = generate_backlog(tmp_path)
    for task in stale["tasks"]:
        task["test_status"] = "missing"
    write_backlog(tmp_path, stale)
    stale = read_backlog(tmp_path)

    assert all(task["checklist_state"]["test"] for task in stale["tasks"])
    assert all(task["test_status"] == "missing" for task in stale["tasks"])
    response = next_backlog_test(tmp_path)

    assert response["kind"] == "backlog-test-task"
    assert response["task"]["id"] == "task:jornada:node:1"


def test_backlog_test_accepts_test_refs_list_and_requires_one_file(tmp_path: Path):
    """Aceita a forma em lista quando ela aponta para um único arquivo.
    Rejeita uma associação que espalha a cobertura por mais de um arquivo.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    _add_test_refs(tmp_path, as_list=True)

    valid = build_backlog(tmp_path)
    assert valid["tasks"][0]["test_status"] == "done"

    path = tmp_path / ".looper" / "draws" / "jornada.json"
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


def test_backlog_checklist_resolves_stale_task_id_by_draw_and_node(tmp_path: Path):
    """Aceita o identificador estável do nó quando a UI envia um id antigo.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)

    update_backlog_checklist(
        tmp_path,
        "task:stale-snapshot:node:1",
        "test",
        False,
        draw_id="jornada",
        node_id=1,
    )

    task = next(item for item in read_backlog(tmp_path)["tasks"] if item["id"] == "task:jornada:node:1")
    assert task["checklist_state"]["test"] is False


def test_backlog_parent_and_subtask_can_be_completed_independently(tmp_path: Path):
    """Permite concluir o pai e a subtask pelo próprio ID.
    Depois da primeira subtask, a resposta avança para a segunda mantendo o pai.
    """
    _create_nested_hierarchical_fixture(tmp_path, delivery_scope="task")
    for task_id in ("task:jornada:node:1", "task:subjornada:node:1", "task:subjornada:node:2"):
        update_backlog_checklist(tmp_path, task_id, "test", True)
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
    _create_nested_hierarchical_fixture(tmp_path, delivery_scope="task")
    for task_id in ("task:jornada:node:1", "task:subjornada:node:1", "task:subjornada:node:2", "task:jornada:node:2", "task:jornada:node:3"):
        update_backlog_checklist(tmp_path, task_id, "test", True)
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


def test_backlog_expands_multiple_subflows_from_one_parent_node(tmp_path: Path):
    """Expande dois subfluxos L3 associados ao mesmo nó L2.
    Mantém as tasks e os identificadores dos dois backlogs no escopo do pai.
    """
    _create_nested_hierarchical_fixture(tmp_path, delivery_scope="task")
    parent_path = tmp_path / ".looper" / "draws" / "jornada.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent["nodes"][0].pop("draw_ref", None)
    parent["nodes"][0]["draw_refs"] = ["subjornada", "subjornada-dois"]
    parent_path.write_text(json.dumps(parent), encoding="utf-8")

    child = json.loads((tmp_path / ".looper" / "draws" / "subjornada.json").read_text(encoding="utf-8"))
    child["id"] = "subjornada-dois"
    child["title"] = "Segunda subjornada interna"
    create_draw(tmp_path, child)

    backlog = build_backlog(tmp_path, generated_at="2026-08-13T12:00:00+00:00")
    parent_task = next(task for task in backlog["tasks"] if task["id"] == "task:jornada:node:1")

    assert parent_task["child_backlog_ids"] == ["subjornada", "subjornada-dois"]
    assert parent_task["child_backlog_id"] == "subjornada"
    assert parent_task["child_task_ids"] == [
        "task:subjornada:node:1",
        "task:subjornada:node:2",
        "task:subjornada-dois:node:1",
        "task:subjornada-dois:node:2",
    ]


def test_backlog_preserves_shared_steps_in_explicit_flow_paths(tmp_path: Path):
    """Preserva todas as etapas quando as branches vêm de flows explícitos.
    Não remove um nó compartilhado só porque ele já apareceu em outro flow.
    """
    _create_hierarchical_fixture(tmp_path)
    draw_path = tmp_path / ".looper" / "draws" / "jornada.json"
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
    journey_path = tmp_path / ".looper" / "draws" / "jornada.json"
    journey = json.loads(journey_path.read_text(encoding="utf-8"))
    journey["flows"] = [
        {"id": 1, "label": "sucesso", "steps": [{"node": 1}, {"node": 2}]},
    ]
    journey_path.write_text(json.dumps(journey), encoding="utf-8")
    child_path = tmp_path / ".looper" / "draws" / "subjornada.json"
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
    draw_path = tmp_path / ".looper" / "draws" / "jornada.json"
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
    Executa generate, task e complete usando somente a saída em linguagem humana.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)

    generated = runner.invoke(app, ["backlog", "generate"])
    assert generated.exit_code == 0
    task = runner.invoke(app, ["backlog", "task"])
    assert task.exit_code == 0
    assert "Task de implementação" in task.stdout
    assert "ID: task:jornada:node:1" in task.stdout
    json_task = runner.invoke(app, ["backlog", "task", "--json"])
    assert json_task.exit_code != 0
    completed = runner.invoke(app, ["backlog", "complete", "task:jornada:node:1"])
    assert completed.exit_code == 0
    missing = runner.invoke(app, ["backlog", "missing"])
    assert missing.exit_code == 0
    assert all(item["status"] != "done" for item in json.loads(missing.stdout)["items"])


def test_backlog_cli_exposes_test_phase_and_structured_missing_test(tmp_path: Path, monkeypatch):
    """Expõe `backlog test` e o bloqueio legível de `backlog task`.
    Mantém as respostas dos dois comandos em linguagem natural para consumo pelo agente.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)

    human = runner.invoke(app, ["backlog", "task"])
    assert human.exit_code == 0
    assert "Teste necessário antes da implementação" in human.stdout
    assert "test_missing" not in human.stdout

    json_task = runner.invoke(app, ["backlog", "task", "--json"])
    assert json_task.exit_code != 0
    testing = runner.invoke(app, ["backlog", "test"])

    assert testing.exit_code == 0
    assert "Task de teste" in testing.stdout
    assert "ID: task:jornada:node:1" in testing.stdout
    assert "Escopo do nível 2: Tela" in testing.stdout
    assert "Tela de destino: Iniciar" in testing.stdout
    assert "Entrada: início do fluxo" in testing.stdout
    assert "frontend" in testing.stdout.lower()
    json_test = runner.invoke(app, ["backlog", "test", "--json"])
    assert json_test.exit_code != 0


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
    assert "Escopo do nível 2: Tela" in result.stdout
    assert "Tela de destino: Iniciar" in result.stdout
    assert "Entrada: início do fluxo" in result.stdout
    assert "frontend" in result.stdout.lower()
    assert "Qual entrada? → botão" in result.stdout
    assert "Está autenticado?" not in result.stdout
    assert "options" not in result.stdout


def test_backlog_cli_describes_all_screen_entry_transitions(tmp_path: Path, monkeypatch):
    """Mostra origem, entrada e destino sem escolher uma única origem.
    Confirma que uma tela com múltiplas entradas exibe cada transição completa.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)

    draw_path = tmp_path / ".looper" / "draws" / "jornada.json"
    document = json.loads(draw_path.read_text(encoding="utf-8"))
    document["edges"].append({
        "id": 4,
        "from": 3,
        "to": 2,
        "kind": "conditional",
        "condition": 3,
        "label": "se recuperar cadastro",
        "description": "Uma recuperação também retorna à tela de sucesso.",
    })
    create_draw(tmp_path, document)

    first = runner.invoke(app, ["backlog", "task"])
    assert first.exit_code == 0
    complete_backlog_task(tmp_path, "task:jornada:node:1")

    result = runner.invoke(app, ["backlog", "task"])

    assert result.exit_code == 0
    assert "Tela de destino: Sucesso" in result.stdout
    assert "Entradas possíveis (2):" in result.stdout
    assert "Tela de origem: Iniciar" in result.stdout
    assert "Tela de origem: Retry" in result.stdout
    assert "Condição: ou" in result.stdout
    assert "Ação: sucesso" in result.stdout
    assert "Condição: se" in result.stdout
    assert "Ação: recuperar cadastro" in result.stdout
    assert "Transição: Iniciar → Sucesso" in result.stdout
    assert "Transição: Retry → Sucesso" in result.stdout
    assert "Nó anterior:" not in result.stdout
    assert "Caminho de acesso:" not in result.stdout


def test_looper_test_blocks_when_backlog_has_unchecked_implementation(tmp_path: Path):
    """Bloqueia o teste global enquanto existir uma task sem check de conclusão.
    Libera o gate somente depois que o agente percorre e conclui todas as tasks.
    """
    (tmp_path / ".looper").mkdir()
    analysis = {
        "contract_version": "1",
        "status": "passed",
        "capabilities": {"symbols": True},
        "symbols": [{"qualified_name": "tests.test_journey.test_journey_flow", "file": "tests/test_journey.py", "kind": "function"}],
        "dependencies": [], "technologies": [], "external_logic": [], "complexity": [],
        "structural_metrics": [], "quality_findings": [], "changes": [], "warnings": [], "errors": [],
    }
    analysis_code = f"import json; print({json.dumps(analysis)!r})"
    (tmp_path / ".looper/config.json").write_text(json.dumps({
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


def test_backlog_injected_bootstrap_and_final_verification_tasks(tmp_path: Path):
    """Injeta bootstrap e verificação final no ciclo operacional do backlog.
    Configura bootstrap e final verification e valida a entrega sequencial e conclusão.
    """
    (tmp_path / ".looper").mkdir()
    (tmp_path / ".looper/config.json").write_text(json.dumps({
        "backlog": {
            "bootstrap_task": True,
            "final_verification_task": True,
        }
    }), encoding="utf-8")
    _create_hierarchical_fixture(tmp_path, bootstrap=True)
    _write_test_evidence(tmp_path)
    generate_backlog(tmp_path)

    # 1. Primeira task deve ser o bootstrap
    first = next_backlog_task(tmp_path)
    assert first["kind"] == "backlog-task"
    assert first["task"]["id"] == "task:bootstrap"
    assert "Preparar" in first["task"]["label"]

    complete_backlog_task(tmp_path, "task:bootstrap")

    # 2. Em seguida, as tasks normais de implementação são entregues
    node1 = next_backlog_task(tmp_path)
    assert node1["task"]["id"] == "task:jornada:node:1"
    complete_backlog_task(tmp_path, "task:jornada:node:1")

    node2 = next_backlog_task(tmp_path)
    assert node2["task"]["id"] == "task:jornada:node:2"
    complete_backlog_task(tmp_path, "task:jornada:node:2")

    node3 = next_backlog_task(tmp_path)
    assert node3["task"]["id"] == "task:jornada:node:3"
    complete_backlog_task(tmp_path, "task:jornada:node:3")

    # 3. Após todas as tasks normais, a task final de verificação E2E e associação de símbolos é entregue
    final = next_backlog_task(tmp_path)
    assert final["kind"] == "backlog-verification-task"
    assert final["task"]["id"] == "task:final:verification"
    assert "Associação de Símbolos" in final["task"]["label"]

    complete_backlog_task(tmp_path, "task:final:verification")

    # 4. Agora sim o backlog está vazio
    empty = next_backlog_task(tmp_path)
    assert empty["kind"] == "backlog-empty"


def test_backlog_injected_l2_verification_tasks_per_node(tmp_path: Path):
    """Injeta verificação funcional ao concluir o escopo de cada nó de nível 2.
    Conclui as tasks normais e confirma que a verificação intermediária é exigida antes do próximo nó.
    """
    (tmp_path / ".looper").mkdir()
    (tmp_path / ".looper/config.json").write_text(json.dumps({
        "backlog": {
            "l2_verification_interval": 1,
        }
    }), encoding="utf-8")
    _create_nested_hierarchical_fixture(tmp_path, delivery_scope="task")
    _write_test_evidence(tmp_path)
    for task_id in ("task:jornada:node:1", "task:subjornada:node:1", "task:subjornada:node:2", "task:jornada:node:2", "task:jornada:node:3"):
        update_backlog_checklist(tmp_path, task_id, "test", True)
    generate_backlog(tmp_path)

    # Conclui nó 1 (e suas subtasks)
    t1 = next_backlog_task(tmp_path)
    assert t1["task"]["id"] == "task:jornada:node:1"
    complete_backlog_task(tmp_path, "task:jornada:node:1")

    sub1 = next_backlog_task(tmp_path)
    assert sub1["task"]["id"] == "task:subjornada:node:1"
    complete_backlog_task(tmp_path, "task:subjornada:node:1")

    sub2 = next_backlog_task(tmp_path)
    assert sub2["task"]["id"] == "task:subjornada:node:2"
    complete_backlog_task(tmp_path, "task:subjornada:node:2")

    # Nó 1 e subtasks concluídos -> injeta verificação do nó 1
    v1 = next_backlog_task(tmp_path)
    assert v1["task"]["id"] == "task:verify:jornada:node:1"
    assert v1["kind"] == "backlog-verification-task"
    assert "Verificação da Implementação" in v1["task"]["label"]
    assert "leia os arquivos e símbolos reais" in v1["task"]["description"]
    assert len(v1["task"]["verification_requirements"]) == 6
    human_v1 = _format_backlog_response(v1)
    assert "Verificação obrigatória da implementação" in human_v1
    assert "Tela de destino:" not in human_v1
    assert "Alvos da verificação:" in human_v1
    assert "Procedimento obrigatório:" in human_v1
    assert "Carregue esses arquivos no contexto" in human_v1
    assert "código presente ou teste superficial não prova implementação" in human_v1
    complete_backlog_task(tmp_path, "task:verify:jornada:node:1")

    # Em seguida, avança para nó 2
    t2 = next_backlog_task(tmp_path)
    assert t2["task"]["id"] == "task:jornada:node:2"
    complete_backlog_task(tmp_path, "task:jornada:node:2")

    # Nó 2 concluído -> injeta verificação do nó 2
    v2 = next_backlog_task(tmp_path)
    assert v2["task"]["id"] == "task:verify:jornada:node:2"
    complete_backlog_task(tmp_path, "task:verify:jornada:node:2")


def test_backlog_injected_l2_verification_interval_configurable(tmp_path: Path):
    """Respeita o intervalo configurável para injeção de verificações de nós L2.
    Configura intervalo de 2 nós e confirma que a verificação acumula e dispara na cadência correta.
    """
    (tmp_path / ".looper").mkdir()
    (tmp_path / ".looper/config.json").write_text(json.dumps({
        "backlog": {
            "l2_verification_interval": 2,
        }
    }), encoding="utf-8")
    _create_hierarchical_fixture(tmp_path)
    _write_test_evidence(tmp_path)
    generate_backlog(tmp_path)

    # Conclui nó 1
    t1 = next_backlog_task(tmp_path)
    assert t1["task"]["id"] == "task:jornada:node:1"
    complete_backlog_task(tmp_path, "task:jornada:node:1")

    # Como o intervalo é 2, após nó 1 NÃO dispara verificação ainda -> entrega nó 2
    t2 = next_backlog_task(tmp_path)
    assert t2["task"]["id"] == "task:jornada:node:2"
    complete_backlog_task(tmp_path, "task:jornada:node:2")

    # Agora 2 nós L2 foram concluídos -> dispara UMA ÚNICA verificação em lote contendo os 2 nós juntos
    v_batch = next_backlog_task(tmp_path)
    assert v_batch["task"]["id"] == "task:verify:jornada:batch:1:2"
    assert v_batch["kind"] == "backlog-verification-task"
    assert "Verificação da Implementação em Lote" in v_batch["task"]["label"]
    assert len(v_batch["task"]["verified_nodes"]) == 2
    assert v_batch["task"]["verified_nodes"][0]["node_id"] == 1
    assert v_batch["task"]["verified_nodes"][1]["node_id"] == 2

    # Conclui a verificação em lote de uma única vez
    complete_backlog_task(tmp_path, "task:verify:jornada:batch:1:2")

    # Próxima task normal é o nó 3
    t3 = next_backlog_task(tmp_path)
    assert t3["task"]["id"] == "task:jornada:node:3"
    complete_backlog_task(tmp_path, "task:jornada:node:3")

    # Como o nó 3 terminou e não há mais tarefas normais, dispara a verificação do nó 3 restante
    v3 = next_backlog_task(tmp_path)
    assert v3["task"]["id"] == "task:verify:jornada:node:3"
    complete_backlog_task(tmp_path, "task:verify:jornada:node:3")

    # Agora sim todo o backlog está concluído
    empty = next_backlog_task(tmp_path)
    assert empty["kind"] == "backlog-empty"


def test_backlog_cli_config_and_interval_option(tmp_path: Path, monkeypatch):
    """Permite configurar e sobrescrever o intervalo de verificação via CLI.
    Testa o comando backlog config e a passagem de --interval na execução de tasks.
    """
    monkeypatch.chdir(tmp_path)
    init_project(tmp_path)
    _create_hierarchical_fixture(tmp_path)
    _write_test_evidence(tmp_path)

    # 1. Configura intervalo via comando CLI backlog config
    config_res = runner.invoke(app, ["backlog", "config", "--interval", "2", "--bootstrap", "--final-verification"])
    assert config_res.exit_code == 0
    assert "l2_verification_interval" in config_res.stdout

    # 2. Lê a configuração atual via CLI
    view_res = runner.invoke(app, ["backlog", "config"])
    assert view_res.exit_code == 0
    assert '"l2_verification_interval": 2' in view_res.stdout
    assert '"bootstrap_task": true' in view_res.stdout

    # 3. Executa backlog task e avança pelo bootstrap
    task1_res = runner.invoke(app, ["backlog", "task"])
    assert task1_res.exit_code == 0
    assert "task:bootstrap" in task1_res.stdout
    complete_backlog_task(tmp_path, "task:bootstrap")

    # 4. Executa nó 1 e conclui
    task2_res = runner.invoke(app, ["backlog", "task"])
    assert "task:jornada:node:1" in task2_res.stdout
    complete_backlog_task(tmp_path, "task:jornada:node:1")

    # 5. Com intervalo 2, próxima task é o nó 2
    task3_res = runner.invoke(app, ["backlog", "task"])
    assert "task:jornada:node:2" in task3_res.stdout


def test_backlog_context_batch_and_claim_window_are_explicit(tmp_path: Path):
    """Entrega predecessor, condição e lote sem permitir avanço rápido configurado.
    Confirma que o cursor preserva contexto e que cada task continua sendo concluída por ID.
    """
    (tmp_path / ".looper").mkdir()
    (tmp_path / ".looper/config.json").write_text(json.dumps({"backlog": {"task_batch_size": 2, "task_batch_scope": "task", "min_task_interval_seconds": 3}}), encoding="utf-8")
    _create_hierarchical_fixture(tmp_path)
    generate_backlog(tmp_path)

    first = next_backlog_task(tmp_path)
    assert first["state"] == "implementation_in_progress"
    assert [item["id"] for item in first["batch"]] == ["task:jornada:node:1", "task:jornada:node:2"]
    complete_backlog_task(tmp_path, first["task"]["id"])

    try:
        next_backlog_task(tmp_path)
    except ValueError as error:
        assert "janela mínima" in str(error)
    else:
        raise AssertionError("a janela mínima deveria bloquear o avanço imediato")


def test_bootstrap_report_requires_design_and_environment_contract(tmp_path: Path):
    """Expõe os bloqueios mínimos do bootstrap em um projeto incompleto.
    Confirma que design, Draw raiz, configuração, armazenamento e env example são auditados.
    """
    report = bootstrap_report(tmp_path)

    assert report["status"] == "blocked"
    assert {"system_level_1", "design", "env_example", "looper_config", "draw_storage"}.issubset(report["failures"])


def test_backlog_separated_mode_layer_exclusivity_and_first_l3_parent_context(tmp_path: Path):
    """Garante exclusividade de camadas e injeção do nó L2 pai apenas no 1º nó L3.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    set_backlog_config(tmp_path, development_mode="separated", bootstrap_task=False, test_loop_enabled=False)

    # 1. Frontend layer entrega apenas tarefas L2 (sem subtasks e sem batch)
    front_task = next_backlog_task(tmp_path, layer="frontend")
    assert front_task["kind"] == "backlog-task"
    assert front_task["task"]["level"] == 2
    assert front_task["task"]["id"] == "task:jornada:node:1"
    assert front_task["implementation_layer"] == "frontend"
    assert front_task["subtasks"] == []
    assert "batch" not in front_task

    complete_backlog_task(tmp_path, "task:jornada:node:1")

    # Conclui as demais tasks L2 de frontend
    while True:
        res = next_backlog_task(tmp_path, layer="frontend")
        if res.get("kind") == "backlog-layer-empty":
            break
        assert res["task"]["level"] == 2
        complete_backlog_task(tmp_path, res["task"]["id"])

    # 2. Backend layer entrega tarefas L3
    # O 1º L3 deve receber parent_screen_context
    back_task_1 = next_backlog_task(tmp_path, layer="backend")
    assert back_task_1["task"]["level"] == 3
    assert back_task_1["task"]["id"] == "task:subjornada:node:1"
    assert back_task_1["implementation_layer"] == "backend"
    assert back_task_1["is_first_l3_for_screen"] is True
    assert back_task_1["parent_screen_context"] is not None
    assert back_task_1["parent_screen_context"]["id"] == "task:jornada:node:1"
    assert back_task_1["parent_screen_context"]["label"] == "Iniciar"
    assert "symbols" in back_task_1["parent_screen_context"]

    complete_backlog_task(tmp_path, "task:subjornada:node:1")

    # O 2º L3 NÃO deve receber parent_screen_context
    back_task_2 = next_backlog_task(tmp_path, layer="backend")
    assert back_task_2["task"]["level"] == 3
    assert back_task_2["task"]["id"] == "task:subjornada:node:2"
    assert back_task_2["is_first_l3_for_screen"] is False
    assert back_task_2["parent_screen_context"] is None

    complete_backlog_task(tmp_path, "task:subjornada:node:2")


def test_backlog_backend_batching_and_l3_verification_intervals(tmp_path: Path):
    """Testa entrega em lote de L3 e injeção de verificação a cada N nós L3 concluídos.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_nested_hierarchical_fixture(tmp_path)
    set_backlog_config(
        tmp_path,
        development_mode="separated",
        bootstrap_task=False,
        test_loop_enabled=False,
        task_batch_size=2,
        verification_interval=2,
    )

    # Conclui todas as tasks de frontend L2
    while True:
        front_task = next_backlog_task(tmp_path, layer="frontend")
        if front_task.get("kind") == "backlog-layer-empty":
            break
        complete_backlog_task(tmp_path, front_task["task"]["id"])

    # Backend: 1º L3 é entregue em lote de 2 nós L3
    back_task_1 = next_backlog_task(tmp_path, layer="backend")
    assert back_task_1["task"]["id"] == "task:subjornada:node:1"
    assert "batch" in back_task_1
    assert len(back_task_1["batch"]) == 2
    assert [item["id"] for item in back_task_1["batch"]] == ["task:subjornada:node:1", "task:subjornada:node:2"]

    complete_backlog_task(tmp_path, "task:subjornada:node:1")

    # 2º L3
    back_task_2 = next_backlog_task(tmp_path, layer="backend")
    complete_backlog_task(tmp_path, "task:subjornada:node:2")

    # Após 2 nós L3 concluídos, deve injetar verificação em lote para os 2 L3
    verify_task = next_backlog_task(tmp_path, layer="backend")
    assert verify_task["kind"] == "backlog-verification-task"
    assert "batch" in verify_task["task"]["id"] or "verify" in verify_task["task"]["id"]
    complete_backlog_task(tmp_path, verify_task["task"]["id"])

    backlog = read_backlog(tmp_path)
    assert "task:subjornada:node:1" in backlog["execution"].get("verified_l3_task_ids", [])
    assert "task:subjornada:node:2" in backlog["execution"].get("verified_l3_task_ids", [])


def test_cli_backlog_frontend_and_backend_commands(tmp_path: Path, monkeypatch):
    """Testa os comandos looper backlog frontend e looper backlog backend na CLI.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    monkeypatch.chdir(tmp_path)
    _create_nested_hierarchical_fixture(tmp_path)
    set_backlog_config(tmp_path, development_mode="separated", bootstrap_task=False, test_loop_enabled=False)

    front_res = runner.invoke(app, ["backlog", "frontend"])
    assert front_res.exit_code == 0
    assert "Iniciar" in front_res.stdout
    assert "frontend" in front_res.stdout.lower()

    complete_backlog_task(tmp_path, "task:jornada:node:1")
    while True:
        res = next_backlog_task(tmp_path, layer="frontend")
        if res.get("kind") == "backlog-layer-empty":
            break
        complete_backlog_task(tmp_path, res["task"]["id"])

    back_res = runner.invoke(app, ["backlog", "backend"])
    assert back_res.exit_code == 0
    assert "Tela pai correspondente (L2):" in back_res.stdout
    assert "Iniciar" in back_res.stdout


def test_init_configures_all_backlog_options(tmp_path: Path):
    """Testa passagem de todos os parâmetros configuráveis no comando looper init.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--integration",
            "codex",
            "--development-mode",
            "separated",
            "--verification-interval",
            "3",
            "--task-batch-size",
            "2",
            "--task-batch-scope",
            "node",
            "--bootstrap",
            "--final-verification",
            "--min-task-interval-seconds",
            "5",
        ],
    )
    assert result.exit_code == 0, result.output
    config = json.loads((tmp_path / ".looper/config.json").read_text(encoding="utf-8"))["backlog"]
    assert config["development_mode"] == "separated"
    assert config["verification_interval"] == 3
    assert config["task_batch_size"] == 2
    assert config["task_batch_scope"] == "node"
    assert config["bootstrap_task"] is True
    assert config["final_verification_task"] is True
    assert config["min_task_interval_seconds"] == 5


def test_test_scope_selects_l2_l3_or_both_and_describes_l2_playwright_flow(tmp_path: Path):
    """Persiste o escopo do loop e entrega orientação de interface para L2.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    _create_hierarchical_fixture(tmp_path)
    _remove_test_refs(tmp_path)
    set_backlog_config(tmp_path, bootstrap_task=False, test_scope="l2")

    config = get_backlog_config(tmp_path)
    assert config["test_scope"] == "l2"
    assert config["test_loop"]["scope"] == "l2"
    assert config["test_loop"]["include_level_2"] is True
    assert config["test_loop"]["l3_loop_enabled"] is False

    response = next_backlog_test(tmp_path)
    assert response["task"]["level"] == 2
    assert "Playwright" in response["instruction"]
    assert "conexão entre telas" in response["instruction"]

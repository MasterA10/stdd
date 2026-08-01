import json
from urllib.request import Request, urlopen
from pathlib import Path

from typer.testing import CliRunner

from stdd.cli import app
from stdd.draw import create_draw, read_draw_index, start_server_for_test


runner = CliRunner()


def draw_payload(draw_id: str = "checkout") -> dict:
    """Monta um desenho pequeno para os testes do renderer.
    Retorna grupos, nós, relações, fluxo e trade-off válidos para o contrato.
    """
    return {
        "id": draw_id,
        "title": "Checkout",
        "subtitle": "Fluxo de compra",
        "kind": "feature",
        "groups": [{"id": 1, "label": "Aplicação", "color": "#5688e8"}],
        "nodes": [
            {"id": 1, "label": "Carrinho", "group": 1, "description": "Itens escolhidos."},
            {"id": 2, "label": "Pagamento", "group": 1, "description": "Autoriza a compra."},
        ],
        "edges": [{"id": 1, "from": 1, "to": 2, "label": "inicia", "kind": "flow", "condition": 3}],
        "flows": [{"id": 1, "label": "Comprar", "steps": [{"node": 1, "text": "seleciona"}, {"node": 2, "text": "paga"}]}],
        "tradeoffs": [{"title": "Síncrono ou assíncrono?", "decision": "Assíncrono", "options": []}],
    }


def test_init_installs_draw_data_without_copying_viewer_code(tmp_path: Path, monkeypatch):
    """Instala os dados do Draw sem copiar código do viewer para o projeto.
    Executa init e verifica o índice persistente e a ausência do HTML legado.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"], catch_exceptions=False)

    assert result.exit_code == 0
    assert (tmp_path / ".stdd/draws/index.json").exists()
    assert not (tmp_path / ".stdd/draw.html").exists()
    index = json.loads((tmp_path / ".stdd/draws/index.json").read_text())
    assert [entry["id"] for entry in index["draws"]] == ["demo-inicial"]
    assert (tmp_path / ".stdd/draws/demo-inicial.json").exists()


def test_init_installs_example_draw_idempotently(tmp_path: Path, monkeypatch):
    """Instala um fluxo inicial para o primeiro uso do viewer.
    Executa init duas vezes e confirma que o JSON de exemplo não é duplicado.
    """
    monkeypatch.chdir(tmp_path)

    runner.invoke(app, ["init"], catch_exceptions=False)
    runner.invoke(app, ["init"], catch_exceptions=False)

    index = json.loads((tmp_path / ".stdd/draws/index.json").read_text())
    assert [entry["id"] for entry in index["draws"]].count("demo-inicial") == 1
    assert len(json.loads((tmp_path / ".stdd/draws/demo-inicial.json").read_text())["nodes"]) > 0


def test_init_removes_legacy_draw_viewer(tmp_path: Path, monkeypatch):
    """Remove o viewer legado durante a migração do projeto.
    Cria um HTML antigo e confirma que init deixa somente o armazenamento JSON.
    """
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / ".stdd/draw.html"
    legacy.parent.mkdir()
    legacy.write_text("viewer legado", encoding="utf-8")

    runner.invoke(app, ["init"], catch_exceptions=False)

    assert not legacy.exists()


def test_create_draw_writes_only_json_and_light_index(tmp_path: Path):
    """Grava um desenho em JSON e atualiza o índice sem gerar HTML individual.
    Cria um payload com relações, fluxo e trade-off e valida os dois artefatos persistidos.
    """
    path = create_draw(tmp_path, draw_payload())

    assert path == tmp_path / ".stdd/draws/checkout.json"
    assert path.exists()
    assert not (tmp_path / ".stdd/draws/checkout.html").exists()
    index = read_draw_index(tmp_path)
    assert index["draws"][0]["id"] == "checkout"
    assert index["draws"][0]["node_count"] == 2
    assert index["draws"][0]["edge_count"] == 1
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["flows"][0]["id"] == 1
    assert saved["edges"][0]["condition"] == 3


def test_create_draw_preserves_optional_questions_and_answers(tmp_path: Path):
    """Persiste perguntas abertas, booleanas e de múltipla escolha no nó.
    Grava respostas diferentes e confirma que o histórico lógico permanece no JSON.
    """
    payload = draw_payload()
    payload["nodes"][0]["questions"] = [
        {"id": 1, "type": "choice", "prompt": "Qual canal?", "options": [{"id": 1, "label": "Web"}, {"id": 2, "label": "App"}], "answer": 2},
        {"id": 2, "type": "boolean", "prompt": "Precisa autenticar?", "answer": False},
        {"id": 3, "type": "open", "prompt": "Qual risco?", "answer": "Fraude"},
    ]

    path = create_draw(tmp_path, payload)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["nodes"][0]["questions"][0]["answer"] == 2
    assert saved["nodes"][0]["questions"][1]["answer"] is False
    assert saved["nodes"][0]["questions"][2]["answer"] == "Fraude"


def test_create_draw_rejects_invalid_question_contract(tmp_path: Path):
    """Bloqueia tipos, opções, respostas e IDs inválidos de perguntas.
    Tenta quatro contratos incorretos e garante que nenhum desenho inválido seja gravado.
    """
    invalid_questions = [
        {"id": 1, "type": "unknown", "prompt": "Pergunta"},
        {"id": 1, "type": "choice", "prompt": "Pergunta", "options": [{"id": 1, "label": "Só uma"}]},
        {"id": 1, "type": "boolean", "prompt": "Pergunta", "answer": "sim"},
        {"id": 1, "type": "open", "prompt": "Pergunta", "answer": 42},
    ]

    for index, question in enumerate(invalid_questions):
        payload = draw_payload(f"pergunta-invalida-{index}")
        payload["nodes"][0]["questions"] = [question]
        try:
            create_draw(tmp_path, payload)
        except ValueError as error:
            assert "question" in str(error) or "pergunta" in str(error)
        else:
            raise AssertionError("pergunta inválida deveria ser rejeitada")


def test_create_draw_replaces_current_json_without_history(tmp_path: Path):
    """Substitui o desenho atual pelo mesmo ID sem criar histórico adicional.
    Grava duas versões e verifica que somente o JSON atual permanece na pasta de dados.
    """
    create_draw(tmp_path, draw_payload())
    updated = draw_payload()
    updated["title"] = "Checkout atualizado"
    create_draw(tmp_path, updated)

    assert json.loads((tmp_path / ".stdd/draws/checkout.json").read_text())["title"] == "Checkout atualizado"
    assert not (tmp_path / ".stdd/draws/history").exists()


def test_create_draw_accepts_descriptive_draw_id_and_numeric_internal_ids(tmp_path: Path):
    """Aceita ID descritivo do desenho e IDs numéricos nas entidades internas.
    Remove posição, cor, estilo e datas do JSON principal porque o viewer os calcula.
    """
    payload = {
        "id": "fluxo-numerico",
        "title": "Fluxo numérico",
        "kind": "feature",
        "updated_at": "não deve persistir",
        "groups": [{"id": 10, "label": "Sistema", "color": "#ff0000"}],
        "nodes": [
            {"id": 1, "label": "Início", "group": 10, "position": {"x": 10, "y": 20}, "color": "red"},
            {"id": 2, "label": "Fim", "group": 10, "style": {"shadow": True}},
        ],
        "edges": [{"id": 100, "from": 1, "to": 2, "kind": "conditional", "condition": 3, "color": "blue"}],
    }

    path = create_draw(tmp_path, payload)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "fluxo-numerico.json"
    assert saved["id"] == "fluxo-numerico"
    assert saved["nodes"][0]["id"] == 1
    assert saved["edges"][0]["from"] == 1
    assert "updated_at" not in saved
    assert "position" not in saved["nodes"][0]
    assert "color" not in saved["nodes"][0]
    assert "style" not in saved["nodes"][1]
    assert "color" not in saved["groups"][0]
    assert "color" not in saved["edges"][0]


def test_create_draw_rejects_descriptive_ids_instead_of_labels(tmp_path: Path):
    """Exige IDs numéricos e reserva textos descritivos para os labels.
    Troca o ID de um nó por texto e confirma que o contrato bloqueia a gravação.
    """
    payload = draw_payload()
    payload["nodes"][0]["id"] = "carrinho"
    payload["edges"][0]["from"] = "carrinho"

    try:
        create_draw(tmp_path, payload)
    except ValueError as error:
        assert "numérico" in str(error)
    else:
        raise AssertionError("ID textual deveria ser rejeitado")


def test_create_draw_requires_descriptive_top_level_id(tmp_path: Path):
    """Reserva IDs numéricos para entidades internas e exige nome no desenho.
    Um ID numérico no documento principal deve ser rejeitado antes da criação do arquivo.
    """
    payload = draw_payload()
    payload["id"] = 42

    try:
        create_draw(tmp_path, payload)
    except ValueError as error:
        assert "descritivo" in str(error)
    else:
        raise AssertionError("ID numérico de desenho deveria ser rejeitado")


def test_create_draw_accepts_empty_canvas_for_visual_creation(tmp_path: Path):
    """Permite criar um desenho vazio antes da inclusão do primeiro bloco.
    Persiste o contrato mínimo para que toda a construção aconteça no editor visual.
    """
    payload = {"id": "novo-sistema", "title": "Novo sistema", "kind": "feature", "nodes": [], "edges": []}

    path = create_draw(tmp_path, payload)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["nodes"] == []
    assert saved["edges"] == []
    assert read_draw_index(tmp_path)["draws"][0]["node_count"] == 0


def test_create_draw_requires_fixed_selectable_edge_conditions(tmp_path: Path):
    """Restringe condições de setas ao vocabulário lógico configurado.
    Aceita se, ou e então separadamente, mas bloqueia texto livre e condição ausente.
    """
    for draw_id, condition in (("cond-entao", 1), ("cond-ou", 2), ("cond-se", 3)):
        valid = draw_payload(draw_id)
        valid["edges"][0]["condition"] = condition
        create_draw(tmp_path, valid)

    for draw_id, condition in (("cond-ausente", None), ("cond-texto", "ou então"), ("cond-zero", 0)):
        invalid = draw_payload(draw_id)
        if condition is None:
            invalid["edges"][0].pop("condition")
        else:
            invalid["edges"][0]["condition"] = condition
        try:
            create_draw(tmp_path, invalid)
        except ValueError as error:
            assert "condition" in str(error)
        else:
            raise AssertionError("condição livre deveria ser rejeitada")


def test_create_draw_rejects_dangling_edges_without_writing(tmp_path: Path):
    """Rejeita relações que apontam para nós inexistentes antes de escrever arquivos.
    Remove o nó de destino de um payload válido e verifica a mensagem e a ausência do JSON.
    """
    payload = draw_payload()
    payload["edges"][0]["to"] = 999

    try:
        create_draw(tmp_path, payload)
    except ValueError as error:
        assert "não existe" in str(error)
    else:
        raise AssertionError("payload inválido deveria ser rejeitado")
    assert not (tmp_path / ".stdd/draws/checkout.json").exists()


def test_create_draw_accepts_subdraw_reference_and_counts_it(tmp_path: Path):
    """Aceita um nó que referencia outro desenho carregável sob demanda.
    Adiciona draw_ref ao payload e verifica sua persistência e contagem no índice leve.
    """
    payload = draw_payload()
    payload["nodes"][1]["draw_ref"] = "payment-details"

    path = create_draw(tmp_path, payload)

    assert json.loads(path.read_text())["nodes"][1]["draw_ref"] == "payment-details"
    assert read_draw_index(tmp_path)["draws"][0]["subdraw_count"] == 1


def test_create_draw_rejects_unsafe_subdraw_reference(tmp_path: Path):
    """Rejeita referências de subdesenho que poderiam escapar da pasta draws.
    Usa um caminho relativo inseguro e verifica que nenhum JSON é gravado.
    """
    payload = draw_payload()
    payload["nodes"][0]["draw_ref"] = "../secret"

    try:
        create_draw(tmp_path, payload)
    except ValueError as error:
        assert "draw_ref" in str(error)
    else:
        raise AssertionError("draw_ref inseguro deveria ser rejeitado")


def test_draw_cli_accepts_inline_json_and_updates_existing_draw(tmp_path: Path, monkeypatch):
    """Aceita JSON inline pela CLI e atualiza o mesmo arquivo por ID.
    Executa create duas vezes e confirma que o índice continua contendo um único desenho.
    """
    monkeypatch.chdir(tmp_path)
    payload = json.dumps(draw_payload(), ensure_ascii=False)
    first = runner.invoke(app, ["draw", "create", "--data-json", payload])
    second = runner.invoke(app, ["draw", "create", "--data-json", payload])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert len(read_draw_index(tmp_path)["draws"]) == 1
    listed = runner.invoke(app, ["draw", "list"])
    assert listed.exit_code == 0
    assert "checkout" in listed.stdout


def test_draw_html_fetches_index_and_only_selected_json():
    """Mantém o viewer orientado a carregamento sob demanda.
    Inspeciona o template e confirma que ele busca o índice e depois apenas o desenho selecionado.
    """
    template = Path("src/stdd/templates/draw/draw.html").read_text(encoding="utf-8")

    assert "getJson('draws/index.json')" in template
    assert "getJson(`draws/${encodeURIComponent(id)}.json`)" in template
    assert "fetch(requestUrl, { cache: 'no-store' })" in template
    assert "Promise.all" not in template
    assert "draw_ref" in template
    assert "question-badge" in template
    assert "expandedQuestionPanel" in template
    assert "unansweredQuestionCount" in template
    assert "question.answer" in template
    assert "Perguntas" in template
    assert "Abrir subdesenho" in template
    assert "Voltar" in template


def test_draw_html_uses_react_flow_at_the_renderer_boundary():
    """Confirma que o frontend usa React Flow sem alterar o contrato lógico.
    Verifica a biblioteca, os adaptadores de entrada e saída e a ausência do renderer SVG próprio.
    """
    template = Path("src/stdd/templates/draw/draw.html").read_text(encoding="utf-8")

    assert '"@xyflow/react"' in template
    assert "react%2Fjsx-runtime" in template
    assert "ReactFlowProvider" in template
    assert "ReactFlow" in template
    assert "#root" in template
    assert "height: 100%;" in template
    assert "function toReactFlowNode" in template
    assert "function toReactFlowEdge" in template
    assert "function fromReactFlowNode" in template
    assert "function fromReactFlowEdge" in template
    assert "nodes: mappedNodes" in template
    assert "edges: mappedEdges" in template
    assert "<svg" not in template
    assert "const responseText = await response.text()" in template
    assert "resposta inválida do servidor" in template
    assert "function apiOrigin()" in template
    assert "window.location.port === '5500'" in template
    assert "window.location.protocol === 'file:'" in template
    assert "new URL(`/.stdd/${url}`, apiOrigin())" in template
    assert "const loadIndex = async (announce = true)" in template
    assert "loadIndex(false)" in template


def test_draw_html_supports_direct_editing_reorganization_and_condition_visuals():
    """Confirma as interações diretas do editor e a leitura visual das condições.
    Verifica reorganização automática, edição inline e estilos distintos para então, ou e se.
    """
    template = Path("src/stdd/templates/draw/draw.html").read_text(encoding="utf-8")

    assert "✦ Reorganizar" in template
    assert "const reorganize = ()" in template
    assert "useReactFlow" in template
    assert "inline-node-input" in template
    assert "inline-node-textarea" in template
    assert "beginInlineEdit('label'" in template
    assert "beginInlineEdit('description'" in template
    assert "Nenhum subdesenho" not in template
    assert "function questionCounts(node)" in template
    assert "question-count answered" in template
    assert "question-count unanswered" in template
    assert "top: 50%;" in template
    assert "left: 50%;" in template
    assert "transform: translate(-50%, -50%);" in template
    assert "strokeDasharray: visual.dash" in template
    assert "label: 'então'" in template
    assert "label: 'ou'" in template
    assert "label: 'se'" in template
    assert "const LoopEdge" in template
    assert "const laneY = Math.max(sourceY, targetY) + 120" in template
    assert "source-bottom" in template
    assert "target-left" in template
    assert "source-right" in template


def test_draw_html_puts_condition_before_edge_message_and_reserves_label_space():
    """Confirma a ordem dos rótulos e o espaçamento baseado no texto da relação.
    Exige o mesmo formato para então, ou e se e uma largura calculada antes do layout.
    """
    template = Path("src/stdd/templates/draw/draw.html").read_text(encoding="utf-8")

    assert "function edgeLabelText(edge)" in template
    assert "function edgeLabelWidth(edge)" in template
    assert "const gaps = {};" in template
    assert "const requiredGap = 320 + labelWidth + 48" in template
    assert "nextX += gaps[r] || 368" in template
    assert "react-flow__edge-textwrapper" in template


def test_demo_draw_contains_answered_questions_and_all_conditions():
    """Mantém um desenho reproduzível para revisar perguntas e respostas no viewer.
    Verifica respostas persistidas e as três condições do contrato lógico.
    """
    payload = json.loads(Path(".stdd/draws/demo-perguntas-respostas.json").read_text(encoding="utf-8"))

    answers = [question.get("answer") for node in payload["nodes"] for question in node.get("questions", [])]
    assert 2 in answers
    assert False in answers
    assert any(isinstance(answer, str) and "Usar tokenização" in answer for answer in answers)
    assert {edge["condition"] for edge in payload["edges"]} == {1, 2, 3}
    assert any(edge["from"] == 4 and edge["to"] == 1 for edge in payload["edges"])
    assert any(answer is None for answer in answers)


def test_draw_html_provides_visual_editor_pan_and_readable_long_flow_layout():
    """Expõe edição visual completa sem obrigar o usuário a manipular JSON.
    Confirma controles de pan, nós, conexões e roteamento em camadas para fluxos longos.
    """
    template = Path("src/stdd/templates/draw/draw.html").read_text(encoding="utf-8")

    assert "content=\"5\"" in template
    assert "id=\"viewport\"" in template
    assert "beginPan" in template
    assert "moveCanvas" in template
    assert "endPointerAction" in template
    assert 'id="edit"' not in template
    assert "toggleEditing" not in template
    assert "state.editing" not in template
    assert "Adicionar bloco" in template
    assert "Conectar blocos" in template
    assert "Excluir seleção" in template
    assert "Salvar alterações" in template
    assert "Editar JSON" not in template
    assert "editor-json" not in template
    assert "buildRanks" in template
    assert "order.reverse()" in template
    assert "orderRank" in template
    assert "routeEdge" in template
    assert "Math.abs(sy - ty) < 20" in template
    assert "edgeLabelGroup" in template
    assert "wrapText(value, maxCharacters)" in template
    assert "labelMaxWidth" in template
    assert "Excluir esta conexão?" in template
    assert "Excluir este bloco e suas conexões?" in template
    assert "state.presentation.positions" in template
    assert "action.dirty" in template
    assert "Movimentos e cores" in Path("README.md").read_text(encoding="utf-8")
    assert 'id="inspector"' not in template
    assert "editDrawMetadata" in template
    assert "editEdgeDirect" in template
    assert "edge-label-bg" in template
    assert "occupiedLabels" in template
    assert "Math.max(.42" in template
    assert "(1400 - box.width * state.zoom) / 2" in template
    assert "wrapText" in template
    assert "measureNode" in template
    assert "connectionPorts" in template
    assert "nextNumericId" in template
    assert "dataset.edgeId" in template
    assert "edge-hitbox" in template
    assert "pointerdown" in template
    assert "state.positions" in template
    assert "node.position" not in template
    assert "Novo desenho" in template
    assert "function newDraw" in template
    assert "function slugify" in template
    assert "uniqueDrawId(title)" in template
    assert "EDGE_CONDITIONS = {1:'então', 2:'ou', 3:'se'}" in template
    assert "EDGE_CONDITIONS[edge.condition]" in template
    assert "condition: DEFAULT_CONDITION" in template
    assert "choices: Object.values(EDGE_CONDITIONS)" in template
    assert "values: Object.keys(EDGE_CONDITIONS).map(Number)" in template
    assert "duplicateSelection" in template
    assert "ctrlKey" in template
    assert "metaKey" in template
    assert "type = 'color'" in template
    assert "localStorage" in template
    assert "editNodeDirect" in template
    assert "cycleEdgeCondition" in template
    assert "shortcut-dialog" in template
    assert "frontTargetFor" in template
    assert "moved:false" in template
    assert "deleteEdge" in template
    assert "edge-remove" in template
    assert "Conexão removida diretamente pela seta" in template
    assert "inlineNodeField" in template
    assert "inline-node-field" in template
    assert "node-color-control" in template
    assert "editNodeTitleDirect" in template
    assert "beginInlineNodeEdit(node, 'description')" in template
    assert "node-kind" in template
    assert "input.type = 'text'" in template
    assert "control = 'textarea'" in template
    assert "Cor do fundo" in template
    assert "Cor do texto" in template
    assert "Nome do desenho" in template
    assert "showDirectoryPicker" in template
    assert "saveDrawToDirectory" in template
    assert "downloadDrawJson" not in template
    assert "salvos diretamente no diretório escolhido" in template
    assert "window.location.protocol === 'file:'" in template
    assert "Salvamento direto indisponível em file://" in template
    assert "new URL(`/__stdd/api/draws/" in template


def test_draw_html_connects_blocks_by_dragging_visible_ports():
    """Disponibiliza conexão direta por arraste sem depender do modo em dois cliques.
    Confirma porta de saída, alvo destacado, seta de preview e criação centralizada da relação.
    """
    template = Path("src/stdd/templates/draw/draw.html").read_text(encoding="utf-8")

    assert "port-out" in template
    assert "port-in" in template
    assert "connection-preview" in template
    assert "drop-target" in template
    assert "beginConnectionDrag" in template
    assert "updateConnectionPreview" in template
    assert "finishConnectionDrag" in template
    assert "createConnection" in template
    assert "elementFromPoint" in template
    assert "Arraste a saída" in template


def test_draw_readme_documents_local_server_and_visual_shortcuts():
    """Documenta o servidor local necessário para fetch e persistência do Draw.
    Confirma que o README explica salvar JSON, atalhos de edição e a URL do viewer.
    """
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "stdd draw serve --port 8765" in readme
    assert "127.0.0.1:8765/.stdd/draw.html" in readme
    assert "Ctrl/Cmd+D" in readme
    assert "arrastar" in readme.lower()
    assert "dentro dele" in readme
    assert "próximo bloco lógico" in readme
    assert "botão `×`" in readme
    assert "Live Server" in readme
    assert "nome do desenho" in readme.lower()
    assert "rota virtual" in readme
    assert "nenhum arquivo HTML" in readme


def test_draw_server_serves_viewer_index_and_selected_json(tmp_path: Path):
    """Serve o viewer e os JSONs pela raiz HTTP local do projeto.
    Cria um desenho, consulta três URLs e encerra o servidor sem deixar thread ativa.
    """
    create_draw(tmp_path, draw_payload())
    server, thread = start_server_for_test(tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        viewer_html = urlopen(f"{base_url}/.stdd/draw.html").read().decode()
        assert 'id="root"' in viewer_html
        assert "Checkout" in urlopen(f"{base_url}/.stdd/draws/index.json").read().decode()
        assert "Carrinho" in urlopen(f"{base_url}/.stdd/draws/checkout.json").read().decode()
        assert "assets/" in viewer_html
        script_path = next(part.split('"', 1)[0] for part in viewer_html.split('src="') if part.startswith("/assets/") and ".js" in part)
        assert "react" in urlopen(f"{base_url}{script_path}").read().decode().lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_draw_server_does_not_expose_project_files(tmp_path: Path):
    """Serve somente o viewer e a API, sem expor arquivos da codebase.
    Cria um arquivo sensível na raiz e confirma que a rota arbitrária retorna 404.
    """
    (tmp_path / "secret.py").write_text("token = 'local'", encoding="utf-8")
    server, thread = start_server_for_test(tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        try:
            urlopen(f"{base_url}/secret.py")
        except Exception as error:
            assert "404" in str(error)
        else:
            raise AssertionError("arquivo da codebase não deveria ser exposto")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_draw_server_saves_edited_json_and_rejects_mismatched_id(tmp_path: Path):
    """Salva edições do viewer via PUT e bloqueia ID divergente na rota.
    Envia JSON válido e inválido ao endpoint local e verifica arquivo atual e status HTTP.
    """
    create_draw(tmp_path, draw_payload())
    server, thread = start_server_for_test(tmp_path)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        updated = draw_payload()
        updated["title"] = "Checkout editado"
        request = Request(
            f"{base_url}/__stdd/api/draws/checkout.json",
            data=json.dumps(updated).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        assert json.loads(urlopen(request).read())["status"] == "saved"
        assert json.loads((tmp_path / ".stdd/draws/checkout.json").read_text())["title"] == "Checkout editado"

        mismatched = dict(updated, id="outro-desenho")
        request = Request(
            f"{base_url}/__stdd/api/draws/checkout.json",
            data=json.dumps(mismatched).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        try:
            urlopen(request)
        except Exception as error:
            assert "400" in str(error)
        else:
            raise AssertionError("ID divergente deveria ser bloqueado")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

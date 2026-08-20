from pathlib import Path


EDITOR_ROOT = Path("draw-editor")


def test_empty_draw_editor_exposes_block_creation_action():
    """Mantém a ação de criar blocos disponível em desenhos vazios.
    Confirma que a aba inicial oferece o formulário de adição de blocos.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")

    assert "Adicionar Bloco" in sidebar
    assert "if (isEmptyDrawing) setActiveTab('info')" in sidebar


def test_draw_editor_exposes_loop_icon_and_modal_for_change_requests():
    """Mantém o pedido de alteração ao lado do atalho de perguntas do nó."""
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")
    modal = (EDITOR_ROOT / "src/components/ChangesModal.tsx").read_text(encoding="utf-8")

    for required in ("ChangesModal", "changesNode", "handleUpdateChanges", "openChangesModal"):
        assert required in app
    for required in ("Repeat2", "onOpenChanges", "openChangesModal"):
        assert required in node
    for required in ("Pedido de alteração", "status: 'pending'", "changes: ChangeRequest[]"):
        assert required in modal


def test_draw_editor_keeps_header_titles_compact_and_sidebar_responsive():
    """Evita título alto e permite preservar o canvas em telas estreitas."""
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    for required in ("isSidebarVisible", "sidebarDock", "sidebar-hidden", "PanelBottom"):
        assert required in app
    for required in ("text-overflow: ellipsis", "white-space: nowrap", ".app-workspace-layout.sidebar-bottom", ".sidebar-bottom :is(.sidebar-content)", "overflow-x: auto"):
        assert required in styles
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    for required in ("dock: 'side' | 'bottom'", "onWheelCapture={redirectBottomWheel}", "content.scrollLeft += event.deltaY"):
        assert required in sidebar


def test_drawings_index_enriches_entries_with_hierarchy_metadata():
    """Carrega a hierarquia real de cada desenho para a navegação.
    Confirma que o índice visual conhece nível, pai e raiz do fluxo.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "enrichDrawingsWithHierarchy" in app
    assert "hierarchy: document?.hierarchy" in app
    assert "setDrawingsIndex(enrichedIndex)" in app


def test_draw_editor_can_move_up_a_hierarchy_level_and_choose_between_parents():
    """Exibe retorno hierárquico mesmo em acesso direto e resolve múltiplos pais.
    Confirma que o editor consulta draw_ref, mostra o botão e abre a escolha de pai.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    modal = (EDITOR_ROOT / "src/components/ParentNavigationModal.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    for required in (
        "findParentNavigationOptions",
        "node.draw_ref !== childId",
        "contract.hierarchy?.parent_draw_ref",
        "const canGoUp =",
        "Subir nível",
        "ParentNavigationModal",
    ):
        assert required in app
    for required in ("Escolha para onde voltar", "mais de um nó", "onSelect", "ArrowUp"):
        assert required in modal
    assert ".level-up-btn" in styles
    assert ".parent-navigation-option" in styles


def test_subdraw_navigation_fits_the_entire_loaded_flow_in_the_canvas():
    """Reposiciona e ajusta o zoom quando um Draw é carregado.
    Mantém todos os nós visíveis sem substituir o foco específico da busca.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "const flowNodeSignature = useMemo(" in app
    assert "const contractNodeSignature = useMemo(" in app
    assert "const nodesInitialized = useNodesInitialized({ includeHiddenNodes: true });" in app
    assert "!nodesInitialized" in app
    assert "renderedDrawId !== contract.id" in app
    assert "flowNodeSignature !== contractNodeSignature" in app
    assert "const pendingAutoFitDrawRef = useRef<string | null>(null);" in app
    assert "setAutoFitRevision((value) => value + 1)" in app
    assert "reactFlowInstanceRef.current?.fitView({" in app
    assert "includeHiddenNodes: true" in app
    assert "duration: 450" in app
    assert "padding: 0.22" in app
    assert "maxZoom: 1.25" in app
    assert "cancelAnimationFrame(frame);" in app
    assert "setRenderedDrawId(null);" in app
    assert "setNodes([]);" in app

    main = (EDITOR_ROOT / "src/main.tsx").read_text(encoding="utf-8")
    assert "<ReactFlowProvider>" in main
    assert "<App />" in main


def test_drawings_sidebar_keeps_all_flows_and_groups_them_by_level():
    """Preserva a lista completa e oferece navegação por níveis.
    Confirma que níveis recolhíveis expõem pais e subfluxos relacionados.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")

    assert "drawingsByLevel" in sidebar
    assert "Navegação por nível" in sidebar
    assert "Todos os desenhos" in sidebar
    assert "Nível ${level}" in sidebar
    assert "subflux" in sidebar.lower()
    assert "parent_draw_ref" in sidebar


def test_draw_editor_exposes_separate_improvement_sessions_and_answers():
    """Mantém perguntas do Draw Improve separadas do editor de fluxos.
    Verifica também a resposta dos três formatos aceitos pela sessão.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")
    editor = (EDITOR_ROOT / "src/components/ImprovementEditor.tsx").read_text(encoding="utf-8")

    for required in (
        "improvementsIndex",
        "loadImprovementById",
        "/.looper/improvements/index.json",
        "/.looper/improvements/",
        "/__looper/api/improvements/",
        "isImprovementDirty",
        "performImprovementSave",
    ):
        assert required in app
    assert "showImprovementModal" in app
    assert "improvement-open-btn" in app
    assert "pendingImprovementQuestions" in app
    assert "Perguntas" in app
    assert ".improvement-dialog {" in styles
    assert ".improvement-dialog-overlay { z-index: 60; overflow: hidden; }" in styles
    assert ".improvement-dialog .improvement-editor {" in styles
    assert "scrollbar-gutter: stable;" in styles
    assert "Sessões de melhoria" in sidebar
    for required in ("perguntas respondidas", "Sim", "Não", "Ainda sem resposta", "applied", "separadamente do fluxo"):
        assert required in editor
    assert "CUSTOM_ANSWER_VALUE" in editor
    assert "Outra resposta..." in editor
    assert "question-answer-textarea" in editor
    assert "questionStateClass" in editor
    assert "unanswered" in editor
    assert "Sem resposta" in editor


def test_draw_editor_removes_floating_canvas_hint():
    """Remove a dica flutuante do canto inferior esquerdo do viewer.
    Confirma que JSX e CSS não mantêm o componente de dica antigo.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "canvas-hint" not in app
    assert "canvas-hint" not in styles


def test_flow_inputs_never_use_the_right_side_of_a_block():
    """Mantém entradas fora do lado direito nos dois modos de roteamento.
    Confirma handles e fallback de curvas e retas sem target-in-right.
    """
    custom_node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")
    layout = (EDITOR_ROOT / "src/layout.ts").read_text(encoding="utf-8")
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert 'type="target" position={Position.Right}' not in custom_node
    assert "target-in-right" not in layout
    assert "targetHandle: edgeHandles.targetHandle" in app


def test_orthogonal_edges_route_around_obstacles_using_semantic_ports():
    """Preserva portas direcionais e corredores livres no roteamento.
    Confirma que o desvio respeita a porta calculada e evita entradas à direita.
    """
    layout = (EDITOR_ROOT / "src/layout.ts").read_text(encoding="utf-8")
    edge = (EDITOR_ROOT / "src/components/AvoidEdge.tsx").read_text(encoding="utf-8")

    assert "targetDir = 'left'" in layout
    assert "sourceHandleId" in edge
    assert "targetHandleId" in edge
    assert "const clearance = 16" in edge
    assert "targetDir === 'right' ? ['left']" in edge


def test_loop_edges_choose_a_clear_lane_and_keep_the_arrow_visible():
    """Mantém loops fora dos blocos e exibe a seta antes da entrada.
    Confirma que a faixa considera obstáculos e que o marcador não fica oculto.
    """
    loop_edge = (EDITOR_ROOT / "src/components/LoopEdge.tsx").read_text(encoding="utf-8")

    assert "useNodes" in loop_edge
    assert "const bottomLane" in loop_edge
    assert "otherBoxes" in loop_edge
    assert "const arrowTip" in loop_edge
    assert "<path d={arrowPath}" in loop_edge


def test_loop_edges_use_distinct_lanes_when_returning_to_the_same_node():
    """Separa retornos concorrentes que chegam ao mesmo bloco.
    Confirma que cada loop recebe faixa e rótulo próprios sem alterar as idas.
    """
    loop_edge = (EDITOR_ROOT / "src/components/LoopEdge.tsx").read_text(encoding="utf-8")

    assert "useEdges" in loop_edge
    assert "sideLoops" in loop_edge
    assert "const sourceIds" in loop_edge
    assert "const sourceIndex" in loop_edge
    assert "const loopSpacing = 72" in loop_edge
    assert "const edgeIndex" in loop_edge
    assert "edgeIndex - (loopCount - 1) / 2" in loop_edge
    assert "const secondaryLane" in loop_edge
    assert "{ side: 'bottom', y: secondaryLane }" in loop_edge
    assert "{ side: 'top', y: secondaryLane }" in loop_edge


def test_same_level_back_edges_enter_from_the_bottom_when_the_lane_is_below():
    """Alinha a porta de entrada com o corredor inferior do retorno.
    Confirma que loops horizontais não chegam por cima sem necessidade.
    """
    layout = (EDITOR_ROOT / "src/layout.ts").read_text(encoding="utf-8")

    assert "sourceHandle: `source-${cond}-bottom`, targetHandle: `target-in-bottom`" in layout


def test_longest_return_from_terminal_node_can_use_the_upper_lane():
    """Balanceia retornos longos para não concentrar todas as linhas embaixo.
    Confirma que o retorno mais distante de uma origem terminal entra pelo topo.
    """
    layout = (EDITOR_ROOT / "src/layout.ts").read_text(encoding="utf-8")

    assert "sourceHasOnlyReturns" in layout
    assert "const farthestReturn" in layout
    assert "const shouldUseUpperLane" in layout
    assert "sourceHandle: `source-${cond}-top`, targetHandle: `target-in-top`" in layout


def test_return_edges_choose_the_clearest_upper_or_lower_corridor():
    """Escolhe a faixa de retorno com menos obstáculos.
    Prefere a faixa superior quando as duas estão livres para manter o fluxo legível.
    """
    layout = (EDITOR_ROOT / "src/layout.ts").read_text(encoding="utf-8")

    assert "function returnLaneFor" in layout
    assert "const topHits = laneHits(topLane)" in layout
    assert "const hasNodeAbove = boxes.some" in layout
    assert "const hasNodeBelow = boxes.some" in layout
    assert "if (!hasNodeAbove && hasNodeBelow) return 'top'" in layout
    assert "const verticalDirection = source.y - target.y" in layout
    assert "if (verticalDirection < 0) return 'top'" in layout
    assert "if (verticalDirection > 0) return 'bottom'" in layout
    assert "preferredReturnLane === 'top'" in layout


def test_alt_click_opens_the_same_detail_view_as_the_eye_action():
    """Abre os detalhes do bloco pelo atalho direto do canvas.
    Confirma que Alt não altera a seleção comum do editor.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "if (event.altKey)" in app
    assert "setActiveDetailNodeId(id)" in app
    assert "<kbd>Alt</kbd> detalhes" in app


def test_alt_click_also_changes_focus_inside_the_focus_canvas():
    """Mantém o atalho Alt disponível dentro da visão de foco.
    Confirma que Alt em um bloco vizinho abre seus próprios detalhes.
    """
    focus = (EDITOR_ROOT / "src/components/FocusDetailModal.tsx").read_text(encoding="utf-8")

    assert "const onNodeClick = (event: React.MouseEvent, node: Node)" in focus
    assert "if (!event.altKey) return;" in focus
    assert "window.openDetailViewer" in focus
    assert "onNodeClick={onNodeClick}" in focus


def test_backlog_checklists_are_editable_on_the_node_toolbar():
    """Exibe os dois checks diretamente ao lado das ações do bloco.
    Confirma que teste e implementação usam o estado do backlog e persistem pela ação compartilhada.
    """
    custom_node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert 'className="node-check-action test nodrag nopan"' in custom_node
    assert 'className={`node-check-action implementation' in custom_node
    assert 'aria-label="Checklist de teste"' in custom_node
    assert 'aria-label="Checklist de implementação"' in custom_node
    assert "backlogChecklist: backlogTask ?" in app
    assert "window.updateBacklogChecklist = updateBacklogChecklist" in app


def test_keyboard_shortcuts_connect_and_duplicate_selected_blocks():
    """Mantém atalhos básicos para conexão, duplicação e desfazer.
    Confirma a origem ordenada e os comandos Z, X, C e Ctrl/Cmd+D/Z.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "selectionOrderRef" in app
    assert "const conditions: Record<string, number> = { z: 1, x: 2, c: 3 }" in app
    assert "key === 'd'" in app
    assert "key === 'z'" in app
    assert "onSelectionChange={onSelectionChange}" in app
    assert "multiSelectionKeyCode={['Shift']}" in app
    assert "const isMultiSelect = event.shiftKey" in app
    assert "(cópia)" in app


def test_keyboard_shortcuts_copy_and_paste_nodes_as_json():
    """Copia o contrato lógico do nó e cola uma nova instância com outro ID.
    Mantém referências e campos do JSON sem duplicar conexões automaticamente.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "function parseClipboardNodeJson(text: string): NodeData[]" in app
    assert "JSON.stringify(payload, null, 2)" in app
    assert "navigator.clipboard.writeText" in app
    assert "navigator.clipboard.readText" in app
    assert "const copies = pastedNodes.map((node, index)" in app
    assert "id: nextIdStart + index" in app
    assert "if (modifier && key === 'c')" in app
    assert "if (modifier && key === 'v')" in app
    assert "Ctrl+C</kbd>/<kbd>Ctrl+V" in app


def test_editor_persists_pending_layout_and_deletions_until_save():
    """Preserva posições e exclusões durante a edição local.
    Confirma que apagar e salvar usam o contrato e o cache visual corretos.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    layout = (EDITOR_ROOT / "src/layout.ts").read_text(encoding="utf-8")

    assert "key === 'delete' || key === 'backspace'" in app
    assert "onEdgesChange={handleEdgesChange}" in app
    assert "presentationPositionsRef.current" in app
    assert "presentationPositionsState" in app
    assert "deleteKeyCode={null}" in app
    assert "customPos?.x !== undefined ? customPos.x : calcPos.x" in layout


def test_editor_discovers_draw_server_when_running_on_another_local_origin():
    """Mantém subfluxos acessíveis quando o editor roda em outra porta.
    O backend local padrão precisa ser descoberto antes de cair no localStorage.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "DEFAULT_DRAW_SERVER_ORIGIN = 'http://127.0.0.1:8765'" in app
    assert "[window.location.origin, DEFAULT_DRAW_SERVER_ORIGIN]" in app
    assert "const backendOrigin = await checkBackendAvailable()" in app
    assert "detectedBackendOrigin = backendOrigin" in app


def test_editor_does_not_update_local_index_for_an_unchanged_drawing():
    """Mantém updated_at estável no índice local.
    Salvar o mesmo contrato não cria uma nova atualização.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "savedLogicalPayload = localStorage.getItem(`looper-draw:${id}`)" in app
    assert "JSON.stringify(JSON.parse(savedLogicalPayload)) === JSON.stringify(cleanPayload)" in app
    assert "setIsDirty(false);\n            return;" in app


def test_global_search_lists_draw_associations_without_diming_the_canvas():
    """Busca em todos os Draws e navega para o nó associado.
    A consulta deve produzir uma lista clicável, preservar o canvas e aplicar zoom no destino.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "loadContractForSearch" in app
    assert "drawingsIndex.map(async (entry)" in app
    assert "searchResults.map((result)" in app
    assert "focusSearchResult" in app
    assert "fitView({" in app
    assert "nodes: [{ id: String(request.nodeId) }]" in app
    assert "Buscar em todos os fluxos..." in app
    assert ".search-results" in styles
    assert "const matchingNodeIds" not in app
    assert "if (hasSearch)" not in app


def test_editor_retries_subdraw_in_backend_before_showing_local_storage_error():
    """Evita falha no primeiro clique enquanto a detecção do backend termina.
    Confere no App.tsx a estratégia de tentativas nos origins do backend antes de reportar erro.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "if the user" not in app
    assert "for (const origin of getApiOrigins())" in app
    assert "detectedBackendOrigin = origin" in app
    assert "setStorageMode('backend')" in app
    assert "Desenho não encontrado no armazenamento local." in app


def test_organize_button_clears_local_positions_without_changing_the_flow():
    """Expõe a reorganização visual como uma ação explícita.
    Limpa somente a apresentação local e mantém o contrato lógico intacto.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "modifier && event.shiftKey && key === 'r'" not in app
    assert "const handleOrganize = () =>" in app
    assert "onClick={handleOrganize}" in app
    assert "Organizar fluxo" in app
    assert "title=\"Limpar as posições locais e reorganizar o fluxo automaticamente\"" in app
    assert "onOrganize" not in sidebar
    assert "localStorage.removeItem(presentationKey)" in app
    assert "setPresentationPositionsState({})" in app
    assert "const handleReset = async () =>" in app
    assert ".react-flow__edges" in styles
    assert "z-index: 0 !important" in styles
    assert ".react-flow__edge" in styles
    assert ".react-flow__nodes" in styles
    assert ".react-flow__node" in styles


def test_edge_conditions_keep_labels_separate_from_connection_colors():
    """Aplica degradê somente às conexões do então e verde ao ou.
    Mantém a cor tipográfica dos rótulos separada da linha e da seta.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    focus = (EDITOR_ROOT / "src/components/FocusDetailModal.tsx").read_text(encoding="utf-8")
    loop = (EDITOR_ROOT / "src/components/LoopEdge.tsx").read_text(encoding="utf-8")
    focus_loop = (EDITOR_ROOT / "src/components/FocusLoopEdge.tsx").read_text(encoding="utf-8")

    assert "const THEN_EDGE_GRADIENT = 'url(#looper-then-edge-gradient)'" in app
    assert "1: { color: theme === 'light' ? '#1e293b' : '#94a3b8', edgeStroke: THEN_EDGE_GRADIENT" in app
    assert "2: { color: '#22c55e', edgeStroke: '#22c55e'" in app
    assert "stroke: isHighlighted ? '#10b981' : visual.edgeStroke" in app
    assert "fill: isHighlighted" in app
    assert "<linearGradient id=\"looper-then-edge-gradient\"" in app
    assert "const THEN_EDGE_GRADIENT = 'url(#looper-then-edge-gradient)'" in focus
    assert "stroke: visual.edgeStroke" in focus
    assert "color: visual.markerColor" in focus
    assert "const edgeData = data as" in loop
    assert "const edgeData = data as" in focus_loop


def test_runs_sidebar_uses_the_main_sidebar_scroll_only():
    """Evita uma rolagem interna concorrente na aba de Runs.
    A lista de execuções acompanha o único contêiner rolável da sidebar.
    """
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")
    runs_list = styles.split(".runs-sidebar-list", 1)[1].split(".run-sidebar-card", 1)[0]

    assert ".sidebar-content {" in styles
    assert "min-height: 0;" in styles
    assert "overflow-y: auto;" in styles.split(".sidebar-content {", 1)[1].split("}", 1)[0]
    assert "max-height" not in runs_list
    assert "overflow" not in runs_list


def test_drawings_sidebar_uses_the_main_sidebar_scroll_only():
    """Evita listas internas concorrentes na aba de Desenhos.
    Catálogo e sessões de melhoria crescem junto com a rolagem principal.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert sidebar.count('className="draw-list"') == 2
    assert "overflowY: 'auto'" not in sidebar
    assert "maxHeight: '420px'" not in sidebar
    assert "maxHeight: '320px'" not in sidebar
    assert ".draw-list {" in styles


def test_shift_selection_keeps_neighbors_visible_while_ctrl_focuses_one_block():
    """Diferencia seleção para conexão de foco visual.
    Confirma que Shift seleciona múltiplos e Ctrl ativa o isolamento.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "const hasMultiSelection = selectionOrderRef.current.length > 1" in app
    assert "hasSelection && !hasMultiSelection" in app
    assert "const isMultiSelect = event.shiftKey" in app
    assert "const [isFocusMode, setIsFocusMode]" in app
    assert "const hasSelection = selectedNodeId !== null && isFocusMode" in app
    assert "setIsFocusMode((event.ctrlKey || event.metaKey) && !isMultiSelect)" in app


def test_shift_click_appends_to_a_normal_first_selection():
    """Mantém o primeiro bloco como âncora da seleção múltipla.
    Confirma que Shift no segundo clique adiciona sem exigir Shift no primeiro.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "const currentSelection = selectionOrderRef.current.length > 0" in app
    assert "? [selectedNodeId]" in app
    assert "selectionOrderRef.current = currentSelection.includes(id)" in app
    assert "? currentSelection.filter((selectedId) => selectedId !== id)" in app


def test_selected_blocks_have_an_explicit_visual_state():
    """Sincroniza a seleção lógica com o estado visual do React Flow.
    Confirma que blocos selecionados são distinguíveis dos blocos comuns.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")

    assert "selected: selectedNodeIds.has(Number(node.id))" in app
    assert "className={`custom-flow-node ${selected ? 'selected' : ''}" in node
    assert "const borderStyle = isBacklogTaskDone" in node
    assert "borderColor: accentColor" in node


def test_space_creates_an_instant_block_without_interrupting_text_fields():
    """Cria um bloco padrão com o atalho de espaço no canvas.
    Confirma que a criação respeita o bloqueio de campos editáveis.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "const createInstantNode = useCallback" in app
    assert "event.code === 'Space'" in app
    assert "createInstantNode();" in app
    assert "if (isEditableTarget(event.target)) return;" in app


def test_v_opens_question_editor_from_the_block_and_footer_documents_it():
    """Abre o editor de perguntas pelo bloco selecionado.
    Mantém o atalho visível no rodapé e permite opções múltiplas pelo modal.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")
    modal = (EDITOR_ROOT / "src/components/QuestionsModal.tsx").read_text(encoding="utf-8")

    assert "key === 'v'" in app
    assert "window.openQuestionsModal?.(selectedNode)" in app
    assert "<kbd>V</kbd> perguntas" in app
    assert "ClipboardList" in node
    assert "Adicionar opção" in modal
    assert "onUpdateQuestions" in modal
    assert "hasUnsavedQuestionDraft" in modal
    assert "requestClose" in modal
    assert "Sair sem salvar" in modal
    assert "Continuar editando" in modal
    assert "onCancel={(event)" in modal
    assert "CUSTOM_ANSWER_VALUE" in modal
    assert "Outra resposta..." in modal
    assert "question-create-card-top" in modal
    assert "isAnswered(question.answer)" in modal
    assert "unanswered" in modal
    assert "Sem resposta" in modal


def test_question_textareas_keep_normal_text_visible_and_highlight_mentions_only_when_needed():
    """Mantém a digitação comum legível nos campos de perguntas.
    Usa a camada de destaque somente para menções e alinha sua tipografia ao textarea.
    """
    utils = (EDITOR_ROOT / "src/utils.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "const hasMentions = /(@looper|@developer|@obs)/i.test(value || '')" in utils
    assert "const useHighlightLayer = hasMentions && !isFocused" in utils
    assert "color: useHighlightLayer ? 'transparent' : 'var(--ink)'" in utils
    assert "background: useHighlightLayer ? 'transparent' : 'var(--input-bg)'" in utils
    assert "question-create-prompt-display" in styles
    assert ".question-prompt-input::placeholder" in styles


def test_black_theme_is_default_and_test_checklist_uses_red_orange_accent():
    """Inicia o viewer no tema preto e destaca o checklist de teste.
    Mantém o ícone de teste distinguível do checklist de implementação.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "useState<'light' | 'dark' | 'black'>('black')" in app
    assert ".node-check-action.test {" in styles
    assert "color: #f04f31;" in styles


def test_node_question_counts_use_answer_state_colors():
    """Destaca respostas concluídas com a identidade vermelho-laranja.
    Mantém perguntas sem resposta em cinza com texto branco legível.
    """
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert ".question-count.answered" in styles
    assert "background: var(--brand-gradient);" in styles
    assert ".question-count.unanswered" in styles
    assert "background: #4b5563;" in styles
    assert "color: #fff;" in styles


def test_dialog_content_inherits_theme_text_color_on_dark_backgrounds():
    """Mantém textos dos diálogos legíveis nos temas escuros.
    Confirma que o elemento nativo e seu conteúdo usam a cor do tema.
    """
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert ".app-dialog {" in styles
    assert "color: var(--ink);" in styles[styles.index(".app-dialog {"):]
    assert ".app-dialog .dialog-content" in styles


def test_static_analysis_sidebar_uses_clear_labels_and_one_theme_scroll():
    """Organiza a aba de análise sem jargão local ou azul residual.
    Mantém a rolagem no painel principal para evitar rolagens aninhadas.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "Visão estrutural" in sidebar
    assert "Saúde do código" in sidebar
    assert "Tecnologias encontradas" in sidebar
    assert "formatFindingKind(kind)" in sidebar
    assert "Adapter local" not in sidebar
    assert "127.0.0.1" not in sidebar
    assert "localStorage" not in sidebar
    assert "background: var(--accent-light);" in styles
    assert "#0284c7" not in styles
    assert "#0369a1" not in styles
    assert "#0ea5e9" not in styles
    file_list_styles = styles[styles.index(".static-analysis-file-list {"):styles.index(".static-analysis-file-list li {")]
    assert "overflow-y: auto" not in file_list_styles
    assert "scrollbar-color: var(--line-strong) transparent;" in styles


def test_static_analysis_indicators_support_dragging_and_occurrence_evidence():
    """Permite reorganizar indicadores e consultar evidências reais.
    Confirma arquivo, linha, severidade e evidência no detalhe selecionado.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")
    types = (EDITOR_ROOT / "src/types.ts").read_text(encoding="utf-8")

    assert "draggable" not in sidebar
    assert "onDragStart" not in sidebar
    assert "onDrop" not in sidebar
    assert "showAnalysisSummary" in sidebar
    assert "static-analysis-summary-toggle" in sidebar
    assert "Evidências da análise" in sidebar
    assert "detailsForIndicator" in sidebar
    assert "detail.file" in sidebar
    assert "detail.line" in sidebar
    assert "detail.evidence" in sidebar
    assert "quality_findings?: Array<Record<string, any>>" in types
    assert ".static-analysis-finding-toggle" in styles
    assert "font-size: 18px;" in styles
    assert ".static-analysis-occurrence" in styles


def test_static_analysis_classifies_files_by_selected_indicator():
    """Agrupa arquivos pela categoria do indicador selecionado.
    Exibe contagem e linhas por arquivo antes da lista de ocorrências.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "groupDetailsByFile" in sidebar
    assert "Arquivos classificados por este indicador" in sidebar
    assert "selectedIndicatorFiles.map" in sidebar
    assert "group.count" in sidebar
    assert "group.lines" in sidebar
    assert ".static-analysis-file-classification" in styles
    assert ".static-analysis-file-group" in styles


def test_static_analysis_breakdown_findings_are_the_file_drilldown_items():
    """Usa cada classe de achado como item clicável e expansível.
    Remove a lista genérica para que arquivos apareçam dentro da classe escolhida.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "className={`static-analysis-finding-item" in sidebar
    assert "finding:${kind}" in sidebar
    assert "current === `finding:${kind}` ? null" in sidebar
    assert "aria-label={`Ver arquivos de" in sidebar
    assert "Arquivos com apontamentos" not in sidebar
    assert ".static-analysis-finding-item" in styles


def test_editor_uses_only_curved_edges_and_shows_shortcut_footer():
    """Mantém apenas o roteamento curvo no viewer.
    Confirma que o algoritmo reto e o botão de alternância não são usados.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "layoutCurvedGraph(filteredNodes" in app
    assert "AvoidEdge" not in app
    assert "type: edgeHandles.loop ? 'loop' : 'default'" in app
    assert "setEdgeRoutingMode" not in app
    assert "shortcut-footer" in app
    assert ".shortcut-footer" in styles


def test_focus_view_connects_incoming_arrows_to_the_left_back_of_nodes():
    """Mantém as entradas da visão de foco no lado traseiro dos blocos.
    Confirma que setas coloridas não terminam no topo ou na base do destino.
    """
    focus = (EDITOR_ROOT / "src/components/FocusDetailModal.tsx").read_text(encoding="utf-8")

    assert "const targetHandle = 'target-in-left'" in focus
    assert "target-in-top" not in focus
    assert "target-in-bottom" not in focus


def test_focus_view_keeps_curves_except_for_mutual_orthogonal_loops():
    """Mantém curvas nas conexões comuns da visão de foco.
    Apenas o retorno de uma conexão bidirecional usa segmentos ortogonais.
    """
    focus = (EDITOR_ROOT / "src/components/FocusDetailModal.tsx").read_text(encoding="utf-8")
    loop = (EDITOR_ROOT / "src/components/FocusLoopEdge.tsx").read_text(encoding="utf-8")

    assert "type: isOrthogonalLoop ? 'focus-loop' : 'default'" in focus
    assert "const hasReverseEdge = contract.edges.some" in focus
    assert "const [showLoops, setShowLoops] = useState(true)" in focus
    assert "if (isOrthogonalLoop && !showLoops) return null" in focus
    assert "Loops {showLoops ? 'visíveis' : 'ocultos'}" in focus
    assert "const incomingIds = new Set" in focus
    assert "const outgoingIds = new Set" in focus
    assert "const loopIds = new Set" in focus
    assert "incomingIds.has(node.id) && !loopIds.has(node.id)" in focus
    assert "outgoingIds.has(node.id) || loopIds.has(node.id)" in focus
    assert "computeEdgeHandles" in focus
    assert "const laneY" in loop
    assert "L ${targetX} ${laneY}" in loop
    assert "EdgeLabelRenderer" in loop
    assert "{label}" in loop


def test_focus_view_canvas_follows_dark_theme_background():
    """Mantém o canvas de foco escuro nos temas escuros.
    Usa o canvas claro somente quando o tema selecionado é claro.
    """
    focus = (EDITOR_ROOT / "src/components/FocusDetailModal.tsx").read_text(encoding="utf-8")

    assert "const focusCanvasBackground = theme === 'light'" in focus
    assert "'var(--canvas, #0f172a)'" in focus
    assert "background: focusCanvasBackground" in focus


def test_logical_save_is_manual_but_positions_use_presentation_cache():
    """Separa o salvamento manual do contrato lógico do cache de posições.
    Confirma que o JSON só usa o botão Salvar e drag grava a apresentação.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "const handleSave = () =>" in app
    assert "const handleSaveAll = async () =>" in app
    assert "const improvementNeedsSave = Boolean(currentImprovement && (" in app
    assert "currentImprovement.status === 'draft'" in app
    assert "onClick={improvementNeedsSave ? handleSaveAll : handleSave}" in app
    assert "Salvar fluxo + respostas" in app
    assert "onClick={handleOrganize}" in app
    assert "window.setTimeout" not in app
    assert "localStorage.setItem(presentationKey, JSON.stringify(parsed))" in app
    drag_handler = app.split("const onNodeDragStop", 1)[1].split("// --- Exposed", 1)[0]
    assert "setIsDirty(false);" not in drag_handler
    assert "...parsed.positions" in drag_handler
    assert "...presentationPositionsRef.current" in drag_handler


def test_manual_save_button_persists_the_logical_contract():
    """Mantém o botão Salvar como persistência do contrato lógico.
    Confirma que o autosave lógico não é disparado por timer.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "handleSave" in app
    assert "Salvar Desenho" in app
    assert "autoSaveTimerRef" not in app
    assert "performSave(contract);" in app


def test_runs_are_available_in_the_sidebar_with_a_brazilian_summary_modal():
    """Exibe summaries de runs diretamente no menu esquerdo.
    Confirma o carregamento do índice local, a data brasileira e as métricas do diff.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "RunRecord" in app
    assert "/.looper/runs/index.json" in app
    assert "runs={runs}" in app
    assert "activeTab === 'runs'" in sidebar
    assert ">('runs');" in sidebar
    assert sidebar.index("<span>Runs</span>") < sidebar.index("<span>Desenhos</span>")
    assert "RunDetailsModal" not in sidebar
    assert "new Intl.DateTimeFormat('pt-BR'" in sidebar
    assert "timeZoneName: 'short'" in sidebar
    assert "timeZone: 'America/Sao_Paulo'" in sidebar
    assert "run-sidebar-summary" in sidebar
    assert "run-sidebar-stats" in sidebar
    assert "lines_added" in sidebar
    assert "lines_deleted" in sidebar
    assert "files_changed" in sidebar
    assert "const runTotals = visibleRuns.reduce" in sidebar
    assert "Mostrar checkpoints (0 linhas)" in sidebar
    assert "useState(false)" in sidebar
    assert "aria-label={`Nota ponderada: ${weightedRunScore}/100`}" in sidebar
    assert "width: `${weightedRunScore}%`" in sidebar
    assert "addedPercentage" not in sidebar
    assert "Eficiência" in sidebar
    assert "Saldo acumulado" not in sidebar
    assert "saldo final" in sidebar
    assert "setRuns(records)" in app
    assert "const [showAllRuns, setShowAllRuns]" in sidebar
    assert "Todas as alterações" in sidebar
    assert "const periodRuns = showAllRuns ? runs : runs.filter(isRunFromToday)" in sidebar
    assert "calculateWeightedRunScore" in sidebar
    assert "const weightedRunTotals = visibleRuns.reduce" in sidebar
    assert "removed > added" in sidebar
    assert "removed * 2" in sidebar
    assert "calculateWeightedRunScore(weightedRunTotals.added, weightedRunTotals.removed)" in sidebar
    assert "ADDITION_WEIGHT = 1" in sidebar
    assert "REMOVAL_WEIGHT = 2" in sidebar
    assert "return Math.round((added * ADDITION_WEIGHT * 100) / weightedChanges)" in sidebar
    assert "if (weightedChanges === 0) return 50" in sidebar
    assert "Nota ponderada" in sidebar
    assert "linear-gradient(90deg, #7f1d3d 0%, #f97316 38%, #eab308 68%, #22c55e 100%)" in styles
    assert "/* Primary actions share the same filled red-to-orange visual language. */" in styles
    assert ".sidebar-submit-btn," in styles
    assert ".icon-btn.success," in styles
    assert ".question-add-option-btn { border-style: solid; }" in styles


def test_blocks_use_groups_instead_of_structural_types():
    """Mantém blocos agnósticos e usa grupos como única fonte de cor.
    Confirma que o editor e o salvamento não reintroduzem tipos de nó ou cores individuais.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    draw = Path("src/looper/draw.py").read_text(encoding="utf-8")

    assert "NODE_KINDS" not in node
    assert "type: 'process'" not in app
    assert "NODE_KINDS" not in sidebar
    assert "delete cleanNode.type" in app
    assert 'node.pop("type", None)' in draw
    assert "groupColor" in node
    assert "#8b5cf6" in node
    assert "withTint(accentColor, 0.82)" in node
    assert "color: newGroupColor" in sidebar


def test_dark_nodes_use_grayscale_fills_and_keep_group_accent_on_border():
    """Diferencia grupos no tema escuro sem colorir o preenchimento.
    Mantém o tema claro e as cores de contorno dos grupos existentes.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    focus = (EDITOR_ROOT / "src/components/FocusDetailModal.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")

    assert "const DARK_GROUP_FILLS" in node
    assert "function darkGroupFill(groupId?: number)" in node
    assert "const isDarkTheme = data.theme === 'dark' || data.theme === 'black';" in node
    assert "background: isDarkTheme" in node
    assert "darkGroupFill(data.group)" in node
    assert "color: isBacklogTaskInProgress || isBacklogTaskDone || isDarkTheme ? '#f8fafc' : '#0f172a'" in node
    assert "const groupPillStyle = isDarkTheme" in node
    assert "backgroundColor: accentColor, color: '#ffffff'" in node
    assert "style={groupPillStyle}" in node
    assert "borderColor: accentColor" in node
    assert "theme," in app
    assert "theme" in focus.split("groupOptions: contract.groups", 1)[1].split("}", 1)[0]


def test_backlog_task_states_style_in_progress_and_done_nodes():
    """Mostra o andamento e a conclusão da task diretamente no nó associado.
    Confirma o brilho animado, o degradê final e o fallback para movimento reduzido.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "status: backlogTask.status" in app
    assert "backlog-task-in-progress" in node
    assert "backlog-task-done" in node
    assert "lucide-test-tube-diagonal" in node
    assert "hasAssociatedTest = backlogChecklist?.test === true" in node
    assert "Boolean(data.test_ref)" in node
    assert "data.test_refs.length > 0" in node
    assert "node-associated-test" in node
    assert "background: #000000;" in styles
    assert "stroke=\"#ffffff\"" in node
    assert "? 'var(--brand-gradient)'" in node
    assert "color: isBacklogTaskInProgress || isBacklogTaskDone || isDarkTheme ? '#f8fafc' : '#0f172a'" in node
    assert "width: 24px" in styles
    assert "height: 18px" in styles
    assert "title={isBacklogTaskInProgress ? 'Task em andamento' : isBacklogTaskDone ? 'Task pronta' : undefined}" in node
    assert ".custom-flow-node.backlog-task-in-progress::after" in styles
    assert "looper-backlog-task-light-sweep" in styles
    assert "looper-backlog-task-gradient-drift" in styles
    assert "background-size: 175% 175%" in styles
    assert node.count("'var(--brand-gradient)'") >= 4
    assert "borderColor: accentColor" in node
    assert "borderWidth: '2px'" in node
    assert "withAlpha(accentColor, 0.2)" in node
    assert "border-color: #ef4444 !important" not in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles


def test_double_click_changes_group_and_canvas_click_exits_editing():
    """Permite trocar grupo no próprio bloco.
    Volta ao modo normal quando a lousa é clicada.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")

    assert "onDoubleClick={handleNodeDoubleClick}" in node
    assert "window.updateNodeGroup?." in node
    assert "looper:clear-node-editing" in node
    assert "window.dispatchEvent(new Event('looper:clear-node-editing'))" in app


def test_new_drawing_button_persists_a_new_json_document():
    """Mantém a criação de desenhos ligada à persistência do contrato.
    Confirma que o novo ID é salvo e indexado pelo mesmo fluxo do autosave.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    draw = Path("src/looper/draw.py").read_text(encoding="utf-8")

    create_block = app.split("const handleCreateDrawing", 1)[1].split("// --- Subdraw Navigation", 1)[0]
    assert "const newContract: Contract" in create_block
    assert "await performSave(newContract)" in create_block
    assert "create_draw(root, payload)" in draw
    assert "draw_directory(root) / f\"{draw_id}.json\"" in draw


def test_runs_load_history_for_period_selection_in_the_sidebar():
    """Carrega o histórico completo para permitir alternância de período.
    A sidebar decide entre as runs de hoje e todas as alterações.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    assert "setRuns(records)" in app
    assert "const isRunFromToday = (run: RunRecord)" in sidebar
    assert "const periodRuns = showAllRuns ? runs : runs.filter(isRunFromToday)" in sidebar


def test_code_references_modal_displays_file_path_under_symbol():
    """Exibe o caminho do arquivo abaixo do nome do símbolo no modal de referências.
    Verifica se CodeReferencesModal.tsx extrai a chave file de code_refs e aplica a classe de subtexto.
    """
    modal = (EDITOR_ROOT / "src/components/CodeReferencesModal.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "const file = typeof reference.file === 'string'" in modal
    assert "code-reference-file-subtext" in modal
    assert ".code-reference-file-subtext" in styles
    assert "code-reference-symbol-wrapper" in modal


def test_code_references_modal_displays_declared_draw_test_references():
    """Exibe testes declarados diretamente no nó do Draw.
    Combina test_refs persistidos com os testes encontrados nos facts estáticos.
    """
    modal = (EDITOR_ROOT / "src/components/CodeReferencesModal.tsx").read_text(encoding="utf-8")
    types = (EDITOR_ROOT / "src/types.ts").read_text(encoding="utf-8")

    assert "node.test_ref" in modal
    assert "node.test_refs" in modal
    assert "const declaredTests = declaredTestReferences.flatMap" in modal
    assert "const tests = Array.from(new Set([...asList(report?.tests), ...declaredTests]))" in modal
    assert "test_refs?: Array<{ file: string; symbols: string[] }>" in types


def test_sidebar_exposes_backlog_tasks_with_questions_and_symbols():
    """Exibe a task atual no viewer com seu contexto rastreável.
    Confirma que a aba Backlog mostra perguntas, respostas e símbolos associados.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    panel = (EDITOR_ROOT / "src/components/BacklogPanel.tsx").read_text(encoding="utf-8")

    assert "backlog={backlog}" in app
    assert "__looper/api/backlog/task" in app
    assert "__looper/api/backlog/test" in app
    assert "__looper/api/backlog/refresh" in app
    assert "__looper/api/backlog/tasks/" in app
    assert "activeTab === 'backlog'" in sidebar
    assert "Perguntas e respostas" in panel
    assert "Símbolos associados" in panel
    assert "Concluir task" in panel
    assert "Concluir testes" in panel
    assert "Testes associados" in panel
    assert "pendingTestTasks" in panel
    assert "taskTestStatus" in panel
    assert "backlog-phase-summary" in panel


def test_backlog_panel_exposes_both_execution_phase_statuses_and_delivery_scope():
    """Mostra testes e implementação separadamente e respeita task ou node."""
    panel = (EDITOR_ROOT / "src/components/BacklogPanel.tsx").read_text(encoding="utf-8")
    status_helpers = (EDITOR_ROOT / "src/backlog-status.ts").read_text(encoding="utf-8")
    types = (EDITOR_ROOT / "src/types.ts").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "Testes" in panel and "Implementação" in panel
    assert "deliveryScopeFor(backlog)" in panel
    assert "task_delivery_scope" in types
    assert "pendingTestTasks" in status_helpers
    assert "testScopeFor" in status_helpers
    assert ".backlog-phase-badge.test" in styles


def test_editor_loads_the_persisted_backlog_from_the_draw_server():
    """Carrega o backlog agregado junto com os Draws do projeto.
    Confirma a rota JSON e o fallback local usado quando o servidor não está disponível.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "/.looper/backlog.json" in app
    assert "looper-backlog" in app
    assert "BacklogDocument" in app


def test_editor_allows_node_checklists_and_persists_them_through_backlog_api():
    """Exibe os checklists de teste e implementação no nó selecionado.
    Usa a API central e mantém o bloqueio visual quando falta evidência do teste.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    panel = (EDITOR_ROOT / "src/components/BacklogPanel.tsx").read_text(encoding="utf-8")
    types = (EDITOR_ROOT / "src/types.ts").read_text(encoding="utf-8")

    assert "/__looper/api/backlog/checklist" in app
    assert "phase_checklists" in types
    assert "Checklist do backlog" in sidebar
    assert "Checklist de teste" in panel
    assert "Checklist de implementação" in panel
    assert "marcação manual" in sidebar


def test_editor_reconciles_selection_and_protects_async_draw_loads():
    """Evita seleção obsoleta e carregamento fora de ordem.
    Mantém o desenho atual quando uma resposta antiga termina depois.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    layout = (EDITOR_ROOT / "src/layout.ts").read_text(encoding="utf-8")

    assert "const drawingLoadRequestRef = useRef(0)" in app
    assert "const isCurrentRequest = () => drawingLoadRequestRef.current === requestId" in app
    assert "const selectedSet = new Set(selectedIds)" in app
    assert "resolveNodeCollisions(nodes, finalPositions, lockedIds)" in layout
    assert "Number.isFinite(manual.x)" in layout
    assert "export function getCycleEdges" in layout


def test_backlog_can_hide_completed_tasks_with_a_visible_red_separator():
    """Permite alternar a visibilidade das tasks concluídas.
    Mantém divisores no início, entre pendentes e no fim da lista.
    """
    panel = (EDITOR_ROOT / "src/components/BacklogPanel.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "showCompletedTasks" in panel
    assert "visibleTaskItems" in panel
    assert "hiddenCompletedCount" in panel
    assert "hiddenCompletedCount > 0" in panel
    assert "Mostrar concluídas" in panel
    assert "Ocultar concluídas" in panel
    assert "backlog-completed-divider" in panel
    assert "completedTasks.length" in panel
    assert "completed-divider-${index}" in panel
    assert panel.count("visibleTaskItems.push({ type: 'separator', hiddenCompletedCount });") == 2
    assert ".backlog-completed-divider" in styles
    assert "background: var(--danger);" in styles

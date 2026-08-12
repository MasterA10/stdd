from pathlib import Path


EDITOR_ROOT = Path("draw-editor")


def test_empty_draw_editor_exposes_block_creation_action():
    """Mantém a ação de criar blocos disponível em desenhos vazios.
    Confirma que a aba inicial oferece o formulário de adição de blocos.
    """
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")

    assert "Adicionar Bloco" in sidebar
    assert "if (isEmptyDrawing) setActiveTab('info')" in sidebar


def test_drawings_index_enriches_entries_with_hierarchy_metadata():
    """Carrega a hierarquia real de cada desenho para a navegação.
    Confirma que o índice visual conhece nível, pai e raiz do fluxo.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "enrichDrawingsWithHierarchy" in app
    assert "hierarchy: document?.hierarchy" in app
    assert "setDrawingsIndex(enrichedIndex)" in app


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

    assert "savedLogicalPayload = localStorage.getItem(`stdd-draw:${id}`)" in app
    assert "JSON.stringify(JSON.parse(savedLogicalPayload)) === JSON.stringify(cleanPayload)" in app
    assert "setIsDirty(false);\n            return;" in app


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


def test_reset_button_is_the_only_way_to_clear_local_positions():
    """Mantém o reset visual exclusivamente no botão superior.
    Remove o atalho Ctrl/Cmd+Shift+R e preserva a limpeza no handler de reset.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    styles = (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")

    assert "modifier && event.shiftKey && key === 'r'" not in app
    assert "localStorage.removeItem(presentationKey)" in app
    assert "setPresentationPositionsState({})" in app
    assert "const handleReset = async () =>" in app
    assert ".react-flow__edges" in styles
    assert "z-index: 0 !important" in styles
    assert ".react-flow__edge" in styles
    assert ".react-flow__nodes" in styles
    assert ".react-flow__node" in styles


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
    assert "selectionOrderRef.current = [...currentSelection, id]" in app


def test_selected_blocks_have_an_explicit_visual_state():
    """Sincroniza a seleção lógica com o estado visual do React Flow.
    Confirma que blocos selecionados são distinguíveis dos blocos comuns.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")

    assert "selected: selectedNodeIds.has(Number(node.id))" in app
    assert "className={`custom-flow-node ${selected ? 'selected' : ''}" in node
    assert "const borderStyle = selected" in node


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


def test_logical_save_is_manual_but_positions_use_presentation_cache():
    """Separa o salvamento manual do contrato lógico do cache de posições.
    Confirma que o JSON só usa o botão Salvar e drag grava a apresentação.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")

    assert "const handleSave = () =>" in app
    assert "onClick={handleSave}" in app
    assert "window.setTimeout" not in app
    assert "localStorage.setItem(presentationKey, JSON.stringify(parsed))" in app
    assert "setIsDirty(false);" in app.split("const onNodeDragStop", 1)[1].split("// --- Exposed", 1)[0]


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

    assert "RunRecord" in app
    assert "/.stdd/runs/index.json" in app
    assert "runs={runs}" in app
    assert "activeTab === 'runs'" in sidebar
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
    assert "addedPercentage" in sidebar
    assert "Saldo acumulado" in sidebar
    assert "saldo final" in sidebar
    assert "linear-gradient(90deg, #ef4444 0%, #f97316 50%, #22c55e 100%)" in (EDITOR_ROOT / "src/index.css").read_text(encoding="utf-8")


def test_blocks_use_groups_instead_of_structural_types():
    """Mantém blocos agnósticos e usa grupos como única fonte de cor.
    Confirma que o editor e o salvamento não reintroduzem tipos de nó ou cores individuais.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")
    sidebar = (EDITOR_ROOT / "src/components/Sidebar.tsx").read_text(encoding="utf-8")
    draw = Path("src/stdd/draw.py").read_text(encoding="utf-8")

    assert "NODE_KINDS" not in node
    assert "type: 'process'" not in app
    assert "NODE_KINDS" not in sidebar
    assert "delete cleanNode.type" in app
    assert 'node.pop("type", None)' in draw
    assert "groupColor" in node
    assert "#8b5cf6" in node
    assert "withTint(accentColor, 0.82)" in node
    assert "color: newGroupColor" in sidebar


def test_double_click_changes_group_and_canvas_click_exits_editing():
    """Permite trocar grupo no próprio bloco.
    Volta ao modo normal quando a lousa é clicada.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    node = (EDITOR_ROOT / "src/components/CustomNode.tsx").read_text(encoding="utf-8")

    assert "onDoubleClick={handleNodeDoubleClick}" in node
    assert "window.updateNodeGroup?." in node
    assert "stdd:clear-node-editing" in node
    assert "window.dispatchEvent(new Event('stdd:clear-node-editing'))" in app


def test_new_drawing_button_persists_a_new_json_document():
    """Mantém a criação de desenhos ligada à persistência do contrato.
    Confirma que o novo ID é salvo e indexado pelo mesmo fluxo do autosave.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    draw = Path("src/stdd/draw.py").read_text(encoding="utf-8")

    create_block = app.split("const handleCreateDrawing", 1)[1].split("// --- Subdraw Navigation", 1)[0]
    assert "const newContract: Contract" in create_block
    assert "await performSave(newContract)" in create_block
    assert "create_draw(root, payload)" in draw
    assert "draw_directory(root) / f\"{draw_id}.json\"" in draw


def test_runs_are_filtered_to_current_day():
    """Filtra as runs para exibir apenas as ocorridas a partir das 00h do dia atual.
    Garante que execuções de dias anteriores não sejam carregadas no menu lateral.
    """
    app = (EDITOR_ROOT / "src/App.tsx").read_text(encoding="utf-8")
    assert "setHours(0, 0, 0, 0)" in app

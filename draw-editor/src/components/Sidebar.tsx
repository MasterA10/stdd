import React, { useState } from 'react';
import type { Contract, NodeData, EdgeData, Group, FlowPath, FlowStep } from '../types';
import { NODE_KINDS } from './CustomNode';
import { Plus, Trash2, FolderPlus, List, Info, ChevronRight, Activity, Settings } from 'lucide-react';

interface SidebarProps {
  contract: Contract;
  selectedNode: NodeData | null;
  selectedEdge: EdgeData | null;
  activeFlowId: number | null;
  onUpdateContract: (updater: (prev: Contract) => Contract) => void;
  onSelectNode: (node: NodeData | null) => void;
  onSelectEdge: (edge: EdgeData | null) => void;
  onTriggerAutoLayout: () => void;
  onSelectFlow: (flowId: number | null) => void;
  onOpenImportExport: (mode: 'import' | 'export') => void;
  // Drawings support
  drawingsIndex: any[];
  currentDrawingId: string;
  onLoadDrawing: (id: string) => void;
  onNewDrawing: () => void;
  storageMode: 'backend' | 'local';
}

export const Sidebar: React.FC<SidebarProps> = ({
  contract,
  selectedNode,
  selectedEdge,
  activeFlowId,
  onUpdateContract,
  onSelectNode,
  onSelectEdge,
  onTriggerAutoLayout,
  onSelectFlow,
  onOpenImportExport,
  drawingsIndex,
  currentDrawingId,
  onLoadDrawing,
  onNewDrawing,
  storageMode
}) => {
  const [activeTab, setActiveTab] = useState<'drawings' | 'info' | 'blocks' | 'groups' | 'flows'>('drawings');
  const [drawingSearchQuery, setDrawingSearchQuery] = useState('');

  // Selected Node State
  const [newQuestionPrompt, setNewQuestionPrompt] = useState('');
  const [newQuestionType, setNewQuestionType] = useState<'open' | 'boolean' | 'choice'>('open');
  const [newQuestionOptionsText, setNewQuestionOptionsText] = useState('');



  // Add Group State
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDesc, setNewGroupDesc] = useState('');

  // Add Flow Path State
  const [newFlowLabel, setNewFlowLabel] = useState('');
  const [newFlowTitle, setNewFlowTitle] = useState('');
  const [newFlowSummary, setNewFlowSummary] = useState('');

  // Add Node State (Geral Tab)
  const [newNodeLabel, setNewNodeLabel] = useState('');
  const [newNodeType, setNewNodeType] = useState('process');
  const [newNodeGroup, setNewNodeGroup] = useState<string>('');
  const [newNodeDesc, setNewNodeDesc] = useState('');

  const filteredDrawings = drawingsIndex.filter((draw) =>
    `${draw.title} ${draw.subtitle} ${draw.kind}`.toLowerCase().includes(drawingSearchQuery.toLowerCase())
  );

  const handleUpdateNode = (updated: Partial<NodeData>) => {
    if (!selectedNode) return;
    onUpdateContract((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) => (n.id === selectedNode.id ? { ...n, ...updated } : n))
    }));
    onSelectNode({ ...selectedNode, ...updated });
  };

  const handleUpdateEdge = (updated: Partial<EdgeData>) => {
    if (!selectedEdge) return;
    onUpdateContract((prev) => ({
      ...prev,
      edges: prev.edges.map((e) => (e.id === selectedEdge.id ? { ...e, ...updated } : e))
    }));
    onSelectEdge({ ...selectedEdge, ...updated });
  };

  const handleAddQuestion = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNode || !newQuestionPrompt.trim()) return;

    const existingQuestions = selectedNode.questions || [];
    const nextQId = existingQuestions.length ? Math.max(...existingQuestions.map((q) => q.id)) + 1 : 1;

    let options = undefined;
    if (newQuestionType === 'choice' && newQuestionOptionsText.trim()) {
      options = newQuestionOptionsText
        .split(',')
        .map((opt, index) => ({ id: index + 1, label: opt.trim() }))
        .filter((opt) => opt.label.length > 0);
    }

    const newQuestion = {
      id: nextQId,
      type: newQuestionType,
      prompt: newQuestionPrompt.trim(),
      options,
      answer: null
    };

    handleUpdateNode({
      questions: [...existingQuestions, newQuestion]
    });

    setNewQuestionPrompt('');
    setNewQuestionOptionsText('');
  };

  const handleDeleteQuestion = (qId: number) => {
    if (!selectedNode) return;
    const questions = (selectedNode.questions || []).filter((q) => q.id !== qId);
    handleUpdateNode({ questions });
  };

  const handleAddGroup = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;

    onUpdateContract((prev) => {
      const nextGroupId = prev.groups.length ? Math.max(...prev.groups.map((g) => g.id)) + 1 : 0;
      const newGroup: Group = {
        id: nextGroupId,
        label: newGroupName.trim(),
        description: newGroupDesc.trim() || undefined
      };
      return {
        ...prev,
        groups: [...prev.groups, newGroup]
      };
    });

    setNewGroupName('');
    setNewGroupDesc('');
  };

  const handleDeleteGroup = (groupId: number) => {
    onUpdateContract((prev) => {
      // Remove group reference from nodes
      const updatedNodes = prev.nodes.map((n) =>
        n.group === groupId ? { ...n, group: undefined } : n
      );
      const updatedGroups = prev.groups.filter((g) => g.id !== groupId);
      return {
        ...prev,
        nodes: updatedNodes,
        groups: updatedGroups
      };
    });
  };

  const handleAddFlow = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFlowLabel.trim() || !newFlowTitle.trim()) return;

    onUpdateContract((prev) => {
      const existingFlows = prev.flows || [];
      const nextFlowId = existingFlows.length ? Math.max(...existingFlows.map((f) => f.id)) + 1 : 1;
      const newFlow: FlowPath = {
        id: nextFlowId,
        label: newFlowLabel.trim(),
        title: newFlowTitle.trim(),
        summary: newFlowSummary.trim(),
        steps: []
      };
      return {
        ...prev,
        flows: [...existingFlows, newFlow]
      };
    });

    setNewFlowLabel('');
    setNewFlowTitle('');
    setNewFlowSummary('');
  };

  const handleDeleteFlow = (flowId: number) => {
    onUpdateContract((prev) => {
      const existingFlows = prev.flows || [];
      const updatedFlows = existingFlows.filter((f) => f.id !== flowId);
      return {
        ...prev,
        flows: updatedFlows
      };
    });
    if (activeFlowId === flowId) {
      onSelectFlow(null);
    }
  };

  const handleAddNewNode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNodeLabel.trim()) return;

    onUpdateContract((prev) => {
      const nextNodeId = prev.nodes.length ? Math.max(...prev.nodes.map((n) => n.id)) + 1 : 1;
      const newNode: NodeData = {
        id: nextNodeId,
        label: newNodeLabel.trim(),
        type: newNodeType,
        group: newNodeGroup !== '' ? Number(newNodeGroup) : undefined,
        description: newNodeDesc.trim(),
        questions: []
      };
      return {
        ...prev,
        nodes: [...prev.nodes, newNode]
      };
    });

    setNewNodeLabel('');
    setNewNodeDesc('');
    setNewNodeGroup('');
  };

  // Add Step to Selected Flow
  const handleAddStepToFlow = (flowId: number, nodeId: number, text: string) => {
    onUpdateContract((prev) => {
      const updatedFlows = (prev.flows || []).map((flow) => {
        if (flow.id !== flowId) return flow;
        const newStep: FlowStep = { node: nodeId, text };
        return {
          ...flow,
          steps: [...flow.steps, newStep]
        };
      });
      return { ...prev, flows: updatedFlows };
    });
  };

  const handleRemoveStepFromFlow = (flowId: number, stepIndex: number) => {
    onUpdateContract((prev) => {
      const updatedFlows = (prev.flows || []).map((flow) => {
        if (flow.id !== flowId) return flow;
        return {
          ...flow,
          steps: flow.steps.filter((_, idx) => idx !== stepIndex)
        };
      });
      return { ...prev, flows: updatedFlows };
    });
  };

  return (
    <aside className="sidebar">
      {/* Brand Section */}
      <div className="brand">
        <div className="brand-mark">ST</div>
        <div>
          <h1 className="brand-title">STDD Flow</h1>
          <p className="brand-tagline">Architecture & Design Visualizer</p>
        </div>
      </div>

      {/* Tabs Menu */}
      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab-btn ${activeTab === 'drawings' ? 'active' : ''}`}
          onClick={() => setActiveTab('drawings')}
        >
          <FolderPlus size={14} />
          <span>Desenhos</span>
        </button>
        <button
          className={`sidebar-tab-btn ${activeTab === 'info' ? 'active' : ''}`}
          onClick={() => setActiveTab('info')}
        >
          <Info size={14} />
          <span>Geral</span>
        </button>
        <button
          className={`sidebar-tab-btn ${activeTab === 'blocks' ? 'active' : ''}`}
          onClick={() => setActiveTab('blocks')}
        >
          <List size={14} />
          <span>Blocos</span>
        </button>
        <button
          className={`sidebar-tab-btn ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          <Settings size={14} />
          <span>Grupos</span>
        </button>
        <button
          className={`sidebar-tab-btn ${activeTab === 'flows' ? 'active' : ''}`}
          onClick={() => setActiveTab('flows')}
        >
          <Activity size={14} />
          <span>Caminhos</span>
        </button>
      </div>

      <div className="sidebar-content">
        {/* Tab 0: Drawings list */}
        {activeTab === 'drawings' && (
          <div className="sidebar-pane">
            <button className="sidebar-submit-btn" onClick={onNewDrawing} style={{ margin: '4px 0 8px' }}>
              <Plus size={14} />
              Novo Desenho
            </button>

            <div className="editor-card" style={{ padding: '12px 14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <strong style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--muted)' }}>Conexão</strong>
                <span className="doc-type-badge" style={{
                  backgroundColor: storageMode === 'backend' ? 'var(--success)' : 'var(--warning)',
                  color: '#fff',
                  fontSize: '8px',
                  fontWeight: 900,
                  padding: '2px 6px',
                  borderRadius: '99px'
                }}>
                  {storageMode === 'backend' ? 'BACKEND' : 'OFFLINE'}
                </span>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--muted)', margin: 0, lineHeight: '1.4' }}>
                {storageMode === 'backend' 
                  ? 'Conectado a http://127.0.0.1:8765. As alterações são salvas diretamente no repositório.'
                  : 'Rodando offline. Os desenhos são salvos no armazenamento local do navegador (localStorage).'}
              </p>
            </div>

            <div className="editor-field" style={{ marginBottom: '8px' }}>
              <input
                className="search-input"
                style={{ margin: 0 }}
                placeholder="Buscar desenho..."
                value={drawingSearchQuery}
                onChange={(e) => setDrawingSearchQuery(e.target.value)}
              />
            </div>

            <div className="draw-list" style={{ display: 'grid', gap: '8px', overflowY: 'auto', maxHeight: '420px', padding: '2px' }}>
              {filteredDrawings.length === 0 ? (
                <p className="no-items-hint" style={{ textAlign: 'center', padding: '20px', color: 'var(--muted)', fontSize: '11px' }}>
                  Nenhum desenho encontrado.
                </p>
              ) : (
                filteredDrawings.map((draw) => (
                  <button
                    key={draw.id}
                    className={`flow-path-select-btn ${currentDrawingId === draw.id ? 'active' : ''}`}
                    onClick={() => onLoadDrawing(draw.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '12px 14px',
                      display: 'block'
                    }}
                  >
                    <strong style={{ display: 'block', fontSize: '13px', fontWeight: 800 }}>
                      {draw.title}
                    </strong>
                    <span style={{ display: 'block', fontSize: '10.5px', color: 'var(--muted)', marginTop: '4px', lineHeight: '1.3' }}>
                      {draw.subtitle || 'Sem descrição.'}
                    </span>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '6px', fontSize: '9px', fontWeight: 800, color: 'var(--muted)' }}>
                      <span style={{ textTransform: 'uppercase', color: currentDrawingId === draw.id ? 'var(--accent-strong)' : 'var(--accent)' }}>{draw.kind}</span>
                      <span>•</span>
                      <span>{draw.node_count} blocos</span>
                      <span>•</span>
                      <span>{draw.edge_count} conexões</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 1: Contract General Info */}
        {activeTab === 'info' && (
          <div className="sidebar-pane">
            <div className="editor-card">
              <h3>Propriedades do Contrato</h3>
              <div className="dialog-fields">
                <div className="editor-field">
                  <label>Título do Fluxo</label>
                  <input
                    value={contract.title || ''}
                    onChange={(e) =>
                      onUpdateContract((prev) => ({ ...prev, title: e.target.value }))
                    }
                  />
                </div>
                <div className="editor-field">
                  <label>Subtítulo / Descrição</label>
                  <textarea
                    value={contract.subtitle || ''}
                    onChange={(e) =>
                      onUpdateContract((prev) => ({ ...prev, subtitle: e.target.value }))
                    }
                  />
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="editor-card action-card-group">
              <h3>Ações Rápidas</h3>
              <div className="action-button-grid">
                <button className="quick-action-btn" onClick={onTriggerAutoLayout}>
                  Auto-Organizar Layout (Sugiyama)
                </button>
                <button
                  className="quick-action-btn secondary"
                  onClick={() => onOpenImportExport('import')}
                >
                  Importar JSON
                </button>
                <button
                  className="quick-action-btn secondary"
                  onClick={() => onOpenImportExport('export')}
                >
                  Exportar JSON
                </button>
              </div>
            </div>

            {/* Add Node Form */}
            <div className="editor-card">
              <h3>Adicionar Novo Bloco</h3>
              <form onSubmit={handleAddNewNode} className="dialog-fields">
                <div className="editor-field">
                  <label>Nome do Bloco</label>
                  <input
                    placeholder="Ex: API de login"
                    required
                    value={newNodeLabel}
                    onChange={(e) => setNewNodeLabel(e.target.value)}
                  />
                </div>
                <div className="editor-field">
                  <label>Tipo</label>
                  <select value={newNodeType} onChange={(e) => setNewNodeType(e.target.value)}>
                    {Object.entries(NODE_KINDS).map(([key, value]) => (
                      <option key={key} value={key}>
                        {value.icon} {value.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="editor-field">
                  <label>Grupo</label>
                  <select value={newNodeGroup} onChange={(e) => setNewNodeGroup(e.target.value)}>
                    <option value="">Nenhum Grupo</option>
                    {contract.groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="editor-field">
                  <label>Descrição</label>
                  <textarea
                    placeholder="Explique o que este bloco faz..."
                    value={newNodeDesc}
                    onChange={(e) => setNewNodeDesc(e.target.value)}
                  />
                </div>
                <button className="sidebar-submit-btn" type="submit">
                  <Plus size={14} />
                  Criar Bloco
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Tab 2: Selection / Blocks List */}
        {activeTab === 'blocks' && (
          <div className="sidebar-pane">
            {selectedNode ? (
              <div className="editor-card selected-item-card">
                <div className="card-header-with-action">
                  <h3>Editar Bloco #{selectedNode.id}</h3>
                  <button
                    className="delete-icon-btn"
                    onClick={() => {
                      if (window.deleteNode) window.deleteNode(selectedNode.id);
                    }}
                    title="Remover Bloco"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                <div className="dialog-fields">
                  <div className="editor-field">
                    <label>Título</label>
                    <input
                      value={selectedNode.label}
                      onChange={(e) => handleUpdateNode({ label: e.target.value })}
                    />
                  </div>

                  <div className="editor-field">
                    <label>Tipo</label>
                    <select
                      value={selectedNode.type || 'process'}
                      onChange={(e) => handleUpdateNode({ type: e.target.value })}
                    >
                      {Object.entries(NODE_KINDS).map(([key, val]) => (
                        <option key={key} value={key}>
                          {val.icon} {val.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="editor-field">
                    <label>Grupo</label>
                    <select
                      value={selectedNode.group === undefined ? '' : String(selectedNode.group)}
                      onChange={(e) => {
                        const val = e.target.value;
                        handleUpdateNode({
                          group: val === '' ? undefined : Number(val)
                        });
                      }}
                    >
                      <option value="">Nenhum Grupo</option>
                      {contract.groups.map((g) => (
                        <option key={g.id} value={String(g.id)}>
                          {g.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="editor-field">
                    <label>Descrição</label>
                    <textarea
                      value={selectedNode.description || ''}
                      onChange={(e) => handleUpdateNode({ description: e.target.value })}
                    />
                  </div>
                </div>

                {/* Node Questions Sub-Editor */}
                <div className="node-questions-sub-editor">
                  <h4>Questões / Checklist ({selectedNode.questions?.length || 0})</h4>
                  <div className="sidebar-question-list">
                    {(selectedNode.questions || []).map((q) => (
                      <div key={q.id} className="sidebar-question-item">
                        <div className="question-text-row">
                          <strong>Q#{q.id} ({q.type}):</strong> {q.prompt}
                        </div>
                        <button
                          className="question-del-btn"
                          onClick={() => handleDeleteQuestion(q.id)}
                          type="button"
                        >
                          <Trash2 size={10} />
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Add Question Form */}
                  <form onSubmit={handleAddQuestion} className="add-question-mini-form">
                    <input
                      placeholder="Nova pergunta para o bloco..."
                      required
                      value={newQuestionPrompt}
                      onChange={(e) => setNewQuestionPrompt(e.target.value)}
                    />
                    <div className="question-type-row">
                      <select
                        value={newQuestionType}
                        onChange={(e) =>
                          setNewQuestionType(e.target.value as 'open' | 'boolean' | 'choice')
                        }
                      >
                        <option value="open">Aberta (Texto)</option>
                        <option value="boolean">Sim/Não</option>
                        <option value="choice">Múltipla Escolha</option>
                      </select>
                    </div>
                    {newQuestionType === 'choice' && (
                      <input
                        placeholder="Opções separadas por vírgula (A, B, C)..."
                        required
                        value={newQuestionOptionsText}
                        onChange={(e) => setNewQuestionOptionsText(e.target.value)}
                      />
                    )}
                    <button className="mini-submit-btn" type="submit">
                      Adicionar Questão
                    </button>
                  </form>
                </div>
              </div>
            ) : selectedEdge ? (
              <div className="editor-card selected-item-card">
                <h3>Editar Conexão #{selectedEdge.id}</h3>
                <div className="dialog-fields">
                  <div className="editor-field">
                    <label>Condição da Conexão</label>
                    <select
                      value={String(selectedEdge.condition)}
                      onChange={(e) => {
                        handleUpdateEdge({ condition: Number(e.target.value) });
                      }}
                    >
                      <option value="1">Então (Principal)</option>
                      <option value="2">Ou (Alternativo)</option>
                      <option value="3">Se (Condicional)</option>
                    </select>
                  </div>

                  <div className="editor-field">
                    <label>Título do Link</label>
                    <input
                      placeholder="Ex: sucesso, erro 400"
                      value={selectedEdge.label || ''}
                      onChange={(e) => handleUpdateEdge({ label: e.target.value })}
                    />
                  </div>

                  <div className="editor-field">
                    <label>Descrição do Link</label>
                    <textarea
                      placeholder="Explique o fluxo ou o evento que ocorre aqui..."
                      value={selectedEdge.description || ''}
                      onChange={(e) => handleUpdateEdge({ description: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-selection-hint">
                <ChevronRight size={32} />
                <p>Selecione um bloco ou link no mapa para editar suas propriedades.</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Groups Editor */}
        {activeTab === 'groups' && (
          <div className="sidebar-pane">
            {/* List Groups */}
            <div className="editor-card">
              <h3>Grupos Cadastrados ({contract.groups.length})</h3>
              <div className="group-list-container">
                {contract.groups.length === 0 ? (
                  <p className="no-items-hint">Nenhum grupo cadastrado ainda.</p>
                ) : (
                  contract.groups.map((g) => (
                    <div key={g.id} className="group-list-item">
                      <div>
                        <strong>{g.label}</strong>
                        {g.description && <p>{g.description}</p>}
                      </div>
                      <button
                        className="group-delete-btn"
                        onClick={() => handleDeleteGroup(g.id)}
                        title="Deletar Grupo"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Add Group Form */}
            <div className="editor-card">
              <h3>Adicionar Novo Grupo</h3>
              <form onSubmit={handleAddGroup} className="dialog-fields">
                <div className="editor-field">
                  <label>Nome do Grupo</label>
                  <input
                    placeholder="Ex: Interface, Banco de Dados"
                    required
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                  />
                </div>
                <div className="editor-field">
                  <label>Descrição</label>
                  <textarea
                    placeholder="Resumo das responsabilidades deste grupo..."
                    value={newGroupDesc}
                    onChange={(e) => setNewGroupDesc(e.target.value)}
                  />
                </div>
                <button className="sidebar-submit-btn" type="submit">
                  <FolderPlus size={14} />
                  Criar Grupo
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Tab 4: Flow Paths (Caminhos) Editor */}
        {activeTab === 'flows' && (
          <div className="sidebar-pane">
            {/* Active Path Selector */}
            <div className="editor-card">
              <h3>Simular Caminho de Execução</h3>
              <div className="flow-path-selector-grid">
                <button
                  className={`flow-path-select-btn ${activeFlowId === null ? 'active' : ''}`}
                  onClick={() => onSelectFlow(null)}
                >
                  Visão Geral (Sem Destaque)
                </button>
                {(contract.flows || []).map((f) => (
                  <div key={f.id} className="flow-path-row">
                    <button
                      className={`flow-path-select-btn ${activeFlowId === f.id ? 'active' : ''}`}
                      onClick={() => onSelectFlow(f.id)}
                    >
                      <strong>{f.label}</strong>
                      <span>{f.title}</span>
                    </button>
                    <button
                      className="flow-path-del-btn"
                      onClick={() => handleDeleteFlow(f.id)}
                      title="Deletar Caminho"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Selected Flow Path Details / Step Editor */}
            {activeFlowId !== null && (
              <div className="editor-card flow-step-card">
                {(() => {
                  const flow = (contract.flows || []).find((f) => f.id === activeFlowId);
                  if (!flow) return null;

                  return (
                    <>
                      <h3>Passos do Caminho: {flow.label}</h3>
                      <p className="flow-summary-desc">{flow.summary || 'Sem resumo disponível.'}</p>

                      <div className="flow-steps-timeline">
                        {flow.steps.length === 0 ? (
                          <p className="no-items-hint">Nenhum passo adicionado. Monte o caminho abaixo:</p>
                        ) : (
                          flow.steps.map((step, idx) => {
                            const node = contract.nodes.find((n) => n.id === step.node);
                            return (
                              <div key={idx} className="flow-step-item">
                                <div className="step-badge">{idx + 1}</div>
                                <div className="step-body">
                                  <strong>{node ? node.label : `Bloco #${step.node}`}</strong>
                                  <p>{step.text || 'Sem descrição do passo.'}</p>
                                </div>
                                <button
                                  className="step-remove-btn"
                                  onClick={() => handleRemoveStepFromFlow(flow.id, idx)}
                                >
                                  <Trash2 size={10} />
                                </button>
                              </div>
                            );
                          })
                        )}
                      </div>

                      {/* Add Step Form */}
                      <div className="add-step-mini-form">
                        <h4>Adicionar Passo ao Caminho</h4>
                        <div className="editor-field">
                          <label>Bloco de Origem</label>
                          <select id="step-node-select">
                            {contract.nodes.map((n) => (
                              <option key={n.id} value={n.id}>
                                {n.label} (#{n.id})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="editor-field">
                          <label>Ação / Descrição</label>
                          <input id="step-node-text" placeholder="Ex: Clica em salvar ou envia dados" />
                        </div>
                        <button
                          className="mini-submit-btn"
                          onClick={() => {
                            const nodeSelect = document.getElementById('step-node-select') as HTMLSelectElement;
                            const textInput = document.getElementById('step-node-text') as HTMLInputElement;
                            if (nodeSelect && textInput && textInput.value.trim()) {
                              handleAddStepToFlow(
                                flow.id,
                                Number(nodeSelect.value),
                                textInput.value.trim()
                              );
                              textInput.value = '';
                            }
                          }}
                        >
                          Adicionar Passo
                        </button>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}

            {/* Add Flow Path Form */}
            <div className="editor-card">
              <h3>Adicionar Novo Caminho</h3>
              <form onSubmit={handleAddFlow} className="dialog-fields">
                <div className="editor-field">
                  <label>Rótulo Curto</label>
                  <input
                    placeholder="Ex: Sucesso, Erro 500"
                    required
                    value={newFlowLabel}
                    onChange={(e) => setNewFlowLabel(e.target.value)}
                  />
                </div>
                <div className="editor-field">
                  <label>Título do Fluxo</label>
                  <input
                    placeholder="Ex: Caminho Feliz de Onboarding"
                    required
                    value={newFlowTitle}
                    onChange={(e) => setNewFlowTitle(e.target.value)}
                  />
                </div>
                <div className="editor-field">
                  <label>Resumo / Descrição</label>
                  <textarea
                    placeholder="Explique o que esta jornada de caminho simula..."
                    value={newFlowSummary}
                    onChange={(e) => setNewFlowSummary(e.target.value)}
                  />
                </div>
                <button className="sidebar-submit-btn" type="submit">
                  <Plus size={14} />
                  Criar Caminho
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

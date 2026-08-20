import React, { useEffect, useRef, useState } from 'react';
import type { BacklogDocument, Contract, DrawIndexEntry, ImprovementIndexEntry, NodeData, EdgeData, Group, FlowPath, FlowStep, RunRecord, StaticAnalysisKpiReport } from '../types';
import { BacklogPanel } from './BacklogPanel';
import { Plus, Trash2, FolderPlus, List, Info, ChevronRight, Activity, Settings, BarChart3 } from 'lucide-react';
import brandLogo from '../assets/looper-logo.svg';

interface SidebarProps {
  dock: 'side' | 'bottom';
  contract: Contract;
  selectedNode: NodeData | null;
  selectedEdge: EdgeData | null;
  activeFlowId: number | null;
  onUpdateContract: (updater: (prev: Contract) => Contract) => void;
  onSelectNode: (node: NodeData | null) => void;
  onSelectEdge: (edge: EdgeData | null) => void;
  onSelectFlow: (flowId: number | null) => void;
  onOpenImportExport: (mode: 'import' | 'export') => void;
  // Drawings support
  drawingsIndex: DrawIndexEntry[];
  currentDrawingId: string;
  onLoadDrawing: (id: string) => void;
  onNewDrawing: () => void;
  improvementsIndex: ImprovementIndexEntry[];
  currentImprovementId: string | null;
  onLoadImprovement: (id: string) => void;
  runs: RunRecord[];
  staticAnalysisKpis: StaticAnalysisKpiReport | null;
  backlog: BacklogDocument | null;
  onClaimBacklogTask: () => void;
  onClaimBacklogTest: () => void;
  onRefreshBacklog: () => void;
  onCompleteBacklogTask: (taskId: string) => void;
  onUpdateBacklogChecklist: (taskId: string, phase: 'test' | 'implementation', checked: boolean) => void;
}

const ADDITION_WEIGHT = 1;
const REMOVAL_WEIGHT = 2;

const FINDING_KIND_LABELS: Record<string, string> = {
  deep_nesting: 'Aninhamento profundo',
  'draw.level2_missing_code_ref': 'Nós do nível 2 sem símbolo',
  'draw.level3_missing_code_ref': 'Nós do nível 3 sem símbolo',
  [['hardcoded', 'secret'].join('_')]: 'Segredo exposto no código',
  high_complexity: 'Alta complexidade',
  long_function: 'Função longa',
  too_many_parameters: 'Muitos parâmetros'
};

const formatFindingKind = (kind: string): string => FINDING_KIND_LABELS[kind] || kind.replaceAll('_', ' ');

const formatStackItem = (item: string): string => {
  if (item === 'draw-editor:javascript') return 'Editor visual (JavaScript)';
  if (item === 'pytest') return 'Pytest';
  return item;
};

const detailFile = (detail: Record<string, any>): string => String(detail.file || detail.source_file || 'Arquivo não informado');

const detailLine = (detail: Record<string, any>): string => {
  const line = detail.line ?? detail.start_line;
  return typeof line === 'number' ? `:${line}` : '';
};

const detailTitle = (detail: Record<string, any>): string => {
  if (typeof detail.kind === 'string') return formatFindingKind(detail.kind);
  if (typeof detail.qualified_name === 'string') return detail.qualified_name;
  if (typeof detail.name === 'string') return detail.name;
  if (typeof detail.target === 'string') return `Dependência: ${detail.target}`;
  return 'Referência encontrada';
};

const detailDescription = (detail: Record<string, any>): string => {
  if (typeof detail.evidence === 'string') return detail.evidence;
  if (typeof detail.symbol_id === 'string') return detail.symbol_id;
  if (typeof detail.resolution === 'string') return `Resolução: ${detail.resolution}`;
  return 'A análise encontrou uma referência neste arquivo.';
};

const groupDetailsByFile = (details: Array<Record<string, any>>) => {
  const groups = new Map<string, { file: string; count: number; lines: string[] }>();
  details.forEach((detail) => {
    const file = detailFile(detail);
    const group = groups.get(file) || { file, count: 0, lines: [] };
    group.count += 1;
    const line = detailLine(detail);
    if (line && !group.lines.includes(line.slice(1))) group.lines.push(line.slice(1));
    groups.set(file, group);
  });
  return Array.from(groups.values()).sort((a, b) => b.count - a.count || a.file.localeCompare(b.file));
};

const calculateWeightedRunScore = (linesAdded: number, linesRemoved: number): number => {
  const added = Math.max(0, Number(linesAdded) || 0);
  const removed = Math.max(0, Number(linesRemoved) || 0);
  const weightedChanges = added * ADDITION_WEIGHT + removed * REMOVAL_WEIGHT;
  if (weightedChanges === 0) return 50;
  return Math.round((added * ADDITION_WEIGHT * 100) / weightedChanges);
};

export const Sidebar: React.FC<SidebarProps> = ({
  dock,
  contract,
  selectedNode,
  selectedEdge,
  activeFlowId,
  onUpdateContract,
  onSelectNode,
  onSelectEdge,
  onSelectFlow,
  onOpenImportExport,
  drawingsIndex,
  currentDrawingId,
  onLoadDrawing,
  onNewDrawing,
  improvementsIndex,
  currentImprovementId,
  onLoadImprovement,
  runs,
  staticAnalysisKpis,
  backlog,
  onClaimBacklogTask,
  onClaimBacklogTest,
  onRefreshBacklog,
  onCompleteBacklogTask,
  onUpdateBacklogChecklist
}) => {
  const contentRef = useRef<HTMLDivElement>(null);

  const redirectBottomWheel = (event: React.WheelEvent<HTMLElement>) => {
    if (dock !== 'bottom' || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    const content = contentRef.current;
    if (!content) return;
    event.preventDefault();
    content.scrollLeft += event.deltaY;
  };

  const formatRunDate = (timestamp: string) => {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return timestamp;
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
      timeZone: 'America/Sao_Paulo'
    }).format(date);
  };

  const [activeTab, setActiveTab] = useState<'drawings' | 'analysis' | 'runs' | 'backlog' | 'info' | 'blocks' | 'groups' | 'flows'>('runs');
  const [drawingSearchQuery, setDrawingSearchQuery] = useState('');
  const [showZeroLineRuns, setShowZeroLineRuns] = useState(false);
  const [showAllRuns, setShowAllRuns] = useState(false);
  const [selectedIndicatorId, setSelectedIndicatorId] = useState<string | null>(null);
  const [showAnalysisSummary, setShowAnalysisSummary] = useState(false);

  // Selected Node State
  const [newQuestionPrompt, setNewQuestionPrompt] = useState('');
  const [newQuestionType, setNewQuestionType] = useState<'open' | 'boolean' | 'choice'>('open');
  const [newQuestionOptionsText, setNewQuestionOptionsText] = useState('');



  // Add Group State
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDesc, setNewGroupDesc] = useState('');
  const [newGroupColor, setNewGroupColor] = useState('#8b5cf6');

  // Add Flow Path State
  const [newFlowLabel, setNewFlowLabel] = useState('');
  const [newFlowTitle, setNewFlowTitle] = useState('');
  const [newFlowSummary, setNewFlowSummary] = useState('');

  // Add Node State (Geral Tab)
  const [newNodeLabel, setNewNodeLabel] = useState('');
  const [newNodeGroup, setNewNodeGroup] = useState<string>('');
  const [newNodeDesc, setNewNodeDesc] = useState('');

  const isEmptyDrawing = contract.nodes.length === 0;

  useEffect(() => {
    if (isEmptyDrawing) setActiveTab('info');
  }, [currentDrawingId, isEmptyDrawing]);

  useEffect(() => {
    const openEdgeEditor = () => setActiveTab('blocks');
    window.addEventListener('looper:edit-edge', openEdgeEditor);
    return () => window.removeEventListener('looper:edit-edge', openEdgeEditor);
  }, []);

  const filteredDrawings = drawingsIndex.filter((draw) =>
    `${draw.title} ${draw.subtitle} ${draw.kind}`.toLowerCase().includes(drawingSearchQuery.toLowerCase())
  );
  const filteredImprovements = improvementsIndex.filter((improvement) =>
    `${improvement.title} ${improvement.draw_id} ${improvement.status}`.toLowerCase().includes(drawingSearchQuery.toLowerCase())
  );
  const drawingsByLevel = filteredDrawings.reduce<Record<string, DrawIndexEntry[]>>((levels, draw) => {
    const level = draw.hierarchy?.level ? String(draw.hierarchy.level) : 'unassigned';
    levels[level] = [...(levels[level] || []), draw];
    return levels;
  }, {});
  const hierarchyChildren = filteredDrawings.reduce<Map<string, DrawIndexEntry[]>>((children, draw) => {
    const parentId = draw.hierarchy?.parent_draw_ref;
    if (!parentId) return children;
    children.set(parentId, [...(children.get(parentId) || []), draw]);
    return children;
  }, new Map());
  const drawingById = new Map(drawingsIndex.map((draw) => [draw.id, draw]));
  const levelGroups = Object.entries(drawingsByLevel).sort(([left], [right]) => {
    if (left === 'unassigned') return 1;
    if (right === 'unassigned') return -1;
    return Number(left) - Number(right);
  });

  const isZeroLineRun = (run: RunRecord) =>
    Boolean(run.checkpoint) ||
    (Number(run.diff_stats?.lines_added || 0) === 0 && Number(run.diff_stats?.lines_deleted || 0) === 0);
  const isRunFromToday = (run: RunRecord) => {
    const runDate = new Date(run.timestamp);
    const today = new Date();
    return !Number.isNaN(runDate.getTime()) &&
      runDate.getFullYear() === today.getFullYear() &&
      runDate.getMonth() === today.getMonth() &&
      runDate.getDate() === today.getDate();
  };
  const periodRuns = showAllRuns ? runs : runs.filter(isRunFromToday);
  const visibleRuns = showZeroLineRuns ? periodRuns : periodRuns.filter((run) => !isZeroLineRun(run));

  const analysisIndicators = (staticAnalysisKpis?.indicators || []).slice().sort((a, b) => {
    return (a.id || '').localeCompare(b.id || '');
  });

  const analysisFindings = Object.entries(staticAnalysisKpis?.summary?.findings_by_kind || {});

  const detailsForIndicator = (indicatorId: string): Array<Record<string, any>> => {
    const details = staticAnalysisKpis?.details;
    const qualityFindings = details?.quality_findings || [];
    if (indicatorId.startsWith('finding:')) {
      const findingKind = indicatorId.slice('finding:'.length);
      return qualityFindings.filter((item) => item.kind === findingKind);
    }
    if (indicatorId === 'quality_findings') return qualityFindings;
    if (indicatorId === 'blocking_findings') return qualityFindings.filter((item) => item.severity === 'blocking');
    if (indicatorId === 'applied_exceptions') return qualityFindings.filter((item) => item.exception_applied);
    if (indicatorId === 'expired_exceptions') return qualityFindings.filter((item) => item.kind === 'static_analysis.exception_expired');
    if (indicatorId === 'symbols') return details?.symbols || [];
    if (indicatorId === 'dependencies') return details?.dependencies || [];
    if (indicatorId === 'files') return (staticAnalysisKpis?.summary?.files || []).map((file) => ({ file }));
    return [];
  };

  const selectedIndicatorDetails = selectedIndicatorId ? detailsForIndicator(selectedIndicatorId) : [];
  const selectedIndicatorFiles = groupDetailsByFile(selectedIndicatorDetails);
  const selectedNodeTask = selectedNode
    ? backlog?.tasks.find((task) => task.draw_id === currentDrawingId && task.node_id === selectedNode.id)
    : undefined;
  const selectedChecklistTaskIds = selectedNodeTask
    ? new Set([selectedNodeTask.id, ...(selectedNodeTask.child_task_ids || [])])
    : new Set<string>();
  const selectedTestChecklist = (backlog?.phase_checklists?.test || []).filter((item) => selectedChecklistTaskIds.has(item.task_id));
  const selectedImplementationChecklist = (backlog?.phase_checklists?.implementation || []).filter((item) => selectedChecklistTaskIds.has(item.task_id));
  const runTotals = visibleRuns.reduce((totals, run) => {
    const added = Number(run.diff_stats?.lines_added || 0);
    const removed = Number(run.diff_stats?.lines_deleted || 0);
    return {
      added: totals.added + added,
      removed: totals.removed + removed
    };
  }, { added: 0, removed: 0 });
  const weightedRunTotals = visibleRuns.reduce((totals, run) => {
    const added = Number(run.diff_stats?.lines_added || 0);
    const removed = Number(run.diff_stats?.lines_deleted || 0);
    const weightedRemoved = removed > added ? removed * 2 : removed;
    return {
      added: totals.added + added,
      removed: totals.removed + weightedRemoved
    };
  }, { added: 0, removed: 0 });
  const netLineBalance = runTotals.added - runTotals.removed;
  const weightedRunScore = calculateWeightedRunScore(weightedRunTotals.added, weightedRunTotals.removed);

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
        description: newGroupDesc.trim() || undefined,
        color: newGroupColor
      };
      return {
        ...prev,
        groups: [...prev.groups, newGroup]
      };
    });

    setNewGroupName('');
    setNewGroupDesc('');
    setNewGroupColor('#8b5cf6');
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
    <aside className="sidebar" onWheelCapture={redirectBottomWheel}>
      {/* Brand Section */}
      <div className="brand">
        <img className="brand-mark brand-logo" src={brandLogo} alt="Looper" />
        <div>
          <h1 className="brand-title">Looper</h1>
          <p className="brand-tagline">Architecture & Design Visualizer</p>
        </div>
      </div>

      {/* Tabs Menu */}
      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab-btn ${activeTab === 'runs' ? 'active' : ''}`}
          onClick={() => setActiveTab('runs')}
        >
          <Activity size={14} />
          <span>Runs</span>
        </button>
        <button
          className={`sidebar-tab-btn ${activeTab === 'drawings' ? 'active' : ''}`}
          onClick={() => setActiveTab('drawings')}
        >
          <FolderPlus size={14} />
          <span>Desenhos</span>
        </button>
        <button
          className={`sidebar-tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
          title="Indicadores da análise estática"
        >
          <BarChart3 size={14} />
          <span>Análise</span>
        </button>
        <button
          className={`sidebar-tab-btn ${activeTab === 'backlog' ? 'active' : ''}`}
          onClick={() => setActiveTab('backlog')}
          title="Tasks pendentes por jornada"
        >
          <List size={14} />
          <span>Backlog</span>
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

      <div className="sidebar-content" ref={contentRef}>
        {activeTab === 'backlog' && (
          <BacklogPanel backlog={backlog} onClaimTask={onClaimBacklogTask} onClaimTest={onClaimBacklogTest} onRefresh={onRefreshBacklog} onCompleteTask={onCompleteBacklogTask} onUpdateChecklist={onUpdateBacklogChecklist} />
        )}

        {/* Tab 0: Drawings list */}
        {activeTab === 'drawings' && (
          <div className="sidebar-pane">
            <button className="sidebar-submit-btn" onClick={onNewDrawing} style={{ margin: '4px 0 8px' }}>
              <Plus size={14} />
              Novo Desenho
            </button>
            <button
              className="quick-action-btn secondary"
              onClick={() => setActiveTab('info')}
              style={{ width: '100%', marginBottom: '10px' }}
            >
              <Plus size={14} />
              Adicionar Bloco
            </button>

            <div className="editor-field" style={{ marginBottom: '8px' }}>
              <input
                className="search-input"
                style={{ margin: 0 }}
                placeholder="Buscar desenho..."
                value={drawingSearchQuery}
                onChange={(e) => setDrawingSearchQuery(e.target.value)}
              />
            </div>

            <div className="draw-hierarchy-card">
              <div className="draw-hierarchy-heading">
                <div>
                  <span className="eyebrow">Navegação</span>
                  <h3>Navegação por nível</h3>
                </div>
                <span className="draw-hierarchy-count">{filteredDrawings.length} fluxos</span>
              </div>
              <p className="draw-hierarchy-help">
                Encontre um fluxo pelo nível e abra seus subfluxos a partir do desenho pai.
              </p>
              {levelGroups.length === 0 ? (
                <div className="draw-hierarchy-empty" role="status">
                  <span className="draw-hierarchy-empty-icon" aria-hidden="true">
                    <FolderPlus size={18} />
                  </span>
                  <strong>Nenhuma hierarquia disponível</strong>
                  <p>Crie ou carregue um desenho para organizar os fluxos por nível.</p>
                  <span className="draw-hierarchy-empty-hint">Os subfluxos aparecerão aqui automaticamente.</span>
                </div>
              ) : (
                <div className="draw-level-groups">
                  {levelGroups.map(([level, drawings]) => (
                    <details key={level} className="draw-level-group" open={level === '1' || level === 'unassigned'}>
                      <summary>
                        <span>{level === 'unassigned' ? 'Sem nível' : `Nível ${level}`}</span>
                        <small>{drawings.length} {drawings.length === 1 ? 'fluxo' : 'fluxos'}</small>
                      </summary>
                      <div className="draw-level-items">
                        {drawings.map((draw) => {
                          const parent = draw.hierarchy?.parent_draw_ref
                            ? drawingById.get(draw.hierarchy.parent_draw_ref)
                            : undefined;
                          const children = hierarchyChildren.get(draw.id) || [];
                          return (
                            <div key={draw.id} className="draw-level-item">
                              <button
                                className={`draw-level-link ${currentDrawingId === draw.id ? 'active' : ''}`}
                                onClick={() => onLoadDrawing(draw.id)}
                              >
                                <span className="draw-level-link-title">{draw.title}</span>
                                <span className="draw-level-link-meta">
                                  {parent ? `Subfluxo de ${parent.title}` : draw.kind || 'desenho'}
                                </span>
                              </button>
                              {children.length > 0 && (
                                <div className="draw-subflow-links">
                                  <span className="draw-subflow-label">{children.length} subfluxo{children.length === 1 ? '' : 's'}</span>
                                  {children.map((child) => (
                                    <button
                                      key={child.id}
                                      className={`draw-subflow-link ${currentDrawingId === child.id ? 'active' : ''}`}
                                      onClick={() => onLoadDrawing(child.id)}
                                    >
                                      <ChevronRight size={12} />
                                      <span>{child.title}</span>
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </div>

            <div className="drawings-all-card">
              <div className="drawings-all-heading">
                <div>
                  <span className="eyebrow">Catálogo completo</span>
                  <h3>Todos os desenhos</h3>
                </div>
                <span className="draw-hierarchy-count">{filteredDrawings.length}</span>
              </div>
              <div className="draw-list">
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

            <div className="drawings-all-card improvement-sessions-card">
              <div className="drawings-all-heading">
                <div>
                  <span className="eyebrow">Perguntas humanas</span>
                  <h3>Sessões de melhoria</h3>
                </div>
                <span className="draw-hierarchy-count">{filteredImprovements.length}</span>
              </div>
              <div className="draw-list">
                {filteredImprovements.length === 0 ? (
                  <p className="no-items-hint" style={{ textAlign: 'center', padding: '16px', color: 'var(--muted)', fontSize: '11px' }}>
                    Nenhuma sessão de melhoria criada.
                  </p>
                ) : filteredImprovements.map((improvement) => (
                  <button
                    key={improvement.id}
                    className={`flow-path-select-btn ${currentImprovementId === improvement.id ? 'active' : ''}`}
                    onClick={() => onLoadImprovement(improvement.id)}
                    style={{ width: '100%', textAlign: 'left', padding: '12px 14px', display: 'block' }}
                  >
                    <strong style={{ display: 'block', fontSize: '13px', fontWeight: 800 }}>{improvement.title}</strong>
                    <span style={{ display: 'block', fontSize: '10.5px', color: 'var(--muted)', marginTop: '4px', lineHeight: '1.3' }}>
                      Draw: {improvement.draw_id}
                    </span>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '6px', fontSize: '9px', fontWeight: 800, color: 'var(--muted)' }}>
                      <span>{improvement.answered_count}/{improvement.question_count} respostas</span>
                      <span>•</span>
                      <span>{improvement.status}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analysis' && (
          <div className="sidebar-pane static-analysis-pane">
            <div className="runs-sidebar-heading">
              <div>
                <span className="eyebrow">Visão estrutural</span>
                <h3>Saúde do código</h3>
              </div>
              <span className={`static-analysis-status ${staticAnalysisKpis?.status || 'unavailable'}`}>
                {staticAnalysisKpis?.status === 'passed' ? 'OK' : staticAnalysisKpis?.status === 'blocked' ? 'BLOQUEADO' : 'INDISPONÍVEL'}
              </span>
            </div>
            {!staticAnalysisKpis ? (
              <div className="runs-empty-sidebar static-analysis-empty">
                <BarChart3 size={22} />
                <strong>Análise ainda não executada</strong>
                <span>Execute <code>looper test</code> para atualizar os indicadores da base.</span>
              </div>
            ) : (
              <>
                <button
                  type="button"
                  className={`static-analysis-summary-toggle ${showAnalysisSummary ? 'open' : ''}`}
                  onClick={() => setShowAnalysisSummary((current) => !current)}
                  aria-expanded={showAnalysisSummary}
                  aria-controls="static-analysis-kpi-grid"
                >
                  <ChevronRight className="static-analysis-summary-chevron" size={15} aria-hidden="true" />
                  <span>
                    <strong>Resumo da análise</strong>
                    <small>{staticAnalysisKpis.summary?.symbols?.toLocaleString('pt-BR') || 0} símbolos encontrados</small>
                  </span>
                </button>
                {showAnalysisSummary && <div className="static-analysis-kpi-grid" id="static-analysis-kpi-grid">
                  {analysisIndicators.map((indicator) => (
                    <div
                      className={`static-analysis-kpi-card ${indicator.status || ''}`}
                      key={indicator.id}
                    >
                      <span className="static-analysis-kpi-label">{indicator.label}</span>
                      <strong>{indicator.value.toLocaleString('pt-BR')}</strong>
                      <small>{indicator.unit || 'itens'}</small>
                    </div>
                  ))}
                </div>}
                {selectedIndicatorId && (
                  <div className="editor-card static-analysis-occurrences">
                    <div className="static-analysis-occurrences-heading">
                      <div>
                        <span className="eyebrow">Evidências da análise</span>
                        <h4>{selectedIndicatorId?.startsWith('finding:')
                          ? formatFindingKind(selectedIndicatorId.slice('finding:'.length))
                          : analysisIndicators.find((indicator) => indicator.id === selectedIndicatorId)?.label || 'Indicador selecionado'}</h4>
                      </div>
                      <button type="button" className="static-analysis-close-details" onClick={() => setSelectedIndicatorId(null)}>Fechar</button>
                    </div>
                    {selectedIndicatorDetails.length === 0 ? (
                      <p className="static-analysis-no-occurrences">Nenhuma ocorrência detalhada foi retornada para este indicador.</p>
                    ) : (
                      <>
                        <div className="static-analysis-file-classification">
                          <span className="eyebrow">Arquivos classificados por este indicador</span>
                          {selectedIndicatorFiles.map((group) => (
                            <div className="static-analysis-file-group" key={group.file}>
                              <code>{group.file}</code>
                              <strong>{group.count}</strong>
                              {group.lines.length > 0 && <small>linhas {group.lines.slice(0, 5).join(', ')}</small>}
                            </div>
                          ))}
                        </div>
                        <div className="static-analysis-occurrence-list">
                          {selectedIndicatorDetails.slice(0, 30).map((detail, index) => (
                            <article className="static-analysis-occurrence" key={`${detailFile(detail)}-${detailLine(detail)}-${index}`}>
                              <div className="static-analysis-occurrence-topline">
                                <strong>{detailTitle(detail)}</strong>
                                {detail.severity && <span className={`static-analysis-severity ${detail.severity}`}>{detail.severity === 'blocking' ? 'Bloqueante' : 'Atenção'}</span>}
                              </div>
                              <code>{detailFile(detail)}{detailLine(detail)}</code>
                              <p>{detailDescription(detail)}</p>
                            </article>
                          ))}
                        </div>
                      </>
                    )}
                    {selectedIndicatorDetails.length > 30 && <small className="static-analysis-occurrences-more">Mostrando 30 de {selectedIndicatorDetails.length} ocorrências.</small>}
                  </div>
                )}
                <div className="editor-card static-analysis-detail-card">
                  <span className="eyebrow">Tecnologias encontradas</span>
                  <div className="static-analysis-tags">
                    {(staticAnalysisKpis.stack?.languages || []).map((item) => <span key={`language-${item}`}>{formatStackItem(item)}</span>)}
                    {(staticAnalysisKpis.stack?.frameworks || []).map((item) => <span key={`framework-${item}`}>{formatStackItem(item)}</span>)}
                    {(staticAnalysisKpis.stack?.test_runners || []).map((item) => <span key={`runner-${item}`}>{formatStackItem(item)}</span>)}
                  </div>
                  <div className="static-analysis-breakdown">
                    {analysisFindings.map(([kind, count]) => (
                      <button
                        className={`static-analysis-finding-item ${selectedIndicatorId === `finding:${kind}` ? 'selected' : ''}`}
                        key={kind}
                        type="button"
                        onClick={() => setSelectedIndicatorId((current) => current === `finding:${kind}` ? null : `finding:${kind}`)}
                        aria-label={`Ver arquivos de ${formatFindingKind(kind)}`}
                      >
                        <ChevronRight className={`static-analysis-finding-toggle ${selectedIndicatorId === `finding:${kind}` ? 'open' : ''}`} size={14} aria-hidden="true" />
                        <span>{formatFindingKind(kind)}</span>
                        <strong>{count}</strong>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="sidebar-pane">
            <div className="runs-sidebar-heading">
              <div>
                <span className="eyebrow">Histórico do agente</span>
                <h3>Runs registradas</h3>
              </div>
              <span className="runs-total-badge">{visibleRuns.length}</span>
            </div>
            <div className="runs-filters">
              <div className="runs-scope-toggle" role="group" aria-label="Período das alterações">
                <button
                  type="button"
                  className={!showAllRuns ? 'active' : ''}
                  onClick={() => setShowAllRuns(false)}
                  aria-pressed={!showAllRuns}
                >
                  Hoje
                </button>
                <button
                  type="button"
                  className={showAllRuns ? 'active' : ''}
                  onClick={() => setShowAllRuns(true)}
                  aria-pressed={showAllRuns}
                >
                  Todas as alterações
                </button>
              </div>
              <label className="runs-filter-toggle">
                <input
                  type="checkbox"
                  checked={showZeroLineRuns}
                  onChange={(event) => setShowZeroLineRuns(event.target.checked)}
                />
                <span>Mostrar checkpoints (0 linhas)</span>
              </label>
            </div>
            <div className="runs-total-card">
              <div className="runs-total-card-header">
                <span className="eyebrow">Eficiência</span>
                <div className="runs-score-summary" title="O saldo usa as linhas reais. Na nota, remoções têm peso 2 e dobram novamente quando uma run remove mais do que adiciona.">
                  <span>Nota ponderada</span>
                  <strong>{weightedRunScore}<small>/100</small></strong>
                </div>
              </div>
              <div className="runs-total-progress" aria-label={`Nota ponderada: ${weightedRunScore}/100`}>
                <span style={{ width: `${weightedRunScore}%` }} />
              </div>
              <div className="runs-total-grid">
                <div><strong className="run-stat-added">+{runTotals.added}</strong><span>adicionadas</span></div>
                <div><strong className="run-stat-removed">−{runTotals.removed}</strong><span>removidas</span></div>
                <div><strong className={netLineBalance >= 0 ? 'run-stat-added' : 'run-stat-removed'}>{netLineBalance >= 0 ? '+' : '−'}{Math.abs(netLineBalance)}</strong><span>saldo final</span></div>
              </div>
            </div>
            {visibleRuns.length === 0 ? (
              <div className="runs-empty-sidebar">
                <Activity size={22} />
                <strong>{periodRuns.length === 0 ? (showAllRuns ? 'Nenhum registro encontrado' : 'Nenhuma run hoje') : 'Nenhuma run visível'}</strong>
                <span>{periodRuns.length === 0
                  ? (showAllRuns ? 'As execuções aparecerão aqui quando o Looper registrar um summary.' : 'Alterne para todas as alterações para consultar o histórico completo.')
                  : 'Desative o filtro para mostrar os checkpoints de 0 linhas.'}</span>
              </div>
            ) : (
              <div className="runs-sidebar-list">
                {visibleRuns.map((run) => (
                  <article key={run.run_id} className="run-sidebar-card">
                    <span className="run-sidebar-date">{formatRunDate(run.timestamp)}</span>
                    <strong className="run-sidebar-summary">{run.description || 'Sem resumo registrado'}</strong>
                    <div className="run-sidebar-types">
                      {(run.work_types || []).length > 0
                        ? run.work_types.map((type) => <span key={type}>{type}</span>)
                        : <span>tipo não informado</span>}
                      {isZeroLineRun(run) && <span>checkpoint</span>}
                    </div>
                    <div className="run-sidebar-stats" aria-label="Impacto da alteração">
                      <span className="run-stat-added">+{run.diff_stats?.lines_added || 0} linhas</span>
                      <span className="run-stat-removed">−{run.diff_stats?.lines_deleted || 0} removidas</span>
                      <span>{run.diff_stats?.files_changed || 0} arquivos</span>
                    </div>
                  </article>
                ))}
              </div>
            )}
            <p className="runs-sidebar-note">Resumo das execuções registradas pelo agente.</p>
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
                {selectedNodeTask && (
                  <div className="node-questions-sub-editor backlog-node-checklists">
                    <h4>Checklist do backlog</h4>
                    <strong>Testes</strong>
                    {selectedTestChecklist.length === 0 ? <span>Nenhum teste associado.</span> : selectedTestChecklist.map((item) => (
                      <label className="backlog-checklist-item" key={item.id}>
                        <input
                          type="checkbox"
                          checked={item.checked}
                          onChange={(event) => onUpdateBacklogChecklist(item.task_id, 'test', event.target.checked)}
                        />
                        <span>{item.label}</span>
                        {item.evidence_status !== 'done' && <small>marcação manual</small>}
                      </label>
                    ))}
                    <strong>Implementação</strong>
                    {selectedImplementationChecklist.length === 0 ? <span>Nenhuma implementação associada.</span> : selectedImplementationChecklist.map((item) => (
                      <label className="backlog-checklist-item" key={item.id}>
                        <input
                          type="checkbox"
                          checked={item.checked}
                          onChange={(event) => onUpdateBacklogChecklist(item.task_id, 'implementation', event.target.checked)}
                        />
                        <span>{item.label}</span>
                      </label>
                    ))}
                  </div>
                )}
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
                  <label>Cor do grupo</label>
                  <input
                    type="color"
                    value={newGroupColor}
                    onChange={(e) => setNewGroupColor(e.target.value)}
                    aria-label="Cor do grupo"
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

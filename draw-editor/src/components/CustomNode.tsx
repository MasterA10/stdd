import React, { useState, useEffect, useRef } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';
import type { NodeData, Question, ChangeRequest } from '../types';
import { Trash2, ClipboardList, Eye, Code2, Repeat2 } from 'lucide-react';
import { renderWithMentions } from '../utils';

const FALLBACK_GROUP_COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f97316', '#ec4899', '#3b82f6'];
const DARK_GROUP_FILLS = ['#242424', '#2d2d2d', '#363636', '#404040', '#4a4a4a', '#545454'];

function groupColor(groupId?: number, color?: string) {
  if (color) return color;
  if (groupId === undefined) return '#94a3b8';
  return FALLBACK_GROUP_COLORS[Math.abs(groupId) % FALLBACK_GROUP_COLORS.length];
}

function darkGroupFill(groupId?: number) {
  if (groupId === undefined) return '#1f1f1f';
  return DARK_GROUP_FILLS[Math.abs(groupId) % DARK_GROUP_FILLS.length];
}

function withAlpha(hex: string, alpha: number) {
  const normalized = hex.replace('#', '');
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return `rgba(148, 163, 184, ${alpha})`;
  const red = parseInt(normalized.slice(0, 2), 16);
  const green = parseInt(normalized.slice(2, 4), 16);
  const blue = parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function withTint(hex: string, whiteAmount: number) {
  const normalized = hex.replace('#', '');
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return '#f8fafc';
  const channel = (offset: number) => {
    const value = parseInt(normalized.slice(offset, offset + 2), 16);
    return Math.round(value + (255 - value) * whiteAmount);
  };
  return `rgb(${channel(0)}, ${channel(2)}, ${channel(4)})`;
}

function unansweredQuestionCount(questions?: Question[]) {
  const qList = Array.isArray(questions) ? questions : [];
  return qList.filter(q => q.answer === null || q.answer === undefined || (typeof q.answer === 'string' && !q.answer.trim())).length;
}

export const CustomNode: React.FC<NodeProps<Node<NodeData, 'custom'>>> = ({ id, data, selected }) => {
  const [editingField, setEditingField] = useState<'label' | 'description' | null>(null);
  const [isEditingGroup, setIsEditingGroup] = useState(false);
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const groupInfo = data.group !== undefined && window.getGroupInfo ? window.getGroupInfo(data.group) : undefined;
  const accentColor = groupColor(data.group, groupInfo?.color);
  const isDarkTheme = data.theme === 'dark' || data.theme === 'black';
  const groupOptions = Array.isArray(data.groupOptions) ? data.groupOptions : [];

  const totalQuestions = Array.isArray(data.questions) ? data.questions.length : 0;
  const unansweredQuestions = unansweredQuestionCount(data.questions);
  const answeredQuestions = totalQuestions - unansweredQuestions;
  const subdrawRefs = data.draw_refs?.length ? data.draw_refs : (data.draw_ref ? [data.draw_ref] : []);
  const codeReferenceCount = Array.isArray(data.code_refs) ? data.code_refs.length : 0;
  const pendingChangeCount = (data.changes || []).filter((change: ChangeRequest) => change.status !== 'done').length;
  const backlogChecklist = data.backlogChecklist;
  const backlogTaskStatus = backlogChecklist?.status;
  const isBacklogTaskInProgress = backlogTaskStatus === 'in_progress';
  const isBacklogTaskDone = backlogTaskStatus === 'done';
  const hasAssociatedTest = backlogChecklist?.test === true
    || Boolean(data.test_ref)
    || (Array.isArray(data.test_refs) && data.test_refs.length > 0);

  const isHighlighted = data.isHighlighted;
  const isDimmed = data.isDimmed;

  useEffect(() => {
    if (editingField === 'label' && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    } else if (editingField === 'description' && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, [editingField]);

  useEffect(() => {
    const clearEditing = () => {
      setEditingField(null);
      setIsEditingGroup(false);
    };
    window.addEventListener('looper:clear-node-editing', clearEditing);
    return () => window.removeEventListener('looper:clear-node-editing', clearEditing);
  }, []);

  const handleDoubleClick = (field: 'label' | 'description', e: React.MouseEvent) => {
    e.stopPropagation();
    setDraft(data[field] || '');
    setEditingField(field);
  };

  const finishEdit = () => {
    if (!editingField) return;
    const value = draft.trim();
    if (window.updateNodeField) {
      window.updateNodeField(Number(id), editingField, value);
    }
    setEditingField(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && editingField === 'label') {
      finishEdit();
    } else if (e.key === 'Escape') {
      setEditingField(null);
      setIsEditingGroup(false);
    }
  };

  const handleNodeDoubleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('input, textarea, select, button')) return;
    e.stopPropagation();
    setEditingField(null);
    setIsEditingGroup(true);
  };

  const handleGroupChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    window.updateNodeGroup?.(Number(id), value === '' ? undefined : Number(value));
    setIsEditingGroup(false);
  };

  const onDeleteNode = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.deleteNode) {
      window.deleteNode(Number(id));
    }
  };

  const onOpenQuestions = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.openQuestionsModal) {
      window.openQuestionsModal(data);
    }
  };

  const onOpenChanges = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.openChangesModal?.(data);
  };

  const onOpenCodeReferences = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.openCodeReferencesModal?.(data);
  };

  const onToggleBacklogChecklist = (phase: 'test' | 'implementation', checked: boolean) => (e: React.SyntheticEvent) => {
    e.stopPropagation();
    if (backlogChecklist && window.updateBacklogChecklist) {
      void window.updateBacklogChecklist(backlogChecklist.taskId, phase, checked);
    }
  };

  // Node visual styles
  const borderStyle = isBacklogTaskDone
    ? {
      borderColor: accentColor,
      borderWidth: '2px',
      boxShadow: `0 0 0 3px ${withAlpha(accentColor, 0.2)}, 0 10px 26px rgba(234, 88, 12, .18)`
    }
    : selected
    ? { borderColor: '#6366f1', borderWidth: '2.5px', boxShadow: '0 0 0 4px rgba(99, 102, 241, 0.15)' }
    : isHighlighted
    ? { borderColor: '#10b981', borderWidth: '2.5px', boxShadow: '0 0 0 4px rgba(16, 185, 129, 0.2)' }
    : { borderColor: accentColor };

  const bgStyle = {
    background: isDarkTheme
      ? isBacklogTaskDone
        ? 'var(--brand-gradient)'
        : isBacklogTaskInProgress
        ? 'var(--brand-gradient)'
        : darkGroupFill(data.group)
      : isBacklogTaskDone
      ? 'var(--brand-gradient)'
      : isBacklogTaskInProgress
      ? 'var(--brand-gradient)'
      : data.group !== undefined
      ? withTint(accentColor, 0.82)
      : '#f8fafc',
    color: isBacklogTaskInProgress || isBacklogTaskDone || isDarkTheme ? '#f8fafc' : '#0f172a',
    opacity: isDimmed ? 0.08 : 1
  };
  const groupPillStyle = isDarkTheme
    ? { backgroundColor: accentColor, color: '#ffffff' }
    : { backgroundColor: withAlpha(accentColor, 0.22), color: accentColor };

  return (
    <div
      className={`custom-flow-node ${selected ? 'selected' : ''} ${isHighlighted ? 'highlighted' : ''} ${isDimmed ? 'dimmed' : ''} ${isBacklogTaskInProgress ? 'backlog-task-in-progress' : ''} ${isBacklogTaskDone ? 'backlog-task-done' : ''}`}
      style={{ ...borderStyle, ...bgStyle }}
      title={isBacklogTaskInProgress ? 'Task em andamento' : isBacklogTaskDone ? 'Task pronta' : undefined}
      onDoubleClick={handleNodeDoubleClick}
    >
      {/* Node actions toolbar */}
      {(selected || isHighlighted) && (
        <div className="node-action-container">
          <button
            className="action-circle-btn danger"
            onClick={onDeleteNode}
            title="Excluir Bloco"
            type="button"
          >
            <Trash2 size={12} />
          </button>
          <button
            className="action-circle-btn info"
            onClick={onOpenQuestions}
            title="Perguntas e observações do bloco"
            type="button"
          >
            <ClipboardList size={12} />
          </button>
          <button
            className="action-circle-btn info"
            onClick={onOpenChanges}
            title={pendingChangeCount ? `${pendingChangeCount} alteração(ões) pendente(s)` : 'Pedidos de alteração do bloco'}
            type="button"
          >
            <Repeat2 size={12} />
          </button>
          <button
            className="action-circle-btn info"
            style={{ backgroundColor: '#6366f1', color: '#fff' }}
            onClick={(e) => {
              e.stopPropagation();
              if (window.openDetailViewer) {
                window.openDetailViewer(Number(id));
              }
            }}
            title="Visualizar Conexões Detalhadas"
            type="button"
          >
            <Eye size={12} />
          </button>
          {backlogChecklist && (
            <>
              <label
                className="node-check-action test nodrag nopan"
                title="Marcar ou desmarcar checklist de teste"
                onClick={(e) => e.stopPropagation()}
                onPointerDown={(e) => e.stopPropagation()}
              >
                <input
                  className="nodrag nopan"
                  type="checkbox"
                  checked={backlogChecklist.test}
                  onChange={onToggleBacklogChecklist('test', !backlogChecklist.test)}
                  aria-label="Checklist de teste"
                />
                <span>T</span>
              </label>
              <label
                className={`node-check-action implementation nodrag nopan${backlogChecklist.test ? '' : ' locked'}`}
                title={backlogChecklist.test ? 'Marcar ou desmarcar checklist de implementação' : 'Conclua o checklist de teste antes da implementação'}
                onClick={(e) => e.stopPropagation()}
                onPointerDown={(e) => e.stopPropagation()}
              >
                <input
                  className="nodrag nopan"
                  type="checkbox"
                  checked={backlogChecklist.implementation}
                  disabled={!backlogChecklist.test}
                  onChange={onToggleBacklogChecklist('implementation', !backlogChecklist.implementation)}
                  aria-label="Checklist de implementação"
                />
                <span>I</span>
              </label>
            </>
          )}
        </div>
      )}

      {/* Top row: group badge only; flow decisions are represented by edges. */}
      <div className="node-top-bar">
        {isEditingGroup ? (
          <select
            className="node-group-select"
            autoFocus
            value={data.group === undefined ? '' : String(data.group)}
            onChange={handleGroupChange}
            onBlur={() => setIsEditingGroup(false)}
            onClick={(e) => e.stopPropagation()}
            aria-label="Grupo do bloco"
          >
            <option value="">Sem grupo</option>
            {groupOptions.map((group: any) => (
              <option key={group.id} value={group.id}>{group.label}</option>
            ))}
          </select>
        ) : (
          <span className="node-group-pill" style={groupPillStyle}>
            {groupInfo?.label || 'Sem grupo'}
          </span>
        )}
        <span className="node-header-id-wrap">
          <span className="node-header-id">#{id}</span>
          {hasAssociatedTest && (
            <span className="node-associated-test" role="img" title="Teste criado e associado" aria-label="Teste criado e associado">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#ffffff"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="lucide lucide-test-tube-diagonal"
                aria-hidden="true"
              >
                <path d="M21 7 6.82 21.18a2.83 2.83 0 0 1-3.99-.01a2.83 2.83 0 0 1 0-4L17 3" />
                <path d="m16 2 6 6" />
                <path d="M12 16H4" />
              </svg>
            </span>
          )}
        </span>
      </div>

      {/* Main Content */}
      <div className="node-body">
        {editingField === 'label' ? (
          <input
            className="inline-node-input"
            ref={inputRef}
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={finishEdit}
            onKeyDown={handleKeyDown}
          />
        ) : (
          <div
            className="node-body-title"
            onDoubleClick={(e) => handleDoubleClick('label', e)}
            title="Dê duplo clique para editar"
          >
            {data.label || 'Sem Nome'}
          </div>
        )}

        {editingField === 'description' ? (
          <textarea
            className="inline-node-textarea"
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={finishEdit}
            onKeyDown={handleKeyDown}
          />
        ) : (
          <div
            className="node-body-desc"
            onDoubleClick={(e) => {
              e.stopPropagation();
              window.openNodeEditModal?.(data);
            }}
            title="Dê duplo clique para editar descrição"
          >
            {renderWithMentions(data.description || 'Nenhuma descrição adicionada.')}
          </div>
        )}
      </div>

      {/* Node Footer Row (Questions or Subdraw link) */}
      {(totalQuestions > 0 || subdrawRefs.length > 0 || codeReferenceCount > 0) && (
        <>
          <div className="node-divider-line" />
          <div className="node-footer-row">
            {subdrawRefs.length > 0 ? (
              <div className="node-footer-subdraw-list">
                {subdrawRefs.map((subdrawRef) => (
                  <span
                    key={subdrawRef}
                    className="node-footer-subdraw"
                    onClick={(e) => {
                      e.stopPropagation();
                      window.openSubdraw?.(subdrawRef);
                    }}
                    title="Abrir subdesenho"
                  >
                    Detalhes: {subdrawRef} ↗
                  </span>
                ))}
              </div>
            ) : totalQuestions > 0 ? (
              <span className="node-footer-questions" onClick={onOpenQuestions}>
                Perguntas
              </span>
              ) : <span />}
            
            {totalQuestions > 0 && (
              <div className="question-counts-pill" onClick={onOpenQuestions}>
                {answeredQuestions > 0 && (
                  <span className="question-count answered" title="Respondidas">
                    {answeredQuestions}
                  </span>
                )}
                {unansweredQuestions > 0 && (
                  <span className="question-count unanswered" title="Sem resposta">
                    {unansweredQuestions}
                  </span>
                )}
              </div>
            )}
            {codeReferenceCount > 0 && (
              <button className="node-code-ref-pill" onClick={onOpenCodeReferences} type="button" title="Ver símbolos e arquivos associados">
                <Code2 size={11} />
                <span className="code-ref-count">{codeReferenceCount}</span>
              </button>
            )}
          </div>
        </>
      )}

      {/* ═══════════════════════════════════════════════════════════
          React Flow handles (4 Condition Ports per Side)
          Vertical: Target at 20%, then Cond 1 at 40%, Cond 2 at 60%, Cond 3 at 80%
          Horizontal: Target at 20%, then Cond 1 at 40%, Cond 2 at 60%, Cond 3 at 80%
          ═══════════════════════════════════════════════════════════ */}

      {/* LEFT SIDE */}
      <Handle type="target" position={Position.Left} id="target-in-left" className="handle-target" style={{ top: '20%' }} />
      <Handle type="source" position={Position.Left} id="source-1-left" className="handle-cond-1" style={{ top: '40%' }} />
      <Handle type="source" position={Position.Left} id="source-2-left" className="handle-cond-2" style={{ top: '60%' }} />
      <Handle type="source" position={Position.Left} id="source-3-left" className="handle-cond-3" style={{ top: '80%' }} />

      {/* RIGHT SIDE */}
      <Handle type="source" position={Position.Right} id="source-1-right" className="handle-cond-1" style={{ top: '40%' }} />
      <Handle type="source" position={Position.Right} id="source-2-right" className="handle-cond-2" style={{ top: '60%' }} />
      <Handle type="source" position={Position.Right} id="source-3-right" className="handle-cond-3" style={{ top: '80%' }} />

      {/* TOP SIDE */}
      <Handle type="target" position={Position.Top} id="target-in-top" className="handle-target" style={{ left: '20%' }} />
      <Handle type="source" position={Position.Top} id="source-1-top" className="handle-cond-1" style={{ left: '40%' }} />
      <Handle type="source" position={Position.Top} id="source-2-top" className="handle-cond-2" style={{ left: '60%' }} />
      <Handle type="source" position={Position.Top} id="source-3-top" className="handle-cond-3" style={{ left: '80%' }} />

      {/* BOTTOM SIDE */}
      <Handle type="target" position={Position.Bottom} id="target-in-bottom" className="handle-target" style={{ left: '20%' }} />
      <Handle type="source" position={Position.Bottom} id="source-1-bottom" className="handle-cond-1" style={{ left: '40%' }} />
      <Handle type="source" position={Position.Bottom} id="source-2-bottom" className="handle-cond-2" style={{ left: '60%' }} />
      <Handle type="source" position={Position.Bottom} id="source-3-bottom" className="handle-cond-3" style={{ left: '80%' }} />
    </div>
  );
};

// Inject types on window object for node execution context
declare global {
  interface Window {
    updateNodeField?: (id: number, field: 'label' | 'description', value: string) => void;
    deleteNode?: (id: number) => void;
    openQuestionsModal?: (node: NodeData) => void;
    openChangesModal?: (node: NodeData) => void;
    openCodeReferencesModal?: (node: NodeData) => void;
    getGroupName?: (groupId: number) => string;
    getGroupInfo?: (groupId: number) => any;
    currentDrawId?: string;
    updateNodeGroup?: (id: number, groupId?: number) => void;
    updateBacklogChecklist?: (taskId: string, phase: 'test' | 'implementation', checked: boolean) => void;
    openSubdraw?: (id: string) => void;
    openDetailViewer?: (id: number) => void;
    openNodeEditModal?: (node: NodeData) => void;
  }
}

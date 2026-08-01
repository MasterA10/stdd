import React, { useState, useEffect, useRef } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps, Node } from '@xyflow/react';
import type { NodeData, Question } from '../types';
import { Trash2, HelpCircle, Eye } from 'lucide-react';

export const NODE_KINDS: { [key: string]: { label: string; color: string; bg: string; icon: string } } = {
  actor: { label: 'Ator', color: '#8B5CF6', bg: '#F5F3FF', icon: '👤' },
  ui: { label: 'Tela', color: '#06B6D4', bg: '#ECFEFF', icon: '🖥️' },
  api: { label: 'API', color: '#3B82F6', bg: '#EFF6FF', icon: '⚡' },
  database: { label: 'Dados', color: '#10B981', bg: '#ECFDF5', icon: '🗄️' },
  external: { label: 'Externo', color: '#F59E0B', bg: '#FFFBEB', icon: '🌐' },
  event: { label: 'Evento', color: '#EC4899', bg: '#FDF2F8', icon: '📡' },
  service: { label: 'Serviço', color: '#6366F1', bg: '#EEF2FF', icon: '⚙️' },
  decision: { label: 'Decisão', color: '#38BDF8', bg: '#F0F9FF', icon: '🔀' },
  process: { label: 'Processo', color: '#F59E0B', bg: '#FEF3C7', icon: '⚡' },
  note: { label: 'Nota', color: '#EAB308', bg: '#FEF9C3', icon: '📝' }
};

function unansweredQuestionCount(questions?: Question[]) {
  const qList = Array.isArray(questions) ? questions : [];
  return qList.filter(q => q.answer === null || q.answer === undefined || (typeof q.answer === 'string' && !q.answer.trim())).length;
}

export const CustomNode: React.FC<NodeProps<Node<NodeData, 'custom'>>> = ({ id, data, selected }) => {
  const [editingField, setEditingField] = useState<'label' | 'description' | null>(null);
  const [draft, setDraft] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const nodeTypeKey = data.type || 'process';
  const preset = NODE_KINDS[nodeTypeKey] || NODE_KINDS.process;

  const totalQuestions = Array.isArray(data.questions) ? data.questions.length : 0;
  const unansweredQuestions = unansweredQuestionCount(data.questions);
  const answeredQuestions = totalQuestions - unansweredQuestions;

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
    }
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

  const handleColorClick = (type: 'background' | 'text') => {
    const input = document.createElement('input');
    input.type = 'color';
    input.value = type === 'background' ? (data.background || preset.bg) : (data.text || '#0f172a');
    input.style.position = 'fixed';
    input.style.left = '-100px';
    input.style.top = '-100px';
    document.body.append(input);

    input.addEventListener('input', () => {
      const hex = input.value;
      if (window.updateNodeColors) {
        window.updateNodeColors(Number(id), hex, type);
      }
    });

    input.addEventListener('change', () => input.remove(), { once: true });
    input.click();
  };

  // Node visual styles
  const borderStyle = isHighlighted
    ? { borderColor: '#10b981', borderWidth: '2.5px', boxShadow: '0 0 0 4px rgba(16, 185, 129, 0.2)' }
    : selected
    ? { borderColor: '#6366f1', borderWidth: '2.5px', boxShadow: '0 0 0 4px rgba(99, 102, 241, 0.15)' }
    : { borderColor: data.background || preset.color };

  const bgStyle = {
    background: data.background || preset.bg,
    color: data.text || '#0f172a',
    opacity: isDimmed ? 0.08 : 1
  };

  return (
    <div
      className={`custom-flow-node ${selected ? 'selected' : ''} ${isHighlighted ? 'highlighted' : ''} ${isDimmed ? 'dimmed' : ''}`}
      style={{ ...borderStyle, ...bgStyle }}
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
          {totalQuestions > 0 && (
            <button
              className="action-circle-btn info"
              onClick={onOpenQuestions}
              title="Perguntas do Bloco"
              type="button"
            >
              <HelpCircle size={12} />
            </button>
          )}
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
          {selected && (
            <>
              <button
                className="action-circle-btn color-picker"
                style={{ backgroundColor: bgStyle.background, border: '2px solid var(--paper)', width: '24px', height: '24px', borderRadius: '50%' }}
                onClick={(e) => { e.stopPropagation(); handleColorClick('background'); }}
                title="Cor do fundo"
                type="button"
              />
              <button
                className="action-circle-btn color-picker"
                style={{ backgroundColor: bgStyle.color, border: '2px solid var(--paper)', width: '24px', height: '24px', borderRadius: '50%' }}
                onClick={(e) => { e.stopPropagation(); handleColorClick('text'); }}
                title="Cor do texto"
                type="button"
              />
            </>
          )}
        </div>
      )}

      {/* Top row: node type and group badge */}
      <div className="node-top-bar">
        <span
          className="node-type-pill"
          style={{ backgroundColor: preset.color + '15', color: preset.color }}
        >
          <span className="node-type-icon">{preset.icon}</span>
          {preset.label}
        </span>
        {data.group !== undefined && window.getGroupName && (
          <span className="node-group-pill">
            {window.getGroupName(data.group)}
          </span>
        )}
        <span className="node-header-id">#{id}</span>
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
          <p
            className="node-body-desc"
            onDoubleClick={(e) => handleDoubleClick('description', e)}
            title="Dê duplo clique para editar descrição"
          >
            {data.description || 'Nenhuma descrição adicionada.'}
          </p>
        )}
      </div>

      {/* Node Footer Row (Questions or Subdraw link) */}
      {(totalQuestions > 0 || data.draw_ref) && (
        <>
          <div className="node-divider-line" />
          <div className="node-footer-row">
            {data.draw_ref ? (
              <span
                className="node-footer-subdraw"
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.openSubdraw) {
                    window.openSubdraw(data.draw_ref!);
                  }
                }}
                title="Abrir subdesenho"
              >
                Detalhes: {data.draw_ref} ↗
              </span>
            ) : (
              <span className="node-footer-questions" onClick={onOpenQuestions}>
                Perguntas
              </span>
            )}
            
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
    getGroupName?: (groupId: number) => string;
    getGroupInfo?: (groupId: number) => any;
    currentDrawId?: string;
    updateNodeColors?: (id: number, color: string, type: 'background' | 'text') => void;
    openSubdraw?: (id: string) => void;
    openDetailViewer?: (id: number) => void;
  }
}

import React, { useState, useEffect } from 'react';
import { Terminal, Plus, Trash2, Edit3, X, Check } from 'lucide-react';
import type { NodeData } from '../types';

interface CodeTasksModalProps {
  node: NodeData;
  onClose: () => void;
  onUpdateCodeTasks: (nodeId: number, codeTasks: string[]) => void;
}

function taskToString(task: unknown): string {
  if (typeof task === 'string') return task.trim();
  if (task && typeof task === 'object') {
    const obj = task as Record<string, any>;
    const title = obj.title || obj.description || obj.endpoint || '';
    const method = obj.method ? `[${obj.method.toUpperCase()}] ` : '';
    const uri = obj.uri || obj.endpoint ? `${obj.uri || obj.endpoint} ` : '';
    if (method || uri) {
      return `${method}${uri}${title ? `— ${title}` : ''}`.trim();
    }
    return String(title || JSON.stringify(obj)).trim();
  }
  return String(task ?? '').trim();
}

export const CodeTasksModal: React.FC<CodeTasksModalProps> = ({ node, onClose, onUpdateCodeTasks }) => {
  const normalizeTasks = (rawTasks: unknown): string[] => {
    if (!Array.isArray(rawTasks)) {
      if (typeof rawTasks === 'string' && rawTasks.trim()) return [rawTasks.trim()];
      return [];
    }
    return rawTasks.map(taskToString).filter((t) => t.length > 0);
  };

  const [tasks, setTasks] = useState<string[]>(normalizeTasks(node.code_tasks));
  const [inputText, setInputText] = useState('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  useEffect(() => {
    setTasks(normalizeTasks(node.code_tasks));
  }, [node.code_tasks]);

  const commit = (nextTasks: string[]) => {
    setTasks(nextTasks);
    onUpdateCodeTasks(node.id, nextTasks);
  };

  const handleSaveTask = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed) return;

    if (editingIndex !== null) {
      const updated = [...tasks];
      updated[editingIndex] = trimmed;
      commit(updated);
      setEditingIndex(null);
    } else {
      commit([...tasks, trimmed]);
    }
    setInputText('');
  };

  const handleStartEdit = (index: number) => {
    setEditingIndex(index);
    setInputText(tasks[index]);
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setInputText('');
  };

  const handleDeleteTask = (index: number) => {
    const updated = tasks.filter((_, i) => i !== index);
    if (editingIndex === index) {
      handleCancelEdit();
    } else if (editingIndex !== null && editingIndex > index) {
      setEditingIndex(editingIndex - 1);
    }
    commit(updated);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey || !e.shiftKey)) {
      e.preventDefault();
      handleSaveTask();
    }
  };

  return (
    <div className="code-tasks-modal-overlay" onClick={onClose}>
      <dialog
        open
        className="code-tasks-dialog"
        onClick={(e) => e.stopPropagation()}
        aria-labelledby="code-tasks-title"
      >
        <div className="code-tasks-header">
          <div className="code-tasks-title-wrapper">
            <div className="code-tasks-badge-icon">
              <Terminal size={18} />
            </div>
            <div>
              <h2 id="code-tasks-title">Tasks de Código (To-Do)</h2>
              <span className="code-tasks-subtitle">
                Nó #{node.id} — {node.label}
              </span>
            </div>
          </div>
          <button className="code-tasks-close-btn" onClick={onClose} title="Fechar modal (Esc)">
            <X size={18} />
          </button>
        </div>

        <div className="code-tasks-body">
          {tasks.length === 0 ? (
            <div className="code-tasks-empty">
              <Terminal size={32} strokeWidth={1.5} className="code-tasks-empty-icon" />
              <p className="code-tasks-empty-title">Nenhuma task de código registrada</p>
              <p className="code-tasks-empty-desc">
                Adicione abaixo os to-dos técnicos de código, endpoints ou regras a serem implementadas neste nó.
              </p>
            </div>
          ) : (
            <div className="code-tasks-list">
              {tasks.map((task, index) => (
                <div
                  key={index}
                  className={`code-task-item ${editingIndex === index ? 'is-editing' : ''}`}
                >
                  <div className="code-task-item-number">{index + 1}</div>
                  <div className="code-task-item-content">
                    <p className="code-task-item-text">{task}</p>
                  </div>
                  <div className="code-task-item-actions">
                    <button
                      className="code-task-action-btn edit"
                      type="button"
                      title="Editar task"
                      onClick={() => handleStartEdit(index)}
                    >
                      <Edit3 size={14} />
                    </button>
                    <button
                      className="code-task-action-btn delete"
                      type="button"
                      title="Excluir task"
                      onClick={() => handleDeleteTask(index)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <form className="code-task-quick-form" onSubmit={handleSaveTask}>
            <div className="code-task-input-wrapper">
              <textarea
                className="code-task-textarea"
                rows={2}
                placeholder={
                  editingIndex !== null
                    ? 'Edite a tarefa de código...'
                    : 'Adicionar nova task de código (ex.: Criar rota POST /api/checkout e validar payload)...'
                }
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </div>
            <div className="code-task-form-bottom">
              <span className="code-task-form-hint">Dica: pressione Enter para adicionar</span>
              <div className="code-task-form-buttons">
                {editingIndex !== null && (
                  <button className="code-task-cancel-btn" type="button" onClick={handleCancelEdit}>
                    Cancelar
                  </button>
                )}
                <button
                  className="code-task-submit-btn"
                  type="submit"
                  disabled={!inputText.trim()}
                >
                  {editingIndex !== null ? (
                    <>
                      <Check size={14} /> Salvar Edição
                    </>
                  ) : (
                    <>
                      <Plus size={14} /> Adicionar Task
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>

        <div className="code-tasks-footer">
          <span className="code-tasks-count-info">
            {tasks.length} {tasks.length === 1 ? 'task de código' : 'tasks de código'}
          </span>
          <button className="code-tasks-primary-btn" type="button" onClick={onClose}>
            Concluir
          </button>
        </div>
      </dialog>
    </div>
  );
};

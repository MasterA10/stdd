import React, { useState, useEffect } from 'react';
import { Terminal, Plus, Trash2, Edit3, X, Check, Code2 } from 'lucide-react';
import type { CodeTask, NodeData } from '../types';

interface CodeTasksModalProps {
  node: NodeData;
  onClose: () => void;
  onUpdateCodeTasks: (nodeId: number, codeTasks: (CodeTask | string)[]) => void;
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'];

function formatJsonOrText(value: unknown): string {
  if (value === undefined || value === null) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function parseJsonOrText(value: string): any {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return trimmed;
    }
  }
  return trimmed;
}

function methodBadgeColor(method?: string): { bg: string; text: string; border: string } {
  const m = (method || '').toUpperCase();
  switch (m) {
    case 'GET':
      return { bg: 'rgba(34, 197, 94, 0.15)', text: '#4ade80', border: 'rgba(34, 197, 94, 0.4)' };
    case 'POST':
      return { bg: 'rgba(99, 102, 241, 0.15)', text: '#818cf8', border: 'rgba(99, 102, 241, 0.4)' };
    case 'PUT':
      return { bg: 'rgba(249, 115, 22, 0.15)', text: '#fb923c', border: 'rgba(249, 115, 22, 0.4)' };
    case 'PATCH':
      return { bg: 'rgba(234, 179, 8, 0.15)', text: '#facc15', border: 'rgba(234, 179, 8, 0.4)' };
    case 'DELETE':
      return { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.4)' };
    default:
      return { bg: 'rgba(148, 163, 184, 0.15)', text: '#cbd5e1', border: 'rgba(148, 163, 184, 0.3)' };
  }
}

export const CodeTasksModal: React.FC<CodeTasksModalProps> = ({ node, onClose, onUpdateCodeTasks }) => {
  const [tasks, setTasks] = useState<(CodeTask | string)[]>(Array.isArray(node.code_tasks) ? node.code_tasks : []);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  // Form draft fields
  const [formTitle, setFormTitle] = useState('');
  const [formMethod, setFormMethod] = useState('POST');
  const [formUri, setFormUri] = useState('');
  const [formParams, setFormParams] = useState('');
  const [formPayload, setFormPayload] = useState('');
  const [formResponse, setFormResponse] = useState('');
  const [formDetails, setFormDetails] = useState('');

  useEffect(() => {
    setTasks(Array.isArray(node.code_tasks) ? node.code_tasks : []);
  }, [node.code_tasks]);

  const commit = (nextTasks: (CodeTask | string)[]) => {
    setTasks(nextTasks);
    onUpdateCodeTasks(node.id, nextTasks);
  };

  const resetForm = () => {
    setFormTitle('');
    setFormMethod('POST');
    setFormUri('');
    setFormParams('');
    setFormPayload('');
    setFormResponse('');
    setFormDetails('');
    setEditingIndex(null);
    setIsAdding(false);
  };

  const startEdit = (index: number) => {
    const task = tasks[index];
    if (typeof task === 'string') {
      setFormTitle(task);
      setFormMethod('POST');
      setFormUri('');
      setFormParams('');
      setFormPayload('');
      setFormResponse('');
      setFormDetails('');
    } else {
      setFormTitle(task.title || task.endpoint || '');
      setFormMethod(task.method || 'POST');
      setFormUri(task.uri || '');
      setFormParams(formatJsonOrText(task.params));
      setFormPayload(formatJsonOrText(task.payload));
      setFormResponse(formatJsonOrText(task.response));
      setFormDetails(task.details || '');
    }
    setEditingIndex(index);
    setIsAdding(false);
  };

  const handleSaveTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() && !formUri.trim()) return;

    const taskObj: CodeTask = {
      id: editingIndex !== null && typeof tasks[editingIndex] === 'object' ? (tasks[editingIndex] as CodeTask).id : Date.now(),
      title: formTitle.trim() || undefined,
      method: formUri.trim() ? formMethod.toUpperCase() : undefined,
      uri: formUri.trim() || undefined,
      params: parseJsonOrText(formParams),
      payload: parseJsonOrText(formPayload),
      response: parseJsonOrText(formResponse),
      details: formDetails.trim() || undefined,
    };

    if (editingIndex !== null) {
      const nextTasks = [...tasks];
      nextTasks[editingIndex] = taskObj;
      commit(nextTasks);
    } else {
      commit([...tasks, taskObj]);
    }
    resetForm();
  };

  const handleDeleteTask = (index: number) => {
    const nextTasks = tasks.filter((_, i) => i !== index);
    commit(nextTasks);
    if (editingIndex === index) {
      resetForm();
    }
  };

  return (
    <div className="dialog-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <dialog className="app-dialog code-tasks-dialog" open aria-labelledby="code-tasks-title">
        <div className="dialog-header">
          <div>
            <p className="eyebrow code-tasks-eyebrow">
              <Terminal size={13} /> Looper · Tasks de Código (Nível 3)
            </p>
            <h2 id="code-tasks-title">{node.label}</h2>
            <p className="code-tasks-node-id">Nó #{node.id} · Especificação técnica de endpoints e implementação</p>
          </div>
          <button className="close-btn" onClick={onClose} type="button" aria-label="Fechar tasks de código">
            <X size={18} />
          </button>
        </div>

        <div className="code-tasks-modal-body">
          {/* List of Tasks */}
          <div className="code-tasks-list-header">
            <strong>Tasks e Endpoints Declarados</strong>
            <span className="code-tasks-total">{tasks.length}</span>
            {!isAdding && editingIndex === null && (
              <button
                className="code-tasks-add-btn"
                type="button"
                onClick={() => {
                  resetForm();
                  setIsAdding(true);
                }}
              >
                <Plus size={14} /> Adicionar Task de Código
              </button>
            )}
          </div>

          {tasks.length === 0 && !isAdding ? (
            <div className="code-tasks-empty">
              <Code2 size={24} className="code-tasks-empty-icon" />
              <p>Nenhuma task de código ou endpoint especificado neste nó.</p>
              <button
                className="code-tasks-add-btn empty-action"
                type="button"
                onClick={() => {
                  resetForm();
                  setIsAdding(true);
                }}
              >
                <Plus size={14} /> Criar primeira task
              </button>
            </div>
          ) : (
            <div className="code-tasks-list">
              {tasks.map((taskItem, index) => {
                const isItemObj = typeof taskItem === 'object' && taskItem !== null;
                const task: CodeTask = isItemObj ? taskItem : { title: String(taskItem) };
                const badge = methodBadgeColor(task.method);

                return (
                  <article
                    key={task.id || index}
                    className={`code-task-card ${editingIndex === index ? 'is-editing' : ''}`}
                  >
                    <div className="code-task-card-header">
                      <div className="code-task-header-left">
                        {task.method && (
                          <span
                            className="code-task-method-badge"
                            style={{ backgroundColor: badge.bg, color: badge.text, borderColor: badge.border }}
                          >
                            {task.method}
                          </span>
                        )}
                        {task.uri && <code className="code-task-uri">{task.uri}</code>}
                        {task.title && <span className="code-task-title">{task.title}</span>}
                      </div>
                      <div className="code-task-actions">
                        <button
                          className="code-task-action-btn"
                          type="button"
                          onClick={() => startEdit(index)}
                          title="Editar task"
                        >
                          <Edit3 size={13} />
                        </button>
                        <button
                          className="code-task-action-btn danger"
                          type="button"
                          onClick={() => handleDeleteTask(index)}
                          title="Excluir task"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>

                    {task.details && <p className="code-task-details">{task.details}</p>}

                    {task.params && (
                      <div className="code-task-block">
                        <span className="code-task-block-label">Parâmetros:</span>
                        <pre className="code-task-code-block">{formatJsonOrText(task.params)}</pre>
                      </div>
                    )}

                    {task.payload && (
                      <div className="code-task-block">
                        <span className="code-task-block-label">Payload esperado:</span>
                        <pre className="code-task-code-block">{formatJsonOrText(task.payload)}</pre>
                      </div>
                    )}

                    {task.response && (
                      <div className="code-task-block">
                        <span className="code-task-block-label">Resposta esperada:</span>
                        <pre className="code-task-code-block">{formatJsonOrText(task.response)}</pre>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}

          {/* Add / Edit Form */}
          {(isAdding || editingIndex !== null) && (
            <form className="code-task-form" onSubmit={handleSaveTask}>
              <div className="code-task-form-title">
                <strong>{editingIndex !== null ? 'Editar Task de Código' : 'Nova Task de Código'}</strong>
                <button className="code-task-form-close" type="button" onClick={resetForm}>
                  <X size={14} />
                </button>
              </div>

              <div className="code-task-form-row">
                <div className="code-task-form-field method-field">
                  <label htmlFor="task-method">Método</label>
                  <select
                    id="task-method"
                    value={formMethod}
                    onChange={(e) => setFormMethod(e.target.value)}
                  >
                    {HTTP_METHODS.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>

                <div className="code-task-form-field uri-field">
                  <label htmlFor="task-uri">URI / Rota</label>
                  <input
                    id="task-uri"
                    type="text"
                    placeholder="/api/v1/resource/:id"
                    value={formUri}
                    onChange={(e) => setFormUri(e.target.value)}
                  />
                </div>
              </div>

              <div className="code-task-form-field">
                <label htmlFor="task-title">Título / Responsabilidade</label>
                <input
                  id="task-title"
                  type="text"
                  placeholder="Ex.: Cria sessão e emite JWT de autenticação"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                />
              </div>

              <div className="code-task-form-field">
                <label htmlFor="task-details">Detalhes técnicos de implementação</label>
                <textarea
                  id="task-details"
                  rows={2}
                  placeholder="Instruções para controller, service, validação e persistência..."
                  value={formDetails}
                  onChange={(e) => setFormDetails(e.target.value)}
                />
              </div>

              <div className="code-task-form-row">
                <div className="code-task-form-field">
                  <label htmlFor="task-params">Parâmetros (Query/Rota)</label>
                  <textarea
                    id="task-params"
                    rows={3}
                    placeholder='{"tenant_id": "string"}'
                    value={formParams}
                    onChange={(e) => setFormParams(e.target.value)}
                  />
                </div>

                <div className="code-task-form-field">
                  <label htmlFor="task-payload">Payload da Requisição</label>
                  <textarea
                    id="task-payload"
                    rows={3}
                    placeholder='{"email": "string", "password": "string"}'
                    value={formPayload}
                    onChange={(e) => setFormPayload(e.target.value)}
                  />
                </div>
              </div>

              <div className="code-task-form-field">
                <label htmlFor="task-response">Payload de Resposta</label>
                <textarea
                  id="task-response"
                  rows={2}
                  placeholder='{"token": "string", "expires_in": 3600}'
                  value={formResponse}
                  onChange={(e) => setFormResponse(e.target.value)}
                />
              </div>

              <div className="code-task-form-actions">
                <button className="code-task-cancel-btn" type="button" onClick={resetForm}>
                  Cancelar
                </button>
                <button className="code-task-submit-btn" type="submit">
                  <Check size={14} /> Salvar Task
                </button>
              </div>
            </form>
          )}
        </div>
      </dialog>
    </div>
  );
};

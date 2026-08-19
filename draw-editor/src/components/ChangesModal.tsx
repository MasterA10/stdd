import React, { useEffect, useState } from 'react';
import { Plus, Repeat2, Trash2, X } from 'lucide-react';
import type { ChangeRequest, NodeData } from '../types';
import { ConfirmModal } from './ConfirmModal';

interface ChangesModalProps {
  node: NodeData;
  onClose: () => void;
  onUpdateChanges: (nodeId: number, changes: ChangeRequest[]) => void;
}

/** Registra mudanças de implementação que o cursor `backlog change` consome. */
export const ChangesModal: React.FC<ChangesModalProps> = ({ node, onClose, onUpdateChanges }) => {
  const [changes, setChanges] = useState<ChangeRequest[]>(node.changes || []);
  const [prompt, setPrompt] = useState('');
  const [showDiscardDraftConfirm, setShowDiscardDraftConfirm] = useState(false);

  useEffect(() => setChanges(node.changes || []), [node.changes]);

  const commit = (nextChanges: ChangeRequest[]) => {
    setChanges(nextChanges);
    onUpdateChanges(node.id, nextChanges);
  };

  const addChange = (event: React.FormEvent) => {
    event.preventDefault();
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;
    const nextId = changes.length ? Math.max(...changes.map((change) => change.id)) + 1 : 1;
    commit([...changes, { id: nextId, prompt: cleanPrompt, status: 'pending' }]);
    setPrompt('');
  };

  const requestClose = () => {
    if (prompt.trim()) return setShowDiscardDraftConfirm(true);
    onClose();
  };

  return (
    <>
      <div className="dialog-overlay">
        <dialog className="app-dialog questions-dialog" open onCancel={(event) => { event.preventDefault(); requestClose(); }}>
          <div className="dialog-content questions-modal-content">
            <div className="dialog-header">
              <div>
                <p className="eyebrow">Looper · Alterações</p>
                <h2>{node.label}</h2>
              </div>
              <button className="close-btn" onClick={requestClose} type="button" aria-label="Fechar alterações"><X size={18} /></button>
            </div>

            <form className="editor-card question-create-card question-create-card-top" onSubmit={addChange}>
              <h3>Adicionar pedido de alteração</h3>
              <textarea
                className="question-create-prompt"
                placeholder="Ex.: Atualize a validação e todos os pontos que exibem esta regra."
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                required
              />
              <button className="sidebar-submit-btn" type="submit"><Plus size={14} /> Adicionar alteração</button>
            </form>

            <div className="question-list">
              {changes.length === 0 ? (
                <div className="questions-empty-state">
                  <Repeat2 size={24} aria-hidden="true" />
                  <strong>Nenhuma alteração pendente</strong>
                  <p>Registre aqui mudanças que podem envolver este nó e outros locais da codebase.</p>
                </div>
              ) : changes.map((change) => (
                <div key={change.id} className={`question-card question-editor-card ${change.status}`}>
                  <div className="question-card-header">
                    <div><span className="question-number">#{String(change.id).padStart(2, '0')}</span><strong>Pedido de alteração</strong></div>
                    <span className="question-unanswered-badge">{change.status === 'done' ? 'Concluída' : change.status === 'in_progress' ? 'Em andamento' : 'Pendente'}</span>
                    {change.status === 'pending' && (
                      <button className="question-del-btn" onClick={() => commit(changes.filter((item) => item.id !== change.id))} title="Remover alteração" type="button"><Trash2 size={12} /></button>
                    )}
                  </div>
                  <p className="change-request-prompt">{change.prompt}</p>
                </div>
              ))}
            </div>
            <div className="dialog-actions"><button className="primary" onClick={onClose} type="button">Concluído</button></div>
          </div>
        </dialog>
      </div>
      <ConfirmModal
        isOpen={showDiscardDraftConfirm}
        title="Descartar alteração?"
        message="O pedido digitado ainda não foi adicionado. Deseja sair sem salvar?"
        confirmLabel="Sair sem salvar"
        cancelLabel="Continuar editando"
        isDanger
        onConfirm={() => { setShowDiscardDraftConfirm(false); setPrompt(''); onClose(); }}
        onCancel={() => setShowDiscardDraftConfirm(false)}
      />
    </>
  );
};

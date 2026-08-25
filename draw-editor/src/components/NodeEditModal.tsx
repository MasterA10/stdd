import React, { useEffect, useRef, useState } from 'react';
import type { NodeData } from '../types';
import { X } from 'lucide-react';

interface NodeEditModalProps {
  node: NodeData;
  onClose: () => void;
  onSave: (nodeId: number, label: string, description: string, successCriteria: string, failureCriteria: string) => void;
}

export const NodeEditModal: React.FC<NodeEditModalProps> = ({ node, onClose, onSave }) => {
  const [label, setLabel] = useState(node.label || '');
  const [description, setDescription] = useState(node.description || '');
  const [successCriteria, setSuccessCriteria] = useState(node.success_criteria || '');
  const [failureCriteria, setFailureCriteria] = useState(node.failure_criteria || '');
  const descriptionRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = descriptionRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, window.innerHeight * 0.55)}px`;
  }, [description]);

  const handleSave = () => {
    onSave(node.id, label, description, successCriteria, failureCriteria);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSave();
    }
  };

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <dialog className="app-dialog node-edit-dialog" open onClick={(e) => e.stopPropagation()}>
        <div className="dialog-content">
          <div className="dialog-header">
            <div>
              <p className="eyebrow">Looper · Edição de Bloco</p>
              <h2>Editar Descrição</h2>
            </div>
            <button className="close-btn" onClick={onClose} type="button">
              <X size={18} />
            </button>
          </div>
          
          <div className="dialog-fields" style={{ marginTop: '20px' }}>
            <label>Título do Bloco</label>
            <input 
              value={label} 
              onChange={(e) => setLabel(e.target.value)} 
              onKeyDown={handleKeyDown}
              autoFocus
            />
          </div>
          
          <div className="dialog-fields" style={{ marginTop: '16px' }}>
            <label>Descrição</label>
              <textarea
                ref={descriptionRef}
                aria-label="Descrição integral do bloco"
                value={description}
              onChange={(e) => setDescription(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Descreva os detalhes e regras deste bloco..."
            />
          </div>

          <fieldset className="dialog-fields node-success-criteria-fields" style={{ marginTop: '16px' }}>
            <legend>Critérios de validação (opcional)</legend>
            <label htmlFor="node-modal-success-criteria">Critério de sucesso</label>
            <textarea
              id="node-modal-success-criteria"
              name="success_criteria"
              value={successCriteria}
              onChange={(e) => setSuccessCriteria(e.target.value)}
              placeholder="Como saberemos que este nó funcionou?"
            />
            <label htmlFor="node-modal-failure-criteria">Critério de falha</label>
            <textarea
              id="node-modal-failure-criteria"
              name="failure_criteria"
              value={failureCriteria}
              onChange={(e) => setFailureCriteria(e.target.value)}
              placeholder="Qual cenário indica que este nó falhou?"
            />
          </fieldset>
          
          <div className="dialog-actions" style={{ marginTop: '24px' }}>
            <button className="secondary" onClick={onClose} type="button">Cancelar</button>
            <button className="primary" onClick={handleSave} type="button" title="Ctrl+Enter para salvar">Salvar</button>
          </div>
        </div>
      </dialog>
    </div>
  );
};

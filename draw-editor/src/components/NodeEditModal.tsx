import React, { useState } from 'react';
import type { NodeData } from '../types';
import { X } from 'lucide-react';

interface NodeEditModalProps {
  node: NodeData;
  onClose: () => void;
  onSave: (nodeId: number, label: string, description: string) => void;
}

export const NodeEditModal: React.FC<NodeEditModalProps> = ({ node, onClose, onSave }) => {
  const [label, setLabel] = useState(node.label || '');
  const [description, setDescription] = useState(node.description || '');

  const handleSave = () => {
    onSave(node.id, label, description);
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
              <p className="eyebrow">STDD · Edição de Bloco</p>
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
              value={description} 
              onChange={(e) => setDescription(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Descreva os detalhes e regras deste bloco..."
            />
          </div>
          
          <div className="dialog-actions" style={{ marginTop: '24px' }}>
            <button className="secondary" onClick={onClose} type="button">Cancelar</button>
            <button className="primary" onClick={handleSave} type="button" title="Ctrl+Enter para salvar">Salvar</button>
          </div>
        </div>
      </dialog>
    </div>
  );
};

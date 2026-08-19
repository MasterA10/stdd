import React from 'react';
import { ArrowUp, ChevronRight, X } from 'lucide-react';

export interface ParentNavigationOption {
  drawId: string;
  title: string;
  nodeId: number | null;
  nodeLabel: string;
  level?: number;
}

interface ParentNavigationModalProps {
  isOpen: boolean;
  childTitle: string;
  options: ParentNavigationOption[];
  onSelect: (option: ParentNavigationOption) => void;
  onClose: () => void;
}

export const ParentNavigationModal: React.FC<ParentNavigationModalProps> = ({
  isOpen,
  childTitle,
  options,
  onSelect,
  onClose
}) => {
  if (!isOpen) return null;

  return (
    <div className="dialog-overlay parent-navigation-overlay">
      <dialog
        className="app-dialog parent-navigation-dialog"
        open
        onCancel={(event) => { event.preventDefault(); onClose(); }}
      >
        <div className="dialog-header">
          <div>
            <p className="eyebrow">STDD · Navegação hierárquica</p>
            <h2>Escolha para onde voltar</h2>
          </div>
          <button className="close-btn" onClick={onClose} type="button" aria-label="Fechar escolha de nível">
            <X size={18} />
          </button>
        </div>

        <p className="dialog-copy parent-navigation-copy">
          “{childTitle}” está associado a mais de um nó. Escolha o desenho pai que deseja abrir.
        </p>

        <div className="parent-navigation-list" role="list" aria-label="Desenhos pais disponíveis">
          {options.map((option) => (
            <button
              className="parent-navigation-option"
              key={`${option.drawId}:${option.nodeId ?? 'draw'}`}
              type="button"
              onClick={() => onSelect(option)}
            >
              <span className="parent-navigation-option-icon" aria-hidden="true">
                <ArrowUp size={17} />
              </span>
              <span className="parent-navigation-option-copy">
                <strong>{option.title}</strong>
                <span>
                  {option.nodeId === null ? 'Desenho pai' : `Nó ${option.nodeId}: ${option.nodeLabel}`}
                  {option.level ? ` · nível ${option.level}` : ''}
                </span>
              </span>
              <ChevronRight className="parent-navigation-option-arrow" size={17} aria-hidden="true" />
            </button>
          ))}
        </div>

        <div className="dialog-actions">
          <button type="button" onClick={onClose}>Cancelar</button>
        </div>
      </dialog>
    </div>
  );
};
